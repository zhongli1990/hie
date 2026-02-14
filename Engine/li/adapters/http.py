"""
LI HTTP Adapters

Implements HTTP-based message transport for HL7v2, FHIR, and other formats.
Provides both inbound (HTTP server) and outbound (HTTP client) adapters.

IRIS equivalents:
    - EnsLib.HTTP.InboundAdapter   (HTTP listener on a port)
    - EnsLib.HTTP.OutboundAdapter  (HTTP client with connection pooling)

Rhapsody equivalent: HTTP Communication Point (Input/Output modes)
Mirth equivalent:    HTTP Listener / HTTP Sender connectors

The HTTP adapters are protocol-agnostic — they transport raw bytes over HTTP.
The host class (e.g., HL7HTTPService, FHIRRESTService) is responsible for
parsing the payload and generating the appropriate response.
"""

from __future__ import annotations

import asyncio
import ssl
from datetime import datetime, timezone
from typing import Any, Callable, Awaitable, TYPE_CHECKING

import structlog

from Engine.li.adapters.base import InboundAdapter, OutboundAdapter, AdapterState

if TYPE_CHECKING:
    from Engine.li.hosts.base import Host

logger = structlog.get_logger(__name__)

# Default settings
DEFAULT_HTTP_PORT = 9380
DEFAULT_READ_TIMEOUT = 30.0
DEFAULT_WRITE_TIMEOUT = 30.0
DEFAULT_CONNECT_TIMEOUT = 10.0
DEFAULT_MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB


class HTTPAdapterError(Exception):
    """Error during HTTP adapter operation."""
    pass


class HTTPRequest:
    """
    Represents an inbound HTTP request.

    Passed to the host for processing. The host returns an HTTPResponse.
    This decouples the HTTP transport from the message processing logic.
    """
    __slots__ = (
        "method", "path", "headers", "body", "query_string",
        "content_type", "remote_addr",
    )

    def __init__(
        self,
        method: str,
        path: str,
        headers: dict[str, str],
        body: bytes,
        query_string: str = "",
        content_type: str = "",
        remote_addr: str = "",
    ):
        self.method = method
        self.path = path
        self.headers = headers
        self.body = body
        self.query_string = query_string
        self.content_type = content_type
        self.remote_addr = remote_addr


class HTTPResponse:
    """
    Represents an outbound HTTP response.

    Returned by the host after processing an HTTPRequest.
    """
    __slots__ = ("status_code", "headers", "body", "content_type")

    def __init__(
        self,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        body: bytes = b"",
        content_type: str = "text/plain",
    ):
        self.status_code = status_code
        self.headers = headers or {}
        self.body = body
        self.content_type = content_type


class InboundHTTPAdapter(InboundAdapter):
    """
    HTTP Inbound Adapter — listens for HTTP requests.

    Starts an HTTP server on a configured port and passes incoming
    requests to the host for processing. The host returns a response
    which is sent back to the client.

    IRIS equivalent: EnsLib.HTTP.InboundAdapter
    Rhapsody equivalent: HTTP Communication Point (Input mode)
    Mirth equivalent: HTTP Listener connector

    Settings:
        Port:           HTTP port to listen on (required)
        Host:           IP address to bind to (default: 0.0.0.0)
        SSLConfig:      SSL certificate config name (optional, for HTTPS)
        SSLCertFile:    Path to SSL certificate file (optional)
        SSLKeyFile:     Path to SSL key file (optional)
        MaxBodySize:    Maximum request body size in bytes (default: 10MB)
        ReadTimeout:    Read timeout in seconds (default: 30)
        AllowedMethods: Comma-separated allowed HTTP methods (default: POST)
        BasePath:       URL base path prefix (default: /)
        EnableCORS:     Enable CORS headers (default: false)
    """

    def __init__(self, host: Host, settings: dict[str, Any] | None = None):
        super().__init__(host, settings)

        # Configuration
        self._port = int(self.get_setting("Port", DEFAULT_HTTP_PORT))
        self._bind_host = self.get_setting("Host", "0.0.0.0")
        self._ssl_cert_file = self.get_setting("SSLCertFile", None)
        self._ssl_key_file = self.get_setting("SSLKeyFile", None)
        self._max_body_size = int(self.get_setting("MaxBodySize", DEFAULT_MAX_BODY_SIZE))
        self._read_timeout = float(self.get_setting("ReadTimeout", DEFAULT_READ_TIMEOUT))
        self._allowed_methods = [
            m.strip().upper()
            for m in self.get_setting("AllowedMethods", "POST").split(",")
        ]
        self._base_path = self.get_setting("BasePath", "/")
        self._enable_cors = str(self.get_setting("EnableCORS", "false")).lower() == "true"

        # Runtime
        self._server: asyncio.Server | None = None
        self._shutdown_event = asyncio.Event()

        # Callback for host to handle requests
        self._request_handler: Callable[[HTTPRequest], Awaitable[HTTPResponse]] | None = None

        self._log = logger.bind(
            adapter="InboundHTTPAdapter",
            host=host.name,
            port=self._port,
        )

    def set_request_handler(
        self, handler: Callable[[HTTPRequest], Awaitable[HTTPResponse]]
    ) -> None:
        """Set the callback for handling HTTP requests."""
        self._request_handler = handler

    async def on_start(self) -> None:
        """Start the HTTP server."""
        self._shutdown_event.clear()

        # SSL context
        ssl_context = None
        if self._ssl_cert_file and self._ssl_key_file:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(self._ssl_cert_file, self._ssl_key_file)

        self._server = await asyncio.start_server(
            self._handle_connection,
            host=self._bind_host,
            port=self._port,
            ssl=ssl_context,
            reuse_address=True,
        )

        self._log.info(
            "http_inbound_adapter_started",
            bind_host=self._bind_host,
            port=self._port,
            ssl=ssl_context is not None,
            allowed_methods=self._allowed_methods,
        )

    async def on_stop(self) -> None:
        """Stop the HTTP server."""
        self._shutdown_event.set()
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        self._log.info("http_inbound_adapter_stopped")

    async def listen(self) -> None:
        """Start serving HTTP requests. Runs until stopped."""
        if self._server:
            await self._server.serve_forever()

    async def _handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a single HTTP connection (may have multiple requests via keep-alive)."""
        peername = writer.get_extra_info("peername")
        remote_addr = f"{peername[0]}:{peername[1]}" if peername else "unknown"

        try:
            # Read one HTTP request (simplified — no keep-alive for now)
            request = await self._read_request(reader, remote_addr)
            if not request:
                return

            self._metrics.bytes_received += len(request.body)
            self._metrics.last_activity_at = datetime.now(timezone.utc)

            # Validate method
            if request.method not in self._allowed_methods:
                response = HTTPResponse(
                    status_code=405,
                    body=b"Method Not Allowed",
                    content_type="text/plain",
                    headers={"Allow": ", ".join(self._allowed_methods)},
                )
            else:
                # Pass to host for processing
                response = await self._process_request(request)

            # Send response
            await self._write_response(writer, response)
            self._metrics.bytes_sent += len(response.body)

        except asyncio.TimeoutError:
            self._log.debug("http_read_timeout", remote=remote_addr)
        except Exception as e:
            self._log.error("http_connection_error", remote=remote_addr, error=str(e))
            self._metrics.errors_total += 1
            # Try to send 500 response
            try:
                err_response = HTTPResponse(
                    status_code=500,
                    body=f"Internal Server Error: {e}".encode(),
                    content_type="text/plain",
                )
                await self._write_response(writer, err_response)
            except Exception:
                pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _read_request(
        self, reader: asyncio.StreamReader, remote_addr: str
    ) -> HTTPRequest | None:
        """Parse an HTTP request from the stream."""
        try:
            # Read request line
            request_line = await asyncio.wait_for(
                reader.readline(), timeout=self._read_timeout
            )
            if not request_line:
                return None

            request_line = request_line.decode("utf-8", errors="replace").strip()
            parts = request_line.split(" ", 2)
            if len(parts) < 2:
                return None

            method = parts[0].upper()
            raw_path = parts[1]

            # Split path and query string
            if "?" in raw_path:
                path, query_string = raw_path.split("?", 1)
            else:
                path = raw_path
                query_string = ""

            # Read headers
            headers: dict[str, str] = {}
            while True:
                line = await asyncio.wait_for(
                    reader.readline(), timeout=self._read_timeout
                )
                line = line.decode("utf-8", errors="replace").strip()
                if not line:
                    break
                if ":" in line:
                    key, value = line.split(":", 1)
                    headers[key.strip().lower()] = value.strip()

            # Read body
            content_length = int(headers.get("content-length", "0"))
            if content_length > self._max_body_size:
                raise HTTPAdapterError(
                    f"Request body too large: {content_length} > {self._max_body_size}"
                )

            body = b""
            if content_length > 0:
                body = await asyncio.wait_for(
                    reader.readexactly(content_length),
                    timeout=self._read_timeout,
                )

            content_type = headers.get("content-type", "")

            return HTTPRequest(
                method=method,
                path=path,
                headers=headers,
                body=body,
                query_string=query_string,
                content_type=content_type,
                remote_addr=remote_addr,
            )

        except asyncio.IncompleteReadError:
            return None

    async def _process_request(self, request: HTTPRequest) -> HTTPResponse:
        """
        Process an HTTP request.

        If a request_handler is set (by the host), use it.
        Otherwise, pass raw body bytes to on_data_received.
        """
        if self._request_handler:
            return await self._request_handler(request)

        # Fallback: pass body bytes to host via on_data_received
        result = await self.on_data_received(request.body)

        # Convert result to HTTPResponse
        if isinstance(result, HTTPResponse):
            return result
        elif isinstance(result, bytes):
            return HTTPResponse(status_code=200, body=result, content_type="text/plain")
        elif result is not None and hasattr(result, "ack") and result.ack:
            return HTTPResponse(
                status_code=200,
                body=result.ack,
                content_type="application/hl7-v2+er7",
            )
        else:
            return HTTPResponse(status_code=200, body=b"OK", content_type="text/plain")

    async def _write_response(
        self, writer: asyncio.StreamWriter, response: HTTPResponse
    ) -> None:
        """Write an HTTP response to the stream."""
        # Status line
        status_text = {
            200: "OK", 201: "Created", 204: "No Content",
            400: "Bad Request", 404: "Not Found", 405: "Method Not Allowed",
            500: "Internal Server Error",
        }.get(response.status_code, "Unknown")

        lines = [f"HTTP/1.1 {response.status_code} {status_text}"]

        # Headers
        headers = dict(response.headers)
        headers["Content-Type"] = response.content_type
        headers["Content-Length"] = str(len(response.body))
        headers["Connection"] = "close"

        if self._enable_cors:
            headers["Access-Control-Allow-Origin"] = "*"
            headers["Access-Control-Allow-Methods"] = ", ".join(self._allowed_methods)
            headers["Access-Control-Allow-Headers"] = "Content-Type"

        for key, value in headers.items():
            lines.append(f"{key}: {value}")

        # Write header + body
        header_bytes = ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8")
        writer.write(header_bytes + response.body)
        await writer.drain()


class OutboundHTTPAdapter(OutboundAdapter):
    """
    HTTP Outbound Adapter — sends HTTP requests to remote systems.

    Makes HTTP requests to a configured URL and returns the response.
    Supports configurable methods, headers, SSL, and retry logic.

    IRIS equivalent: EnsLib.HTTP.OutboundAdapter
    Rhapsody equivalent: HTTP Communication Point (Output mode)
    Mirth equivalent: HTTP Sender connector

    Settings:
        URL:            Base URL for requests (required, e.g., http://host:port/path)
        HTTPMethod:     HTTP method (default: POST)
        ContentType:    Content-Type header (default: application/hl7-v2+er7)
        Credentials:    Auth credentials name (optional)
        SSLConfig:      SSL config name (optional)
        SSLVerify:      Verify SSL certificates (default: true)
        ConnectTimeout: Connection timeout in seconds (default: 10)
        ResponseTimeout: Response timeout in seconds (default: 30)
        MaxRetries:     Maximum send retries (default: 3)
        RetryDelay:     Delay between retries in seconds (default: 5)
        CustomHeaders:  JSON string of additional headers (optional)
    """

    def __init__(self, host: Host, settings: dict[str, Any] | None = None):
        super().__init__(host, settings)

        # Configuration
        self._url = self.get_setting("URL", "http://localhost:8080")
        self._method = self.get_setting("HTTPMethod", "POST").upper()
        self._content_type = self.get_setting("ContentType", "application/hl7-v2+er7")
        self._ssl_verify = str(self.get_setting("SSLVerify", "true")).lower() == "true"
        self._connect_timeout = float(self.get_setting("ConnectTimeout", DEFAULT_CONNECT_TIMEOUT))
        self._response_timeout = float(self.get_setting("ResponseTimeout", DEFAULT_READ_TIMEOUT))
        self._max_retries = int(self.get_setting("MaxRetries", 3))
        self._retry_delay = float(self.get_setting("RetryDelay", 5.0))

        # Parse custom headers
        self._custom_headers: dict[str, str] = {}
        custom_headers_str = self.get_setting("CustomHeaders", "")
        if custom_headers_str:
            try:
                import json
                self._custom_headers = json.loads(custom_headers_str)
            except Exception:
                pass

        self._log = logger.bind(
            adapter="OutboundHTTPAdapter",
            host=host.name,
            url=self._url,
        )

    async def on_start(self) -> None:
        """Initialize the adapter."""
        self._log.info("http_outbound_adapter_started", url=self._url)

    async def on_stop(self) -> None:
        """Clean up."""
        self._log.info("http_outbound_adapter_stopped")

    async def send(self, message: Any) -> bytes:
        """
        Send a message via HTTP and return the response body.

        Uses aiohttp for async HTTP requests with connection pooling.

        Args:
            message: Message to send (bytes, or object with .raw attribute)

        Returns:
            Response body bytes

        Raises:
            HTTPAdapterError: If request fails after all retries
        """
        # Extract bytes
        if isinstance(message, bytes):
            data = message
        elif hasattr(message, "raw"):
            data = message.raw
        else:
            data = str(message).encode("utf-8")

        last_error = None

        for attempt in range(self._max_retries):
            try:
                response_body, status_code = await self._do_request(data)

                self._metrics.bytes_sent += len(data)
                self._metrics.bytes_received += len(response_body)
                self._metrics.last_activity_at = datetime.now(timezone.utc)
                await self.on_send(data)

                self._log.debug(
                    "http_message_sent",
                    size=len(data),
                    status=status_code,
                    response_size=len(response_body),
                    attempt=attempt + 1,
                )

                return response_body

            except Exception as e:
                last_error = e
                self._metrics.errors_total += 1
                self._log.warning(
                    "http_send_failed",
                    attempt=attempt + 1,
                    max_retries=self._max_retries,
                    error=str(e),
                )
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay)

        raise HTTPAdapterError(
            f"HTTP request failed after {self._max_retries} attempts: {last_error}"
        )

    async def _do_request(self, data: bytes) -> tuple[bytes, int]:
        """
        Perform a single HTTP request.

        Uses aiohttp if available, falls back to raw asyncio sockets.

        Returns:
            Tuple of (response_body, status_code)
        """
        try:
            import aiohttp

            ssl_context = None if self._ssl_verify else False

            timeout = aiohttp.ClientTimeout(
                total=self._response_timeout,
                connect=self._connect_timeout,
            )

            headers = {"Content-Type": self._content_type}
            headers.update(self._custom_headers)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    method=self._method,
                    url=self._url,
                    data=data,
                    headers=headers,
                    ssl=ssl_context,
                ) as resp:
                    body = await resp.read()
                    return body, resp.status

        except ImportError:
            # Fallback: use raw HTTP over asyncio (simplified)
            return await self._raw_http_request(data)

    async def _raw_http_request(self, data: bytes) -> tuple[bytes, int]:
        """
        Fallback HTTP request using raw asyncio sockets.

        Used when aiohttp is not available.
        """
        from urllib.parse import urlparse

        parsed = urlparse(self._url)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"
        if parsed.query:
            path += f"?{parsed.query}"

        ssl_context = None
        if parsed.scheme == "https":
            ssl_context = ssl.create_default_context()
            if not self._ssl_verify:
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=ssl_context),
            timeout=self._connect_timeout,
        )

        try:
            # Build request
            headers = {
                "Host": host,
                "Content-Type": self._content_type,
                "Content-Length": str(len(data)),
                "Connection": "close",
            }
            headers.update(self._custom_headers)

            request_line = f"{self._method} {path} HTTP/1.1\r\n"
            header_lines = "".join(f"{k}: {v}\r\n" for k, v in headers.items())
            request_bytes = (request_line + header_lines + "\r\n").encode("utf-8") + data

            writer.write(request_bytes)
            await writer.drain()

            # Read response
            response_data = await asyncio.wait_for(
                reader.read(self._max_body_size if hasattr(self, '_max_body_size') else 10 * 1024 * 1024),
                timeout=self._response_timeout,
            )

            # Parse status code
            status_line = response_data.split(b"\r\n", 1)[0].decode("utf-8", errors="replace")
            parts = status_line.split(" ", 2)
            status_code = int(parts[1]) if len(parts) >= 2 else 500

            # Extract body (after double CRLF)
            body_start = response_data.find(b"\r\n\r\n")
            body = response_data[body_start + 4:] if body_start >= 0 else b""

            return body, status_code

        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
