"""
HIE Command Line Interface

Provides commands for running and managing HIE productions.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
import structlog

from Engine.core.config import load_config, validate_config


def setup_logging(level: str = "INFO", format: str = "json") -> None:
    """Configure structured logging."""
    import logging
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if format == "json" else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, level.upper()),
        stream=sys.stdout,
    )


@click.group()
@click.version_option(version="0.1.0", prog_name="HIE")
def main() -> None:
    """HIE - Healthcare Integration Engine
    
    Enterprise-grade healthcare messaging platform.
    """
    pass


@main.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to configuration file"
)
@click.option(
    "--log-level", "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level"
)
@click.option(
    "--log-format", "-f",
    type=click.Choice(["json", "console"]),
    default="console",
    help="Logging format"
)
def run(config: Path, log_level: str, log_format: str) -> None:
    """Run an HIE production from a configuration file."""
    setup_logging(log_level, log_format)
    logger = structlog.get_logger(__name__)
    
    try:
        # Load configuration
        logger.info("loading_config", path=str(config))
        hie_config = load_config(config)
        
        # Validate configuration
        errors = validate_config(hie_config)
        if errors:
            for error in errors:
                logger.error("config_error", error=error)
            sys.exit(1)
        
        # Create and run production
        from Engine.core.production import Production
        from Engine.factory import create_production_from_config
        
        production = create_production_from_config(hie_config)
        
        logger.info(
            "starting_production",
            name=production.name,
            items=len(production.items),
            routes=len(production.routes)
        )
        
        # Run until interrupted
        asyncio.run(production.run_forever())
        
    except FileNotFoundError as e:
        logger.error("config_not_found", error=str(e))
        sys.exit(1)
    except Exception as e:
        logger.exception("fatal_error", error=str(e))
        sys.exit(1)


@main.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Path to configuration file"
)
def validate(config: Path) -> None:
    """Validate a configuration file."""
    setup_logging("INFO", "console")
    logger = structlog.get_logger(__name__)
    
    try:
        hie_config = load_config(config)
        errors = validate_config(hie_config)
        
        if errors:
            click.echo(click.style("Configuration INVALID:", fg="red", bold=True))
            for error in errors:
                click.echo(click.style(f"  • {error}", fg="red"))
            sys.exit(1)
        else:
            click.echo(click.style("Configuration VALID", fg="green", bold=True))
            click.echo(f"  Production: {hie_config.production.name}")
            click.echo(f"  Items: {len(hie_config.items)}")
            click.echo(f"  Routes: {len(hie_config.routes)}")
    
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        sys.exit(1)


@main.command()
@click.option(
    "--output", "-o",
    type=click.Path(path_type=Path),
    default=Path("hie-config.yaml"),
    help="Output file path"
)
def init(output: Path) -> None:
    """Generate a sample configuration file."""
    sample_config = '''# HIE Configuration
# Healthcare Integration Engine

production:
  name: "Sample Production"
  description: "A sample HIE production configuration"
  enabled: true
  auto_start_items: true
  auto_start_routes: true
  graceful_shutdown_timeout: 30.0
  health_check_interval: 10.0

items:
  # HTTP Receiver - accepts HL7v2 messages via REST
  - id: http_receiver
    type: receiver.http
    name: "HTTP HL7 Receiver"
    enabled: true
    host: "0.0.0.0"
    port: 8080
    path: "/hl7"
    methods: ["POST"]
    content_types:
      - "application/hl7-v2"
      - "x-application/hl7-v2+er7"
      - "text/plain"
    
  # File Receiver - watches directory for files
  - id: file_receiver
    type: receiver.file
    name: "File Receiver"
    enabled: true
    watch_directory: "/data/inbound"
    patterns: ["*.hl7", "*.txt", "*.csv"]
    poll_interval: 1.0
    move_to: "/data/processed"
    
  # Passthrough Processor - for testing
  - id: passthrough
    type: processor.passthrough
    name: "Passthrough"
    enabled: true
    
  # MLLP Sender - sends HL7v2 to downstream system
  - id: mllp_sender
    type: sender.mllp
    name: "MLLP Sender"
    enabled: true
    host: "downstream.example.com"
    port: 2575
    timeout: 30.0
    max_connections: 5
    
  # File Sender - writes messages to files
  - id: file_sender
    type: sender.file
    name: "File Sender"
    enabled: true
    output_directory: "/data/outbound"
    filename_pattern: "{message_id}.hl7"

routes:
  # Route HTTP messages through to MLLP
  - id: http_to_mllp
    name: "HTTP to MLLP Route"
    enabled: true
    path: [http_receiver, passthrough, mllp_sender]
    
  # Route file messages to file output
  - id: file_to_file
    name: "File to File Route"
    enabled: true
    path: [file_receiver, passthrough, file_sender]

logging:
  level: "INFO"
  format: "json"

persistence:
  type: "memory"
'''
    
    if output.exists():
        if not click.confirm(f"File {output} exists. Overwrite?"):
            return
    
    output.write_text(sample_config)
    click.echo(click.style(f"Created sample configuration: {output}", fg="green"))


@main.command()
def version() -> None:
    """Show version information."""
    from hie import __version__
    click.echo(f"HIE - Healthcare Integration Engine v{__version__}")
    click.echo("Enterprise-grade healthcare messaging platform")


if __name__ == "__main__":
    main()
