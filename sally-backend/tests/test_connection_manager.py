"""
Tests for the connection manager implementation.
"""

import threading
import time
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.infrastructure.connection_manager import (
    WeaviateConnectionManager,
    MongoDBConnectionManager,
    cleanup_all_connections
)


class TestWeaviateConnectionManager:
    """Test cases for WeaviateConnectionManager"""
    
    def setup_method(self):
        """Reset singleton before each test"""
        WeaviateConnectionManager.reset_instance()
    
    def test_singleton_pattern(self):
        """Test that singleton pattern works correctly"""
        mgr1 = WeaviateConnectionManager()
        mgr2 = WeaviateConnectionManager()
        assert mgr1 is mgr2
    
    def test_singleton_reset(self):
        """Test that singleton reset works"""
        mgr1 = WeaviateConnectionManager()
        WeaviateConnectionManager.reset_instance()
        mgr2 = WeaviateConnectionManager()
        assert mgr1 is not mgr2
    
    def test_connection_pooling_logic(self):
        """Test that connection pooling logic works correctly"""
        mgr = WeaviateConnectionManager()
        
        # Mock the client creation
        mock_client = MagicMock()
        mock_client.is_ready.return_value = True
        
        # Directly set the client instead of mocking _create_client
        mgr._client = mock_client
        mgr._connection_birth_time = time.time()
        
        with patch.object(mgr, '_is_client_healthy', return_value=True):
            with patch.object(mgr, '_perform_health_check') as mock_health:
                with patch.object(mgr, '_is_ready', return_value=True):
                    mock_health.return_value = True
                    
                    # Get a client
                    client1 = mgr.get_client()
                    assert client1 is mock_client
                    assert mgr._connection_count == 1
                    
                    # Release the client but don't let it close the connection
                    with patch.object(mgr, 'close_client'):
                        mgr.release()
                        assert mgr._connection_count == 0
                        # Client should be in pool, not None
                        assert mgr._client is mock_client
                        assert len(mgr._connection_pool) == 1
    
    def test_thread_safety(self):
        """Test that connection pool operations are thread-safe"""
        mgr = WeaviateConnectionManager()
        
        # Mock the client creation
        mock_client = MagicMock()
        mock_client.is_ready.return_value = True
        
        with patch.object(mgr, '_create_client') as mock_create:
            with patch.object(mgr, '_is_client_healthy', return_value=True):
                mock_create.return_value = mock_client
                
                results = []
                
                def get_and_release():
                    for _ in range(5):
                        client = mgr.get_client()
                        mgr.release()
                        results.append(mgr._connection_count)
                
                # Create multiple threads
                threads = []
                for _ in range(3):
                    t = threading.Thread(target=get_and_release)
                    threads.append(t)
                    t.start()
                
                # Wait for all threads to complete
                for t in threads:
                    t.join()
                
                # Check that counts are consistent
                assert all(count >= 0 for count in results)
    
    def test_close_client_clears_pool(self):
        """Test that close_client clears the connection pool"""
        mgr = WeaviateConnectionManager()
        mgr._connection_pool = [MagicMock(), MagicMock()]
        
        mgr.close_client()
        
        assert len(mgr._connection_pool) == 0
        assert mgr._client is None


class TestMongoDBConnectionManager:
    """Test cases for MongoDBConnectionManager"""
    
    def setup_method(self):
        """Reset singleton before each test"""
        MongoDBConnectionManager.reset_instance()
    
    def test_singleton_pattern(self):
        """Test that singleton pattern works correctly"""
        mgr1 = MongoDBConnectionManager()
        mgr2 = MongoDBConnectionManager()
        assert mgr1 is mgr2
    
    def test_singleton_reset(self):
        """Test that singleton reset works"""
        mgr1 = MongoDBConnectionManager()
        MongoDBConnectionManager.reset_instance()
        mgr2 = MongoDBConnectionManager()
        assert mgr1 is not mgr2
    
    def test_connection_pooling_logic(self):
        """Test that connection pooling logic works correctly"""
        mgr = MongoDBConnectionManager()
        
        # Mock the client creation
        mock_client = MagicMock()
        
        # Directly set the client instead of mocking _create_client
        mgr._client = mock_client
        mgr._connection_birth_time = time.time()
        
        with patch.object(mgr, '_is_client_healthy', return_value=True):
            with patch.object(mgr, '_perform_health_check') as mock_health:
                mock_health.return_value = True
                
                # Get a client
                client1 = mgr.get_client()
                assert client1 is mock_client
                assert mgr._connection_count == 1
                
                # Release the client but don't let it close the connection
                with patch.object(mgr, 'close_client'):
                    mgr.release()
                    assert mgr._connection_count == 0
                    # Client should be in pool, not None
                    assert mgr._client is mock_client
                    assert len(mgr._connection_pool) == 1
    
    def test_thread_safety(self):
        """Test that connection pool operations are thread-safe"""
        mgr = MongoDBConnectionManager()
        
        # Mock the client creation
        mock_client = MagicMock()
        
        with patch.object(mgr, '_create_client') as mock_create:
            with patch.object(mgr, '_is_client_healthy', return_value=True):
                mock_create.return_value = mock_client
                
                results = []
                
                def get_and_release():
                    for _ in range(5):
                        client = mgr.get_client()
                        mgr.release()
                        results.append(mgr._connection_count)
                
                # Create multiple threads
                threads = []
                for _ in range(3):
                    t = threading.Thread(target=get_and_release)
                    threads.append(t)
                    t.start()
                
                # Wait for all threads to complete
                for t in threads:
                    t.join()
                
                # Check that counts are consistent
                assert all(count >= 0 for count in results)
    
    def test_close_client_clears_pool(self):
        """Test that close_client clears the connection pool"""
        mgr = MongoDBConnectionManager()
        mgr._connection_pool = [MagicMock(), MagicMock()]
        
        mgr.close_client()
        
        assert len(mgr._connection_pool) == 0
        assert mgr._client is None


class TestResourceMonitor:
    """Test cases for ResourceMonitor"""
    
    def test_get_connection_stats(self):
        """Test that get_connection_stats works"""
        from app.infrastructure.connection_manager import ResourceMonitor
        
        stats = ResourceMonitor.get_connection_stats()
        
        assert 'weaviate' in stats
        assert 'mongodb' in stats
        assert 'memory' in stats
        assert 'timestamp' in stats
        assert 'overall_health' in stats


class TestCleanupFunctions:
    """Test cases for cleanup functions"""
    
    def test_cleanup_all_connections(self):
        """Test that cleanup_all_connections works"""
        # Mock the connection managers
        with patch('app.infrastructure.connection_manager.WeaviateConnectionManager') as mock_weaviate:
            with patch('app.infrastructure.connection_manager.MongoDBConnectionManager') as mock_mongodb:
                mock_weaviate_instance = MagicMock()
                mock_mongodb_instance = MagicMock()
                mock_weaviate.return_value = mock_weaviate_instance
                mock_mongodb.return_value = mock_mongodb_instance
                
                cleanup_all_connections()
                
                mock_weaviate_instance.close_client.assert_called_once()
                mock_mongodb_instance.close_client.assert_called_once()


if __name__ == "__main__":
    test_weaviate = TestWeaviateConnectionManager()
    test_mongodb = TestMongoDBConnectionManager()
    test_resource = TestResourceMonitor()
    test_cleanup = TestCleanupFunctions()
    
    # Run tests
    test_weaviate.test_singleton_pattern()
    test_weaviate.test_singleton_reset()
    test_weaviate.test_connection_pooling_logic()
    test_weaviate.test_thread_safety()
    test_weaviate.test_close_client_clears_pool()
    
    test_mongodb.test_singleton_pattern()
    test_mongodb.test_singleton_reset()
    test_mongodb.test_connection_pooling_logic()
    test_mongodb.test_thread_safety()
    test_mongodb.test_close_client_clears_pool()
    
    test_resource.test_get_connection_stats()
    test_cleanup.test_cleanup_all_connections()
    
    print("All tests passed!")