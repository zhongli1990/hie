"""
Dashboard API Routes

Provides endpoints for dashboard statistics, throughput, and activity data.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from aiohttp import web
import structlog

logger = structlog.get_logger(__name__)


def setup_dashboard_routes(app: web.Application, db_pool) -> None:
    """Register dashboard routes."""
    
    async def get_dashboard_stats(request: web.Request) -> web.Response:
        """Get dashboard statistics.
        
        GET /api/dashboard/stats
        
        Returns:
            - projects_count: Total projects
            - projects_running: Running projects
            - items_count: Total items
            - messages_today: Messages processed today
            - messages_total: Total messages
            - error_rate: Error rate (0-1)
            - uptime_percent: System uptime percentage
        """
        try:
            # Get project counts
            projects_result = await db_pool.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE state = 'running') as running
                FROM projects
            """)
            
            # Get item counts
            items_result = await db_pool.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE item_type = 'service') as services,
                    COUNT(*) FILTER (WHERE item_type = 'process') as processes,
                    COUNT(*) FILTER (WHERE item_type = 'operation') as operations
                FROM project_items
            """)
            
            # Get message stats from portal_messages
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            messages_result = await db_pool.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE received_at >= $1) as today,
                    COUNT(*) FILTER (WHERE status IN ('failed', 'error')) as failed,
                    COUNT(*) FILTER (WHERE status IN ('failed', 'error') AND received_at >= $1) as failed_today
                FROM portal_messages
            """, today_start)
            
            # Calculate error rate
            total_today = messages_result['today'] or 0
            failed_today = messages_result['failed_today'] or 0
            error_rate = (failed_today / total_today) if total_today > 0 else 0
            
            # Calculate message trend (compare to yesterday)
            yesterday_start = today_start - timedelta(days=1)
            yesterday_result = await db_pool.fetchrow("""
                SELECT COUNT(*) as count
                FROM portal_messages
                WHERE received_at >= $1 AND received_at < $2
            """, yesterday_start, today_start)
            yesterday_count = yesterday_result['count'] or 0
            
            if yesterday_count > 0:
                message_trend = ((total_today - yesterday_count) / yesterday_count) * 100
            else:
                message_trend = 0 if total_today == 0 else 100
            
            return web.json_response({
                "projects_count": projects_result['total'] or 0,
                "projects_running": projects_result['running'] or 0,
                "items_count": items_result['total'] or 0,
                "items_services": items_result['services'] or 0,
                "items_processes": items_result['processes'] or 0,
                "items_operations": items_result['operations'] or 0,
                "messages_today": total_today,
                "messages_total": messages_result['total'] or 0,
                "messages_failed": messages_result['failed'] or 0,
                "error_rate": round(error_rate, 4),
                "message_trend": round(message_trend, 1),
                "uptime_percent": 99.9,  # TODO: Calculate from health checks
            })
            
        except Exception as e:
            logger.error("dashboard_stats_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=500)
    
    async def get_dashboard_throughput(request: web.Request) -> web.Response:
        """Get message throughput data for charts.
        
        GET /api/dashboard/throughput?period=1h
        
        Returns time-series data for throughput visualization.
        """
        try:
            period = request.query.get("period", "1h")
            
            # Determine time range and bucket size
            now = datetime.now(timezone.utc)
            if period == "1h":
                start_time = now - timedelta(hours=1)
                bucket_minutes = 5
            elif period == "6h":
                start_time = now - timedelta(hours=6)
                bucket_minutes = 15
            elif period == "24h":
                start_time = now - timedelta(hours=24)
                bucket_minutes = 60
            else:
                start_time = now - timedelta(hours=1)
                bucket_minutes = 5
            
            # Get message counts per bucket
            result = await db_pool.fetch("""
                SELECT 
                    date_trunc('minute', received_at) - 
                        (EXTRACT(minute FROM received_at)::integer % $3) * interval '1 minute' as bucket,
                    COUNT(*) as count,
                    COUNT(*) FILTER (WHERE direction = 'inbound') as inbound,
                    COUNT(*) FILTER (WHERE direction = 'outbound') as outbound
                FROM portal_messages
                WHERE received_at >= $1 AND received_at <= $2
                GROUP BY bucket
                ORDER BY bucket
            """, start_time, now, bucket_minutes)
            
            # Format for chart
            data_points = []
            for row in result:
                data_points.append({
                    "time": row['bucket'].isoformat() if row['bucket'] else None,
                    "total": row['count'],
                    "inbound": row['inbound'],
                    "outbound": row['outbound'],
                })
            
            # Calculate peak and average
            counts = [dp['total'] for dp in data_points] if data_points else [0]
            peak = max(counts) if counts else 0
            avg = sum(counts) / len(counts) if counts else 0
            
            return web.json_response({
                "period": period,
                "bucket_minutes": bucket_minutes,
                "data": data_points,
                "peak": peak,
                "average": round(avg, 1),
            })
            
        except Exception as e:
            logger.error("dashboard_throughput_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=500)
    
    async def get_dashboard_activity(request: web.Request) -> web.Response:
        """Get recent activity feed.
        
        GET /api/dashboard/activity?limit=10
        
        Returns recent messages and events.
        """
        try:
            limit = min(int(request.query.get("limit", 10)), 50)
            
            # Get recent messages
            result = await db_pool.fetch("""
                SELECT 
                    pm.id,
                    pm.message_type,
                    pm.item_name,
                    pm.direction,
                    pm.status,
                    pm.received_at,
                    pm.error_message,
                    p.name as project_name,
                    p.display_name as project_display_name
                FROM portal_messages pm
                JOIN projects p ON pm.project_id = p.id
                ORDER BY pm.received_at DESC
                LIMIT $1
            """, limit)
            
            activities = []
            for row in result:
                # Determine activity type
                if row['status'] in ('failed', 'error'):
                    activity_type = "error"
                    description = row['error_message'] or f"{row['message_type'] or 'Message'} failed"
                else:
                    activity_type = "message"
                    msg_type = row['message_type'] or 'Message'
                    if row['direction'] == 'inbound':
                        description = f"{msg_type} received successfully"
                    else:
                        description = f"{msg_type} sent successfully"
                
                activities.append({
                    "id": str(row['id']),
                    "type": activity_type,
                    "description": description,
                    "project_name": row['project_display_name'] or row['project_name'],
                    "item_name": row['item_name'],
                    "timestamp": row['received_at'].isoformat() if row['received_at'] else None,
                })
            
            return web.json_response({
                "activities": activities,
                "total": len(activities),
            })
            
        except Exception as e:
            logger.error("dashboard_activity_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=500)
    
    async def get_dashboard_projects(request: web.Request) -> web.Response:
        """Get projects overview with items for tree view.
        
        GET /api/dashboard/projects
        
        Returns projects with their items and message counts.
        """
        try:
            # Get projects with item counts
            projects = await db_pool.fetch("""
                SELECT 
                    p.id,
                    p.name,
                    p.display_name,
                    p.state,
                    p.enabled,
                    COUNT(DISTINCT i.id) as items_count
                FROM projects p
                LEFT JOIN project_items i ON i.project_id = p.id
                GROUP BY p.id
                ORDER BY p.display_name, p.name
            """)
            
            result = []
            for proj in projects:
                # Get items for this project
                items = await db_pool.fetch("""
                    SELECT 
                        i.id,
                        i.name,
                        i.item_type,
                        i.enabled,
                        i.class_name
                    FROM project_items i
                    WHERE i.project_id = $1
                    ORDER BY i.item_type, i.name
                """, proj['id'])
                
                # Get message counts per item
                msg_counts = await db_pool.fetch("""
                    SELECT 
                        item_name,
                        COUNT(*) as count,
                        COUNT(*) FILTER (WHERE status IN ('failed', 'error')) as errors
                    FROM portal_messages
                    WHERE project_id = $1
                    GROUP BY item_name
                """, proj['id'])
                
                msg_count_map = {r['item_name']: {'count': r['count'], 'errors': r['errors']} for r in msg_counts}
                
                # Build items list
                items_list = []
                for item in items:
                    counts = msg_count_map.get(item['name'], {'count': 0, 'errors': 0})
                    items_list.append({
                        "id": str(item['id']),
                        "name": item['name'],
                        "type": item['item_type'],
                        "enabled": item['enabled'],
                        "class_name": item['class_name'],
                        "message_count": counts['count'],
                        "error_count": counts['errors'],
                    })
                
                # Calculate project totals
                total_messages = sum(i['message_count'] for i in items_list)
                total_errors = sum(i['error_count'] for i in items_list)
                
                result.append({
                    "id": str(proj['id']),
                    "name": proj['name'],
                    "display_name": proj['display_name'],
                    "state": proj['state'],
                    "enabled": proj['enabled'],
                    "items_count": proj['items_count'],
                    "message_count": total_messages,
                    "error_count": total_errors,
                    "items": items_list,
                })
            
            return web.json_response({
                "projects": result,
                "total": len(result),
            })
            
        except Exception as e:
            logger.error("dashboard_projects_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=500)
    
    # Register routes
    app.router.add_get("/api/dashboard/stats", get_dashboard_stats)
    app.router.add_get("/api/dashboard/throughput", get_dashboard_throughput)
    app.router.add_get("/api/dashboard/activity", get_dashboard_activity)
    app.router.add_get("/api/dashboard/projects", get_dashboard_projects)
    
    logger.info("dashboard_routes_registered")
