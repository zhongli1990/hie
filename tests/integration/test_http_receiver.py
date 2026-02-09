"""
Integration tests for HTTP Receiver.
"""

import pytest
import asyncio
import pytest_asyncio

from Engine.items.receivers.http_receiver import HTTPReceiver
from Engine.core.config import HTTPReceiverConfig
from Engine.core.message import Message


class TestHTTPReceiverIntegration:
    """Integration tests for HTTPReceiver."""
    
    @pytest.fixture
    def receiver_config(self):
        return HTTPReceiverConfig(
            id="test_http",
            name="Test HTTP Receiver",
            host="127.0.0.1",
            port=18080,  # Use non-standard port for testing
            path="/hl7",
            content_types=["text/plain", "application/hl7-v2"],
        )
    
    @pytest_asyncio.fixture
    async def receiver(self, receiver_config):
        receiver = HTTPReceiver(receiver_config)
        yield receiver
        if receiver.is_running:
            await receiver.stop()
    
    @pytest.mark.asyncio
    async def test_receiver_starts_and_stops(self, receiver):
        await receiver.start()
        
        assert receiver.is_running
        
        await receiver.stop()
        
        assert not receiver.is_running
    
    @pytest.mark.asyncio
    async def test_receiver_accepts_post_request(self, receiver):
        received_messages = []
        
        async def handler(msg: Message) -> Message | None:
            received_messages.append(msg)
            return msg
        
        receiver.set_message_handler(handler)
        await receiver.start()
        
        # Give server time to start
        await asyncio.sleep(0.2)
        
        # Send test request
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://127.0.0.1:18080/hl7",
                data=b"MSH|^~\\&|TEST|TEST|TEST|TEST|20240101||ADT^A01|1|P|2.5",
                headers={"Content-Type": "text/plain"}
            ) as response:
                assert response.status == 202
                message_id = await response.text()
                assert len(message_id) > 0
        
        # Give time for processing
        await asyncio.sleep(0.2)
        
        assert len(received_messages) == 1
        assert b"MSH|" in received_messages[0].raw
        
        await receiver.stop()
    
    @pytest.mark.asyncio
    async def test_receiver_rejects_wrong_content_type(self, receiver):
        await receiver.start()
        await asyncio.sleep(0.2)
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "http://127.0.0.1:18080/hl7",
                data=b"test",
                headers={"Content-Type": "application/json"}
            ) as response:
                assert response.status == 415  # Unsupported Media Type
        
        await receiver.stop()
    
    @pytest.mark.asyncio
    async def test_receiver_health_endpoint(self, receiver):
        await receiver.start()
        await asyncio.sleep(0.2)
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("http://127.0.0.1:18080/health") as response:
                assert response.status == 200
                data = await response.json()
                assert data["id"] == "test_http"
                assert data["healthy"] is True
        
        await receiver.stop()
