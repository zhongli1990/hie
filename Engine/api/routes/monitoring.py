"""
Monitoring API Routes

Provides endpoints for real-time metrics, throughput, and system health data.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any
from uuid import UUID

from aiohttp import web
import structlog

logger = structlog.get_logger(__name__)


def setup_monitoring_routes(app: web.Application, db_pool) -> None:
    """Register monitoring routes."""
    
    async def get_monitoring_metrics(request: web.Request) -> web.Response:
        """Get real-time monitoring metrics.
        
        GET /api/monitoring/metrics
        
        Returns system-wide metrics including throughput, latency, error rate.
        """
        try:
            now = datetime.now(timezone.utc)
            one_hour_ago = now - timedelta(hours=1)
            five_min_ago = now - timedelta(minutes=5)
            
            # Get message throughput (messages per minute in last 5 min)
            throughput_result = await db_pool.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE received_at >= $2) as recent
                FROM portal_messages
                WHERE received_at >= $1
            """, one_hour_ago, five_min_ago)
            
            total_hour = throughput_result['total'] or 0
            recent_5min = throughput_result['recent'] or 0
            messages_per_second = recent_5min / 300 if recent_5min > 0 else 0  # 5 min = 300 sec
            
            # Get latency stats
            latency_result = await db_pool.fetchrow("""
                SELECT 
                    AVG(latency_ms) as avg_latency,
                    MAX(latency_ms) as max_latency,
                    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY latency_ms) as p99_latency
                FROM portal_messages
                WHERE received_at >= $1 AND latency_ms IS NOT NULL
            """, one_hour_ago)
            
            avg_latency = float(latency_result['avg_latency'] or 0)
            p99_latency = float(latency_result['p99_latency'] or 0)
            
            # Get error rate
            error_result = await db_pool.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE status IN ('failed', 'error')) as errors
                FROM portal_messages
                WHERE received_at >= $1
            """, one_hour_ago)
            
            total_msgs = error_result['total'] or 0
            error_count = error_result['errors'] or 0
            error_rate = (error_count / total_msgs * 100) if total_msgs > 0 else 0
            
            # Get queue depth (pending messages)
            queue_result = await db_pool.fetchrow("""
                SELECT COUNT(*) as pending
                FROM portal_messages
                WHERE status IN ('received', 'processing')
            """)
            queue_depth = queue_result['pending'] or 0
            
            return web.json_response({
                "messages_per_second": round(messages_per_second, 2),
                "avg_latency_ms": round(avg_latency, 1),
                "p99_latency_ms": round(p99_latency, 1),
                "error_rate": round(error_rate, 2),
                "queue_depth": queue_depth,
                "messages_last_hour": total_hour,
                "errors_last_hour": error_count,
                "timestamp": now.isoformat(),
            })
            
        except Exception as e:
            logger.error("monitoring_metrics_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=500)
    
    async def get_monitoring_throughput(request: web.Request) -> web.Response:
        """Get throughput time-series data for charts.
        
        GET /api/monitoring/throughput?minutes=30
        
        Returns per-minute message counts for the specified duration.
        """
        try:
            minutes = min(int(request.query.get("minutes", 30)), 60)
            now = datetime.now(timezone.utc)
            start_time = now - timedelta(minutes=minutes)
            
            # Get message counts per minute
            result = await db_pool.fetch("""
                SELECT 
                    date_trunc('minute', received_at) as minute,
                    COUNT(*) as count,
                    COUNT(*) FILTER (WHERE direction = 'inbound') as inbound,
                    COUNT(*) FILTER (WHERE direction = 'outbound') as outbound,
                    COUNT(*) FILTER (WHERE status IN ('failed', 'error')) as errors,
                    AVG(latency_ms) FILTER (WHERE latency_ms IS NOT NULL) as avg_latency
                FROM portal_messages
                WHERE received_at >= $1
                GROUP BY minute
                ORDER BY minute
            """, start_time)
            
            # Build time series with zero-fill for missing minutes
            data_map = {}
            for row in result:
                if row['minute']:
                    key = row['minute'].isoformat()
                    data_map[key] = {
                        "time": key,
                        "total": row['count'],
                        "inbound": row['inbound'],
                        "outbound": row['outbound'],
                        "errors": row['errors'],
                        "avg_latency": round(float(row['avg_latency'] or 0), 1),
                    }
            
            # Generate complete time series
            data_points = []
            current = start_time.replace(second=0, microsecond=0)
            while current <= now:
                key = current.isoformat()
                if key in data_map:
                    data_points.append(data_map[key])
                else:
                    data_points.append({
                        "time": key,
                        "total": 0,
                        "inbound": 0,
                        "outbound": 0,
                        "errors": 0,
                        "avg_latency": 0,
                    })
                current += timedelta(minutes=1)
            
            return web.json_response({
                "minutes": minutes,
                "data": data_points,
                "total_messages": sum(d['total'] for d in data_points),
                "total_errors": sum(d['errors'] for d in data_points),
            })
            
        except Exception as e:
            logger.error("monitoring_throughput_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=500)
    
    async def get_monitoring_items(request: web.Request) -> web.Response:
        """Get per-item metrics.
        
        GET /api/monitoring/items
        
        Returns metrics for each item (service/operation).
        """
        try:
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            
            # Get metrics per item
            result = await db_pool.fetch("""
                SELECT 
                    pm.item_name,
                    pi.item_type,
                    pm.direction,
                    COUNT(*) as message_count,
                    COUNT(*) FILTER (WHERE pm.status IN ('failed', 'error')) as error_count,
                    AVG(pm.latency_ms) FILTER (WHERE pm.latency_ms IS NOT NULL) as avg_latency,
                    MAX(pm.latency_ms) as max_latency
                FROM portal_messages pm
                LEFT JOIN project_items pi ON pi.name = pm.item_name
                WHERE pm.received_at >= $1
                GROUP BY pm.item_name, pi.item_type, pm.direction
                ORDER BY message_count DESC
            """, one_hour_ago)
            
            items = []
            for row in result:
                items.append({
                    "name": row['item_name'],
                    "type": row['item_type'] or "unknown",
                    "direction": row['direction'],
                    "message_count": row['message_count'],
                    "error_count": row['error_count'],
                    "avg_latency_ms": round(float(row['avg_latency'] or 0), 1),
                    "max_latency_ms": row['max_latency'] or 0,
                    "error_rate": round((row['error_count'] / row['message_count'] * 100) if row['message_count'] > 0 else 0, 2),
                })
            
            return web.json_response({
                "items": items,
                "total": len(items),
            })
            
        except Exception as e:
            logger.error("monitoring_items_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=500)
    
    async def get_monitoring_projects(request: web.Request) -> web.Response:
        """Get per-project metrics.
        
        GET /api/monitoring/projects
        
        Returns metrics for each project.
        """
        try:
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            five_min_ago = datetime.now(timezone.utc) - timedelta(minutes=5)
            
            # Get metrics per project
            result = await db_pool.fetch("""
                SELECT 
                    p.id,
                    p.name,
                    p.display_name,
                    p.state,
                    COUNT(pm.id) as message_count,
                    COUNT(pm.id) FILTER (WHERE pm.status IN ('failed', 'error')) as error_count,
                    COUNT(pm.id) FILTER (WHERE pm.received_at >= $2) as recent_count,
                    AVG(pm.latency_ms) FILTER (WHERE pm.latency_ms IS NOT NULL) as avg_latency
                FROM projects p
                LEFT JOIN portal_messages pm ON pm.project_id = p.id AND pm.received_at >= $1
                GROUP BY p.id
                ORDER BY message_count DESC
            """, one_hour_ago, five_min_ago)
            
            projects = []
            for row in result:
                msg_count = row['message_count'] or 0
                error_count = row['error_count'] or 0
                recent_count = row['recent_count'] or 0
                
                # Calculate messages per second (recent 5 min)
                msgs_per_sec = recent_count / 300 if recent_count > 0 else 0
                
                # Determine health status
                error_rate = (error_count / msg_count * 100) if msg_count > 0 else 0
                if error_rate > 5:
                    status = "critical"
                elif error_rate > 1:
                    status = "warning"
                else:
                    status = "healthy"
                
                projects.append({
                    "id": str(row['id']),
                    "name": row['display_name'] or row['name'],
                    "state": row['state'],
                    "messages_processed": msg_count,
                    "messages_per_second": round(msgs_per_sec, 2),
                    "avg_latency_ms": round(float(row['avg_latency'] or 0), 1),
                    "error_rate": round(error_rate, 2),
                    "status": status,
                })
            
            return web.json_response({
                "projects": projects,
                "total": len(projects),
            })
            
        except Exception as e:
            logger.error("monitoring_projects_failed", error=str(e))
            return web.json_response({"error": str(e)}, status=500)
    
    # Register routes
    app.router.add_get("/api/monitoring/metrics", get_monitoring_metrics)
    app.router.add_get("/api/monitoring/throughput", get_monitoring_throughput)
    app.router.add_get("/api/monitoring/items", get_monitoring_items)
    app.router.add_get("/api/monitoring/projects", get_monitoring_projects)
    
    logger.info("monitoring_routes_registered")
