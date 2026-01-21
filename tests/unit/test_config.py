"""
Unit tests for HIE Configuration system.
"""

import pytest
import tempfile
from pathlib import Path

from hie.core.config import (
    load_config,
    load_config_from_string,
    save_config,
    validate_config,
    parse_item_config,
    HIEConfig,
    HTTPReceiverConfig,
    FileReceiverConfig,
    MLLPSenderConfig,
    FileSenderConfig,
)
from hie.core.production import ProductionConfig
from hie.core.route import RouteConfig


class TestLoadConfig:
    """Tests for configuration loading."""
    
    def test_load_config_from_string(self):
        yaml_content = """
production:
  name: "Test Production"
  description: "Test description"

items:
  - id: test_receiver
    type: receiver.http
    port: 8080

routes:
  - id: test_route
    path: [test_receiver]
"""
        config = load_config_from_string(yaml_content)
        
        assert config.production.name == "Test Production"
        assert len(config.items) == 1
        assert config.items[0]["id"] == "test_receiver"
        assert len(config.routes) == 1
    
    def test_load_config_from_file(self):
        yaml_content = """
production:
  name: "File Test"

items: []
routes: []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            config = load_config(f.name)
            
            assert config.production.name == "File Test"
    
    def test_load_config_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/path/config.yaml")
    
    def test_load_empty_config(self):
        with pytest.raises(ValueError, match="Empty configuration"):
            load_config_from_string("")


class TestSaveConfig:
    """Tests for configuration saving."""
    
    def test_save_and_reload_config(self):
        config = HIEConfig(
            production=ProductionConfig(name="Save Test"),
            items=[{"id": "item1", "type": "receiver.http"}],
            routes=[RouteConfig(id="route1", path=["item1"])],
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            save_config(config, f.name)
            
            reloaded = load_config(f.name)
            
            assert reloaded.production.name == "Save Test"
            assert len(reloaded.items) == 1


class TestValidateConfig:
    """Tests for configuration validation."""
    
    def test_valid_config(self):
        config = HIEConfig(
            production=ProductionConfig(name="Valid"),
            items=[
                {"id": "receiver1", "type": "receiver.http"},
                {"id": "sender1", "type": "sender.mllp"},
            ],
            routes=[
                RouteConfig(id="route1", path=["receiver1", "sender1"])
            ],
        )
        
        errors = validate_config(config)
        assert len(errors) == 0
    
    def test_missing_item_id(self):
        config = HIEConfig(
            production=ProductionConfig(name="Invalid"),
            items=[{"type": "receiver.http"}],  # Missing id
            routes=[],
        )
        
        errors = validate_config(config)
        assert any("missing 'id'" in e for e in errors)
    
    def test_duplicate_item_id(self):
        config = HIEConfig(
            production=ProductionConfig(name="Invalid"),
            items=[
                {"id": "item1", "type": "receiver.http"},
                {"id": "item1", "type": "sender.mllp"},  # Duplicate
            ],
            routes=[],
        )
        
        errors = validate_config(config)
        assert any("Duplicate item ID" in e for e in errors)
    
    def test_route_references_unknown_item(self):
        config = HIEConfig(
            production=ProductionConfig(name="Invalid"),
            items=[{"id": "item1", "type": "receiver.http"}],
            routes=[
                RouteConfig(id="route1", path=["item1", "unknown_item"])
            ],
        )
        
        errors = validate_config(config)
        assert any("unknown item" in e for e in errors)
    
    def test_route_unknown_error_handler(self):
        config = HIEConfig(
            production=ProductionConfig(name="Invalid"),
            items=[{"id": "item1", "type": "receiver.http"}],
            routes=[
                RouteConfig(
                    id="route1",
                    path=["item1"],
                    error_handler="unknown_handler"
                )
            ],
        )
        
        errors = validate_config(config)
        assert any("unknown error handler" in e for e in errors)


class TestParseItemConfig:
    """Tests for item configuration parsing."""
    
    def test_parse_http_receiver_config(self):
        data = {
            "id": "http1",
            "type": "receiver.http",
            "host": "0.0.0.0",
            "port": 9090,
            "path": "/api/hl7",
        }
        
        config = parse_item_config(data)
        
        assert isinstance(config, HTTPReceiverConfig)
        assert config.id == "http1"
        assert config.port == 9090
        assert config.path == "/api/hl7"
    
    def test_parse_file_receiver_config(self):
        data = {
            "id": "file1",
            "type": "receiver.file",
            "watch_directory": "/data/inbound",
            "patterns": ["*.hl7", "*.csv"],
        }
        
        config = parse_item_config(data)
        
        assert isinstance(config, FileReceiverConfig)
        assert config.watch_directory == "/data/inbound"
        assert config.patterns == ["*.hl7", "*.csv"]
    
    def test_parse_mllp_sender_config(self):
        data = {
            "id": "mllp1",
            "type": "sender.mllp",
            "host": "downstream.example.com",
            "port": 2575,
            "timeout": 60.0,
        }
        
        config = parse_item_config(data)
        
        assert isinstance(config, MLLPSenderConfig)
        assert config.host == "downstream.example.com"
        assert config.port == 2575
        assert config.timeout == 60.0
    
    def test_parse_file_sender_config(self):
        data = {
            "id": "filesender1",
            "type": "sender.file",
            "output_directory": "/data/outbound",
            "filename_pattern": "{message_id}.hl7",
        }
        
        config = parse_item_config(data)
        
        assert isinstance(config, FileSenderConfig)
        assert config.output_directory == "/data/outbound"


class TestHIEConfig:
    """Tests for HIEConfig model."""
    
    def test_default_logging(self):
        config = HIEConfig(
            production=ProductionConfig(name="Test"),
        )
        
        assert config.logging["level"] == "INFO"
        assert config.logging["format"] == "json"
    
    def test_default_persistence(self):
        config = HIEConfig(
            production=ProductionConfig(name="Test"),
        )
        
        assert config.persistence["type"] == "memory"
    
    def test_custom_settings(self):
        config = HIEConfig(
            production=ProductionConfig(name="Test"),
            logging={"level": "DEBUG", "format": "console"},
            persistence={"type": "postgresql", "host": "localhost"},
        )
        
        assert config.logging["level"] == "DEBUG"
        assert config.persistence["type"] == "postgresql"
