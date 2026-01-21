"""
Unit tests for HIE Route model.
"""

import pytest
import asyncio

from hie.core.route import (
    Route,
    RouteConfig,
    RouteState,
    FilterConfig,
    FilterOperator,
    RouteMetrics,
)
from hie.core.item import Item, ItemConfig, ItemType, Processor
from hie.core.message import Message, Priority


class SimpleProcessor(Processor):
    """Simple processor for testing."""
    
    def __init__(self, config: ItemConfig):
        super().__init__(config)
        self.processed = []
    
    async def _process(self, message: Message) -> Message:
        self.processed.append(message)
        return message


class TestFilterConfig:
    """Tests for FilterConfig."""
    
    def test_equals_filter(self):
        filter_cfg = FilterConfig(
            field="envelope.message_type",
            operator=FilterOperator.EQUALS,
            value="ADT^A01"
        )
        
        msg = Message.create(raw=b"test", message_type="ADT^A01")
        assert filter_cfg.evaluate(msg) is True
        
        msg2 = Message.create(raw=b"test", message_type="ADT^A02")
        assert filter_cfg.evaluate(msg2) is False
    
    def test_not_equals_filter(self):
        filter_cfg = FilterConfig(
            field="envelope.message_type",
            operator=FilterOperator.NOT_EQUALS,
            value="ADT^A01"
        )
        
        msg = Message.create(raw=b"test", message_type="ADT^A02")
        assert filter_cfg.evaluate(msg) is True
    
    def test_contains_filter(self):
        filter_cfg = FilterConfig(
            field="envelope.message_type",
            operator=FilterOperator.CONTAINS,
            value="ADT"
        )
        
        msg = Message.create(raw=b"test", message_type="ADT^A01")
        assert filter_cfg.evaluate(msg) is True
        
        msg2 = Message.create(raw=b"test", message_type="ORU^R01")
        assert filter_cfg.evaluate(msg2) is False
    
    def test_starts_with_filter(self):
        filter_cfg = FilterConfig(
            field="envelope.message_type",
            operator=FilterOperator.STARTS_WITH,
            value="ADT"
        )
        
        msg = Message.create(raw=b"test", message_type="ADT^A01")
        assert filter_cfg.evaluate(msg) is True
    
    def test_in_filter(self):
        filter_cfg = FilterConfig(
            field="envelope.message_type",
            operator=FilterOperator.IN,
            value=["ADT^A01", "ADT^A02", "ADT^A03"]
        )
        
        msg = Message.create(raw=b"test", message_type="ADT^A01")
        assert filter_cfg.evaluate(msg) is True
        
        msg2 = Message.create(raw=b"test", message_type="ORU^R01")
        assert filter_cfg.evaluate(msg2) is False
    
    def test_priority_filter(self):
        filter_cfg = FilterConfig(
            field="envelope.priority",
            operator=FilterOperator.EQUALS,
            value=Priority.URGENT
        )
        
        msg = Message.create(raw=b"test", priority=Priority.URGENT)
        assert filter_cfg.evaluate(msg) is True


class TestRouteConfig:
    """Tests for RouteConfig."""
    
    def test_default_config(self):
        config = RouteConfig(
            id="test_route",
            path=["item1", "item2"]
        )
        
        assert config.id == "test_route"
        assert config.path == ["item1", "item2"]
        assert config.enabled is True
        assert config.ordered is False
    
    def test_config_with_filters(self):
        config = RouteConfig(
            id="filtered_route",
            path=["item1", "item2"],
            filters=[
                FilterConfig(
                    field="envelope.message_type",
                    operator=FilterOperator.EQUALS,
                    value="ADT^A01"
                )
            ],
            filter_mode="all"
        )
        
        assert len(config.filters) == 1
        assert config.filter_mode == "all"


class TestRouteMetrics:
    """Tests for RouteMetrics."""
    
    def test_record_entered(self):
        metrics = RouteMetrics()
        
        metrics.record_entered()
        
        assert metrics.messages_entered == 1
        assert metrics.messages_in_flight == 1
    
    def test_record_completed(self):
        metrics = RouteMetrics()
        metrics.record_entered()
        
        metrics.record_completed(100.0)
        
        assert metrics.messages_completed == 1
        assert metrics.messages_in_flight == 0
        assert metrics.avg_latency_ms == 100.0
    
    def test_record_failed(self):
        metrics = RouteMetrics()
        metrics.record_entered()
        
        metrics.record_failed()
        
        assert metrics.messages_failed == 1
        assert metrics.messages_in_flight == 0
    
    def test_record_filtered(self):
        metrics = RouteMetrics()
        
        metrics.record_filtered()
        
        assert metrics.messages_filtered == 1


class TestRoute:
    """Tests for Route class."""
    
    @pytest.fixture
    def items(self):
        """Create test items."""
        item1 = SimpleProcessor(ItemConfig(id="item1", item_type=ItemType.PROCESSOR))
        item2 = SimpleProcessor(ItemConfig(id="item2", item_type=ItemType.PROCESSOR))
        item3 = SimpleProcessor(ItemConfig(id="item3", item_type=ItemType.PROCESSOR))
        return {"item1": item1, "item2": item2, "item3": item3}
    
    @pytest.fixture
    def route_config(self):
        return RouteConfig(
            id="test_route",
            name="Test Route",
            path=["item1", "item2", "item3"]
        )
    
    @pytest.fixture
    def route(self, route_config):
        return Route(route_config)
    
    def test_route_properties(self, route, route_config):
        assert route.id == "test_route"
        assert route.name == "Test Route"
        assert route.state == RouteState.CREATED
        assert route.config == route_config
    
    def test_route_bind_items(self, route, items):
        route.bind_items(items)
        
        # Items should be bound (internal state)
        assert len(route._items) == 3
    
    def test_route_bind_missing_item(self, route):
        items = {"item1": SimpleProcessor(ItemConfig(id="item1", item_type=ItemType.PROCESSOR))}
        
        with pytest.raises(ValueError, match="Item not found"):
            route.bind_items(items)
    
    @pytest.mark.asyncio
    async def test_route_start_stop(self, route, items):
        route.bind_items(items)
        
        await route.start()
        assert route.state == RouteState.RUNNING
        assert route.is_running is True
        
        await route.stop()
        assert route.state == RouteState.STOPPED
    
    @pytest.mark.asyncio
    async def test_route_pause_resume(self, route, items):
        route.bind_items(items)
        await route.start()
        
        await route.pause()
        assert route.state == RouteState.PAUSED
        
        await route.resume()
        assert route.state == RouteState.RUNNING
        
        await route.stop()
    
    def test_route_accepts_no_filters(self, route, items):
        route.bind_items(items)
        
        msg = Message.create(raw=b"test", message_type="ANY")
        assert route.accepts(msg) is True
    
    def test_route_accepts_with_filter_match(self, items):
        config = RouteConfig(
            id="filtered",
            path=["item1", "item2"],
            filters=[
                FilterConfig(
                    field="envelope.message_type",
                    operator=FilterOperator.EQUALS,
                    value="ADT^A01"
                )
            ]
        )
        route = Route(config)
        route.bind_items(items)
        
        msg = Message.create(raw=b"test", message_type="ADT^A01")
        assert route.accepts(msg) is True
        
        msg2 = Message.create(raw=b"test", message_type="ORU^R01")
        assert route.accepts(msg2) is False
    
    def test_route_accepts_filter_mode_any(self, items):
        config = RouteConfig(
            id="filtered",
            path=["item1", "item2"],
            filters=[
                FilterConfig(
                    field="envelope.message_type",
                    operator=FilterOperator.EQUALS,
                    value="ADT^A01"
                ),
                FilterConfig(
                    field="envelope.message_type",
                    operator=FilterOperator.EQUALS,
                    value="ORU^R01"
                )
            ],
            filter_mode="any"
        )
        route = Route(config)
        route.bind_items(items)
        
        msg1 = Message.create(raw=b"test", message_type="ADT^A01")
        msg2 = Message.create(raw=b"test", message_type="ORU^R01")
        msg3 = Message.create(raw=b"test", message_type="OTHER")
        
        assert route.accepts(msg1) is True
        assert route.accepts(msg2) is True
        assert route.accepts(msg3) is False
    
    def test_route_health_check(self, route, items):
        route.bind_items(items)
        
        health = route.health_check()
        
        assert health["id"] == "test_route"
        assert health["name"] == "Test Route"
        assert health["state"] == "created"
        assert health["path"] == ["item1", "item2", "item3"]
        assert "metrics" in health
    
    @pytest.mark.asyncio
    async def test_route_cannot_submit_when_not_running(self, route, items):
        route.bind_items(items)
        
        msg = Message.create(raw=b"test")
        
        with pytest.raises(RuntimeError, match="Cannot submit"):
            await route.submit(msg)
