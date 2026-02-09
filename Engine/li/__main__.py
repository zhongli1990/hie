"""
LI Engine CLI Entry Point

Runs the LI (Lightweight Integration) Engine with IRIS XML configuration.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import click
import structlog


def setup_logging(level: str = "INFO", format: str = "json") -> None:
    """Configure structured logging for LI Engine."""
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
@click.version_option(version="0.1.0", prog_name="LI Engine")
def main() -> None:
    """LI Engine - IRIS-Compatible Healthcare Integration Engine

    Enterprise-grade workflow orchestrator for NHS hospital trusts.
    """
    pass


@main.command()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True, path_type=Path),
    envvar="LI_CONFIG",
    help="Path to IRIS XML configuration file"
)
@click.option(
    "--log-level", "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    envvar="LI_LOG_LEVEL",
    help="Logging level"
)
@click.option(
    "--log-format", "-f",
    type=click.Choice(["json", "console"]),
    default="console",
    envvar="LI_LOG_FORMAT",
    help="Logging format"
)
def run(config: Path | None, log_level: str, log_format: str) -> None:
    """Run the LI Engine production from IRIS XML configuration."""
    setup_logging(log_level, log_format)
    logger = structlog.get_logger(__name__)

    if not config:
        logger.error("config_required", message="Configuration file required. Use --config or set LI_CONFIG environment variable")
        sys.exit(1)

    try:
        from Engine.li.config import IRISXMLLoader
        from Engine.li.engine.production import ProductionEngine

        # Load IRIS XML configuration
        logger.info("loading_config", path=str(config))
        loader = IRISXMLLoader()
        production_config = loader.load(config)

        # Create and run production
        logger.info(
            "starting_production",
            name=production_config.name,
            items=len(production_config.items)
        )

        production = ProductionEngine(production_config)

        # Run until interrupted
        asyncio.run(production.start())

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
    help="Path to IRIS XML configuration file"
)
def validate(config: Path) -> None:
    """Validate an IRIS XML configuration file."""
    setup_logging("INFO", "console")
    logger = structlog.get_logger(__name__)

    try:
        from Engine.li.config import IRISXMLLoader

        loader = IRISXMLLoader()
        production_config = loader.load(config)

        click.echo(click.style("✓ Configuration VALID", fg="green", bold=True))
        click.echo(f"  Production: {production_config.name}")
        click.echo(f"  Items: {len(production_config.items)}")

    except Exception as e:
        click.echo(click.style(f"✗ Configuration INVALID: {e}", fg="red"))
        sys.exit(1)


if __name__ == "__main__":
    main()
