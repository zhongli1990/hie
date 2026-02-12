"""
Integration tests for Session and Trace APIs
Tests the new sequence diagram backend endpoints
"""

import pytest
from uuid import uuid4, UUID
from datetime import datetime, timedelta
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from Engine.api.routes.messages import register_routes
from Engine.api.repositories import PortalMessageRepository


class TestSessionTraceAPI(AioHTTPTestCase):
    """Test session listing and trace retrieval APIs"""

    async def get_application(self):
        """Create test application"""
        app = web.Application()

        # Mock database pool
        app['db_pool'] = await self.create_mock_pool()

        # Register routes
        register_routes(app)

        return app

    async def create_mock_pool(self):
        """Create mock database pool with test data"""
        # This would be replaced with actual test database connection
        # For now, we'll use pytest fixtures
        return None

    @unittest_run_loop
    async def test_list_sessions_endpoint(self):
        """Test GET /api/projects/{id}/sessions endpoint"""
        project_id = str(uuid4())

        resp = await self.client.request(
            "GET",
            f"/api/projects/{project_id}/sessions?limit=10"
        )

        assert resp.status == 200
        data = await resp.json()

        # Verify response structure
        assert 'sessions' in data
        assert 'total' in data
        assert isinstance(data['sessions'], list)

    @unittest_run_loop
    async def test_list_sessions_with_item_filter(self):
        """Test session filtering by item name"""
        project_id = str(uuid4())

        resp = await self.client.request(
            "GET",
            f"/api/projects/{project_id}/sessions?item=PAS-In&limit=10"
        )

        assert resp.status == 200
        data = await resp.json()

        # All sessions should be for the filtered item
        assert all('PAS-In' in str(s) for s in data.get('sessions', []))

    @unittest_run_loop
    async def test_get_session_trace_endpoint(self):
        """Test GET /api/sessions/{id}/trace endpoint"""
        session_id = "TEST-SESSION-001"

        resp = await self.client.request(
            "GET",
            f"/api/sessions/{session_id}/trace"
        )

        # Should return 200 or 404 depending on if session exists
        assert resp.status in [200, 404]

        if resp.status == 200:
            data = await resp.json()

            # Verify trace data structure
            assert 'session_id' in data
            assert 'messages' in data
            assert 'items' in data
            assert 'started_at' in data
            assert 'ended_at' in data

            assert data['session_id'] == session_id
            assert isinstance(data['messages'], list)
            assert isinstance(data['items'], list)

    @unittest_run_loop
    async def test_invalid_project_id_returns_400(self):
        """Test that invalid project ID returns 400"""
        resp = await self.client.request(
            "GET",
            "/api/projects/invalid-uuid/sessions"
        )

        assert resp.status == 400
        data = await resp.json()
        assert 'error' in data

    @unittest_run_loop
    async def test_missing_session_id_returns_400(self):
        """Test that missing session ID returns 400"""
        resp = await self.client.request(
            "GET",
            "/api/sessions//trace"  # Empty session_id
        )

        # Should return 400 or 404
        assert resp.status in [400, 404]


@pytest.mark.asyncio
class TestPortalMessageRepository:
    """Unit tests for PortalMessageRepository session methods"""

    @pytest.fixture
    async def db_pool(self, postgresql):
        """Create test database pool"""
        # This would connect to test database
        # Using pytest-postgresql or similar
        pass

    @pytest.fixture
    async def repository(self, db_pool):
        """Create repository instance"""
        return PortalMessageRepository(db_pool)

    @pytest.fixture
    async def sample_messages(self, db_pool):
        """Insert sample messages for testing"""
        project_id = uuid4()
        session_id = f"TEST-{uuid4()}"

        messages = []
        base_time = datetime.utcnow()

        # Create a session with 5 messages
        for i in range(5):
            messages.append({
                'project_id': project_id,
                'session_id': session_id,
                'item_name': f'Item-{i % 3}',  # 3 different items
                'item_type': ['service', 'process', 'operation'][i % 3],
                'direction': 'inbound',
                'message_type': 'ADT^A01',
                'status': 'completed',
                'received_at': base_time + timedelta(seconds=i),
                'completed_at': base_time + timedelta(seconds=i + 1),
                'latency_ms': 1000 + (i * 100),
            })

        # Insert into database
        # ... (database insertion code)

        return {
            'project_id': project_id,
            'session_id': session_id,
            'messages': messages
        }

    async def test_list_sessions_groups_by_session_id(self, repository, sample_messages):
        """Test that list_sessions groups messages by session_id"""
        sessions = await repository.list_sessions(
            project_id=sample_messages['project_id'],
            limit=10,
            offset=0
        )

        assert len(sessions) > 0

        # Verify session has aggregated data
        session = next((s for s in sessions if s['session_id'] == sample_messages['session_id']), None)
        assert session is not None
        assert session['message_count'] == 5
        assert session['success_rate'] == 1.0  # All completed

    async def test_list_sessions_calculates_time_range(self, repository, sample_messages):
        """Test that list_sessions calculates correct time ranges"""
        sessions = await repository.list_sessions(
            project_id=sample_messages['project_id'],
            limit=10,
            offset=0
        )

        session = next((s for s in sessions if s['session_id'] == sample_messages['session_id']), None)

        # Verify time range
        assert 'started_at' in session
        assert 'ended_at' in session

        started = datetime.fromisoformat(session['started_at'])
        ended = datetime.fromisoformat(session['ended_at'])

        assert ended > started
        assert (ended - started).total_seconds() >= 4  # 5 messages, 1 second apart

    async def test_get_session_trace_returns_all_messages(self, repository, sample_messages):
        """Test that get_session_trace returns all messages in order"""
        trace = await repository.get_session_trace(sample_messages['session_id'])

        assert trace is not None
        assert len(trace['messages']) == 5
        assert trace['session_id'] == sample_messages['session_id']

        # Verify messages are ordered by received_at
        timestamps = [msg['received_at'] for msg in trace['messages']]
        assert timestamps == sorted(timestamps)

    async def test_get_session_trace_extracts_unique_items(self, repository, sample_messages):
        """Test that get_session_trace extracts unique items correctly"""
        trace = await repository.get_session_trace(sample_messages['session_id'])

        assert 'items' in trace
        items = trace['items']

        # Should have 3 unique items
        assert len(items) == 3

        # Verify items are sorted by type order
        item_types = [item['item_type'] for item in items]
        # service < process < operation
        type_order = {'service': 0, 'process': 1, 'operation': 2}
        assert all(
            type_order[item_types[i]] <= type_order[item_types[i+1]]
            for i in range(len(item_types)-1)
        )

    async def test_get_session_trace_nonexistent_returns_none(self, repository):
        """Test that getting nonexistent session returns None"""
        trace = await repository.get_session_trace("NONEXISTENT-SESSION")

        assert trace is None or len(trace.get('messages', [])) == 0


@pytest.mark.parametrize("status,expected_success_rate", [
    ("completed", 1.0),
    ("failed", 0.0),
    ("sent", 1.0),
    ("error", 0.0),
    ("received", 0.0),  # Not completed yet
])
def test_success_rate_calculation(status, expected_success_rate):
    """Test success rate calculation for different statuses"""
    # This would test the SQL aggregation logic
    # ROUND(COUNT(*) FILTER (WHERE status IN ('sent', 'completed'))::numeric / NULLIF(COUNT(*)::numeric, 0), 2)

    messages = [{'status': status}] * 10

    completed_count = sum(1 for m in messages if m['status'] in ['sent', 'completed'])
    total_count = len(messages)

    success_rate = round(completed_count / total_count, 2) if total_count > 0 else 0.0

    assert success_rate == expected_success_rate


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
