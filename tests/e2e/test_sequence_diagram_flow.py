"""
End-to-End tests for Message Sequence Diagram feature
Tests the complete flow from message creation to visualization
"""

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime, timedelta


@pytest.mark.e2e
@pytest.mark.asyncio
class TestSequenceDiagramE2E:
    """
    End-to-end tests for IRIS HealthConnect-style sequence diagram
    """

    @pytest.fixture
    async def test_project(self, db_pool):
        """Create a test project with items"""
        project_id = uuid4()

        # Create project with 5 items in pipeline
        items = [
            {'name': 'PAS-In', 'type': 'service'},
            {'name': 'ValidateTransform', 'type': 'process'},
            {'name': 'ADT_Router', 'type': 'process'},
            {'name': 'EPR_Out', 'type': 'operation'},
            {'name': 'RIS_Out', 'type': 'operation'},
        ]

        # ... (database insertion code)

        return {'project_id': project_id, 'items': items}

    @pytest.fixture
    async def message_session(self, test_project, db_pool):
        """Create a complete message session flowing through pipeline"""
        project_id = test_project['project_id']
        session_id = f"E2E-TEST-{uuid4()}"
        base_time = datetime.utcnow()

        messages = []

        # Message 1: PAS-In → ValidateTransform
        messages.append({
            'project_id': project_id,
            'session_id': session_id,
            'item_name': 'PAS-In',
            'item_type': 'service',
            'source_item': None,
            'destination_item': 'ValidateTransform',
            'direction': 'inbound',
            'message_type': 'ADT^A01',
            'status': 'completed',
            'received_at': base_time,
            'completed_at': base_time + timedelta(milliseconds=450),
            'latency_ms': 450,
        })

        # Message 2: ValidateTransform → ADT_Router
        messages.append({
            'project_id': project_id,
            'session_id': session_id,
            'item_name': 'ValidateTransform',
            'item_type': 'process',
            'source_item': 'PAS-In',
            'destination_item': 'ADT_Router',
            'direction': 'internal',
            'message_type': 'HL7-to-FHIR',
            'status': 'completed',
            'received_at': base_time + timedelta(milliseconds=500),
            'completed_at': base_time + timedelta(milliseconds=1700),
            'latency_ms': 1200,
        })

        # Message 3: ADT_Router → EPR_Out
        messages.append({
            'project_id': project_id,
            'session_id': session_id,
            'item_name': 'ADT_Router',
            'item_type': 'process',
            'source_item': 'ValidateTransform',
            'destination_item': 'EPR_Out',
            'direction': 'internal',
            'message_type': 'ADT^A01',
            'status': 'completed',
            'received_at': base_time + timedelta(milliseconds=1700),
            'completed_at': base_time + timedelta(milliseconds=4900),
            'latency_ms': 3200,
        })

        # Message 4: ADT_Router → RIS_Out (parallel)
        messages.append({
            'project_id': project_id,
            'session_id': session_id,
            'item_name': 'ADT_Router',
            'item_type': 'process',
            'source_item': 'ValidateTransform',
            'destination_item': 'RIS_Out',
            'direction': 'internal',
            'message_type': 'ADT^A01',
            'status': 'completed',
            'received_at': base_time + timedelta(milliseconds=2000),
            'completed_at': base_time + timedelta(milliseconds=4800),
            'latency_ms': 2800,
        })

        # Insert messages into database
        # ... (database insertion code)

        return {
            'project_id': project_id,
            'session_id': session_id,
            'messages': messages,
            'expected_items': 5,  # All 5 items involved
            'expected_arrows': 4,  # 4 message flows
        }

    async def test_complete_sequence_diagram_flow(self, message_session, api_client):
        """
        Test complete end-to-end flow:
        1. Create messages in database
        2. Call session list API
        3. Verify session appears
        4. Call trace API
        5. Verify trace data structure
        6. Verify items and messages are correct
        """

        # Step 1: List sessions for project
        sessions_response = await api_client.get(
            f"/api/projects/{message_session['project_id']}/sessions"
        )

        assert sessions_response.status == 200
        sessions_data = await sessions_response.json()

        # Verify our session appears
        test_session = next(
            (s for s in sessions_data['sessions'] if s['session_id'] == message_session['session_id']),
            None
        )

        assert test_session is not None
        assert test_session['message_count'] == 4
        assert test_session['success_rate'] == 1.0  # All completed

        # Step 2: Get trace data for session
        trace_response = await api_client.get(
            f"/api/sessions/{message_session['session_id']}/trace"
        )

        assert trace_response.status == 200
        trace_data = await trace_response.json()

        # Step 3: Verify trace data structure
        assert trace_data['session_id'] == message_session['session_id']
        assert len(trace_data['messages']) == 4
        assert len(trace_data['items']) == 5  # All 5 items in pipeline

        # Step 4: Verify items are sorted correctly (service → process → operation)
        items = trace_data['items']
        item_types = [item['item_type'] for item in items]

        # Count by type
        assert item_types.count('service') == 1
        assert item_types.count('process') == 2
        assert item_types.count('operation') == 2

        # Verify service comes first
        assert item_types[0] == 'service'

        # Verify processes come before operations
        last_process_idx = max(i for i, t in enumerate(item_types) if t == 'process')
        first_operation_idx = min((i for i, t in enumerate(item_types) if t == 'operation'), default=len(item_types))
        assert last_process_idx < first_operation_idx

        # Step 5: Verify messages have correct source/destination
        messages = trace_data['messages']

        # First message should be from PAS-In
        assert any(m for m in messages if m['item_name'] == 'PAS-In')

        # Should have messages going to both EPR_Out and RIS_Out
        assert any(m for m in messages if m['destination_item'] == 'EPR_Out')
        assert any(m for m in messages if m['destination_item'] == 'RIS_Out')

        # Step 6: Verify time range
        assert trace_data['started_at'] is not None
        assert trace_data['ended_at'] is not None

        started = datetime.fromisoformat(trace_data['started_at'].replace('Z', '+00:00'))
        ended = datetime.fromisoformat(trace_data['ended_at'].replace('Z', '+00:00'))

        assert ended > started
        assert (ended - started).total_seconds() >= 4  # At least 4.9 seconds duration

    async def test_session_list_pagination(self, test_project, api_client):
        """Test session list pagination works correctly"""

        # Request first 5 sessions
        response = await api_client.get(
            f"/api/projects/{test_project['project_id']}/sessions?limit=5&offset=0"
        )

        assert response.status == 200
        data = await response.json()

        assert len(data['sessions']) <= 5

        # Request next page
        response2 = await api_client.get(
            f"/api/projects/{test_project['project_id']}/sessions?limit=5&offset=5"
        )

        assert response2.status == 200
        data2 = await response2.json()

        # Sessions should be different (no overlap)
        session_ids_page1 = {s['session_id'] for s in data['sessions']}
        session_ids_page2 = {s['session_id'] for s in data2['sessions']}

        assert session_ids_page1.isdisjoint(session_ids_page2)

    async def test_session_with_errors(self, test_project, db_pool, api_client):
        """Test that sessions with errors show correct success rate"""
        project_id = test_project['project_id']
        session_id = f"ERROR-TEST-{uuid4()}"

        # Create 10 messages: 7 successful, 3 failed
        messages = []
        base_time = datetime.utcnow()

        for i in range(10):
            status = 'failed' if i < 3 else 'completed'

            messages.append({
                'project_id': project_id,
                'session_id': session_id,
                'item_name': 'TestItem',
                'item_type': 'process',
                'status': status,
                'received_at': base_time + timedelta(seconds=i),
            })

        # Insert messages
        # ... (database insertion code)

        # Fetch session
        response = await api_client.get(
            f"/api/projects/{project_id}/sessions"
        )

        data = await response.json()
        test_session = next(
            (s for s in data['sessions'] if s['session_id'] == session_id),
            None
        )

        assert test_session is not None
        assert test_session['message_count'] == 10
        assert test_session['success_rate'] == 0.7  # 7 out of 10

    async def test_sequence_diagram_frontend_integration(self, message_session, browser):
        """
        Test frontend sequence diagram rendering (requires Playwright/Selenium)
        """
        # This would be a full browser test
        # Navigate to Messages page
        await browser.goto(f"http://localhost:3000/messages")

        # Wait for messages to load
        await browser.wait_for_selector('[data-testid="message-list"]')

        # Click Activity icon on first message
        await browser.click('[data-testid="sequence-diagram-btn"]')

        # Wait for sequence diagram modal
        await browser.wait_for_selector('[data-testid="sequence-diagram-modal"]')

        # Verify swimlanes are rendered
        swimlanes = await browser.query_selector_all('[data-testid="sequence-swimlane"]')
        assert len(swimlanes) == message_session['expected_items']

        # Verify arrows are rendered
        arrows = await browser.query_selector_all('[data-testid="sequence-arrow"]')
        assert len(arrows) == message_session['expected_arrows']

        # Verify zoom controls work
        await browser.click('[data-testid="zoom-in-btn"]')
        # ... (check zoom level changed)

        # Click export button
        await browser.click('[data-testid="export-btn"]')
        # ... (verify download initiated)


@pytest.mark.performance
async def test_sequence_diagram_performance(db_pool, api_client):
    """Test performance with large sessions (100+ messages)"""
    project_id = uuid4()
    session_id = f"PERF-TEST-{uuid4()}"

    # Create 100 messages
    messages = []
    base_time = datetime.utcnow()

    for i in range(100):
        messages.append({
            'project_id': project_id,
            'session_id': session_id,
            'item_name': f'Item-{i % 10}',
            'item_type': ['service', 'process', 'operation'][i % 3],
            'received_at': base_time + timedelta(milliseconds=i * 100),
        })

    # Insert messages
    # ... (database insertion code)

    # Measure API response time
    import time
    start = time.time()

    response = await api_client.get(f"/api/sessions/{session_id}/trace")

    end = time.time()
    duration = end - start

    assert response.status == 200
    assert duration < 1.0  # Should respond within 1 second

    data = await response.json()
    assert len(data['messages']) == 100


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'e2e'])
