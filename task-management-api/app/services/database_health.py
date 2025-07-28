"""
Database health check and monitoring service

This module provides:
- Database connectivity checks
- Query performance monitoring
- Connection pool status
- Migration status verification
"""

import time
import logging
from typing import Dict, Any, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.database.engine import db_manager
from app.models import User  # Test with a simple model

logger = logging.getLogger(__name__)

class DatabaseHealthService:
    """
    Service for monitoring database health and performance
    
    Provides comprehensive health checks including connectivity,
    query performance, and system status monitoring.
    """
    
    async def perform_health_check(self) -> Dict[str, Any]:
        """
        Perform comprehensive database health check
        
        Returns:
            Dictionary with health check results and metrics
        """
        health_status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'checks': {}
        }
        
        try:
            # Test basic connectivity
            connectivity_result = await self._check_connectivity()
            health_status['checks']['connectivity'] = connectivity_result
            
            # Test query performance
            performance_result = await self._check_query_performance()
            health_status['checks']['performance'] = performance_result
            
            # Check connection pool status
            pool_result = await self._check_connection_pool()
            health_status['checks']['connection_pool'] = pool_result
            
            # Verify migration status
            migration_result = await self._check_migration_status()
            health_status['checks']['migrations'] = migration_result
            
            # Determine overall health status
            if any(check['status'] == 'unhealthy' for check in health_status['checks'].values()):
                health_status['status'] = 'unhealthy'
            elif any(check['status'] == 'warning' for check in health_status['checks'].values()):
                health_status['status'] = 'warning'
                
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            health_status['status'] = 'unhealthy'
            health_status['error'] = str(e)
        
        return health_status
    
    async def _check_connectivity(self) -> Dict[str, Any]:
        """
        Test basic database connectivity
        
        Returns:
            Connectivity check results
        """
        start_time = time.time()
        
        try:
            async with db_manager.session_factory() as session:
                # Simple connectivity test
                result = await session.execute(text("SELECT 1 as test"))
                test_value = result.scalar()
                
                if test_value == 1:
                    return {
                        'status': 'healthy',
                        'response_time_ms': round((time.time() - start_time) * 1000, 2),
                        'message': 'Database connection successful'
                    }
                else:
                    return {
                        'status': 'unhealthy',
                        'message': 'Unexpected query result'
                    }
                    
        except SQLAlchemyError as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Database connection failed'
            }
    
    async def _check_query_performance(self) -> Dict[str, Any]:
        """
        Test query performance with sample operations
        
        Returns:
            Performance check results with timing metrics
        """
        start_time = time.time()
        
        try:
            async with db_manager.session_factory() as session:
                # Test query performance with count operation
                query_start = time.time()
                result = await session.execute(text("SELECT COUNT(*) FROM users"))
                user_count = result.scalar()
                query_time = (time.time() - query_start) * 1000
                
                # Performance thresholds (in milliseconds)
                if query_time < 100:
                    status = 'healthy'
                elif query_time < 500:
                    status = 'warning'
                else:
                    status = 'unhealthy'
                
                return {
                    'status': status,
                    'query_time_ms': round(query_time, 2),
                    'total_time_ms': round((time.time() - start_time) * 1000, 2),
                    'user_count': user_count,
                    'message': f'Query completed in {query_time:.2f}ms'
                }
                
        except SQLAlchemyError as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Query performance test failed'
            }
    
    async def _check_connection_pool(self) -> Dict[str, Any]:
        """
        Check connection pool status and metrics
        
        Returns:
            Connection pool health information
        """
        try:
            if not db_manager.engine:
                return {
                    'status': 'unhealthy',
                    'message': 'Database engine not initialized'
                }
            
            pool = db_manager.engine.pool
            
            # Get pool statistics
            pool_status = {
                'status': 'healthy',
                'size': pool.size(),
                'checked_in': pool.checkedin(),
                'checked_out': pool.checkedout(),
                'overflow': pool.overflow(),
                'message': 'Connection pool is healthy'
            }
            
            # Check for potential issues
            utilization = (pool.checkedout() / pool.size()) * 100 if pool.size() > 0 else 0
            
            if utilization > 90:
                pool_status['status'] = 'warning'
                pool_status['message'] = f'High pool utilization: {utilization:.1f}%'
            elif utilization > 95:
                pool_status['status'] = 'unhealthy'
                pool_status['message'] = f'Critical pool utilization: {utilization:.1f}%'
            
            pool_status['utilization_percent'] = round(utilization, 1)
            
            return pool_status
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Connection pool check failed'
            }
    
    async def _check_migration_status(self) -> Dict[str, Any]:
        """
        Verify database migration status
        
        Returns:
            Migration status information
        """
        try:
            async with db_manager.session_factory() as session:
                # Check if alembic_version table exists
                result = await session.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'alembic_version'
                    )
                """))
                
                has_alembic_table = result.scalar()
                
                if not has_alembic_table:
                    return {
                        'status': 'warning',
                        'message': 'No migration history found (fresh database?)',
                        'current_revision': None
                    }
                
                # Get current migration revision
                result = await session.execute(text("SELECT version_num FROM alembic_version"))
                current_revision = result.scalar()
                
                return {
                    'status': 'healthy',
                    'current_revision': current_revision,
                    'message': f'Database at revision: {current_revision}'
                }
                
        except SQLAlchemyError as e:
            return {
                'status': 'unhealthy',
                'error': str(e),
                'message': 'Migration status check failed'
            }

# Global service instance
database_health_service = DatabaseHealthService()