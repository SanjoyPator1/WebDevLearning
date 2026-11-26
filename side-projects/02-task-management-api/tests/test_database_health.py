"""
Test database health check functionality

This module tests:
- Database connectivity checks
- Performance monitoring
- Connection pool status
- Migration status verification
"""

import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.database_health import DatabaseHealthService

class TestDatabaseHealth:
    """Test database health check service"""
    
    @pytest.fixture
    def health_service(self):
        """Create health service instance"""
        return DatabaseHealthService()
    
    async def test_connectivity_check_success(self, health_service: DatabaseHealthService, db_session: AsyncSession):
        """Test successful connectivity check"""
        with patch('app.database.engine.db_manager.session_factory') as mock_factory:
            mock_factory.return_value.__aenter__.return_value = db_session
            
            result = await health_service._check_connectivity()
            
            assert result['status'] == 'healthy'
            assert 'response_time_ms' in result
            assert result['message'] == 'Database connection successful'
    
    async def test_performance_check(self, health_service: DatabaseHealthService, db_session: AsyncSession):
        """Test query performance check"""
        with patch('app.database.engine.db_manager.session_factory') as mock_factory:
            mock_factory.return_value.__aenter__.return_value = db_session
            
            result = await health_service._check_query_performance()
            
            assert result['status'] in ['healthy', 'warning']
            assert 'query_time_ms' in result
            assert 'user_count' in result
    
    async def test_full_health_check(self, health_service: DatabaseHealthService):
        """Test comprehensive health check"""
        # Mock all individual check methods
        with patch.object(health_service, '_check_connectivity') as mock_conn, \
             patch.object(health_service, '_check_query_performance') as mock_perf, \
             patch.object(health_service, '_check_connection_pool') as mock_pool, \
             patch.object(health_service, '_check_migration_status') as mock_migration:
            
            # Set up mock responses
            mock_conn.return_value = {'status': 'healthy'}
            mock_perf.return_value = {'status': 'healthy'}
            mock_pool.return_value = {'status': 'healthy'}
            mock_migration.return_value = {'status': 'healthy'}
            
            result = await health_service.perform_health_check()
            
            assert result['status'] == 'healthy'
            assert 'timestamp' in result
            assert 'checks' in result
            assert len(result['checks']) == 4
    
    async def test_unhealthy_status_propagation(self, health_service: DatabaseHealthService):
        """Test that unhealthy status propagates to overall health"""
        with patch.object(health_service, '_check_connectivity') as mock_conn, \
             patch.object(health_service, '_check_query_performance') as mock_perf, \
             patch.object(health_service, '_check_connection_pool') as mock_pool, \
             patch.object(health_service, '_check_migration_status') as mock_migration:
            
            # Set one check as unhealthy
            mock_conn.return_value = {'status': 'unhealthy'}
            mock_perf.return_value = {'status': 'healthy'}
            mock_pool.return_value = {'status': 'healthy'}
            mock_migration.return_value = {'status': 'healthy'}
            
            result = await health_service.perform_health_check()
            
            assert result['status'] == 'unhealthy'