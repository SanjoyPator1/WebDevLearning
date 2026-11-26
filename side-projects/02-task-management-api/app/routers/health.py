"""
Health check endpoints for system monitoring

This module provides:
- Application health status
- Database health checks
- System metrics and monitoring
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from app.services.database_health import database_health_service
from app.database.engine import db_manager

router = APIRouter(prefix="/health", tags=["Health Checks"])

@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Basic application health check
    
    Returns:
        Basic health status and application information
    """
    return {
        'status': 'healthy',
        'service': 'Task Management API',
        'version': '1.0.0',
        'database_initialized': db_manager._initialized
    }

@router.get("/database")
async def database_health_check() -> Dict[str, Any]:
    """
    Comprehensive database health check
    
    Returns:
        Detailed database health status with metrics
    """
    health_result = await database_health_service.perform_health_check()
    
    # Return appropriate HTTP status based on health
    if health_result['status'] == 'unhealthy':
        raise HTTPException(
            status_code=503,
            detail={
                'message': 'Database is unhealthy',
                'health_check': health_result
            }
        )
    
    return health_result

@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed system health check including all components
    
    Returns:
        Comprehensive health status for all system components
    """
    # Get database health
    db_health = await database_health_service.perform_health_check()
    
    # Get application metrics
    app_health = {
        'status': 'healthy',
        'uptime_seconds': 0,  # You can implement uptime tracking
        'memory_usage': 'Available via system monitoring',
        'active_connections': db_manager.engine.pool.checkedout() if db_manager.engine else 0
    }
    
    # Combine all health checks
    overall_status = 'healthy'
    if db_health['status'] == 'unhealthy':
        overall_status = 'unhealthy'
    elif db_health['status'] == 'warning':
        overall_status = 'warning'
    
    return {
        'overall_status': overall_status,
        'timestamp': db_health['timestamp'],
        'components': {
            'database': db_health,
            'application': app_health
        }
    }