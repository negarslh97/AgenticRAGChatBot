"""
Unit tests for incremental synchronization logic in KnowledgeBaseRepository
"""

import pytest
import hashlib
from unittest.mock import Mock, patch
from app.infrastructure.knowledge_base_repository import KnowledgeBaseRepository


class TestIncrementalSync:
    """Test suite for incremental synchronization methods."""

    @pytest.fixture
    def repo(self):
        """Create repository instance for testing."""
        return KnowledgeBaseRepository()

    def test_calculate_content_hash_consistency(self, repo):
        """Test that content hash calculation is consistent."""
        node_properties1 = {
            'title': 'Test Title',
            'content': 'Test content',
            'level': 1,
            'path': '1',
            'order': 0,
            'parent_id': ''
        }

        node_properties2 = {
            'title': 'Test Title',
            'content': 'Test content',
            'level': 1,
            'path': '1',
            'order': 0,
            'parent_id': ''
        }

        # Same content should produce same hash
        hash1 = repo._calculate_content_hash(node_properties1)
        hash2 = repo._calculate_content_hash(node_properties2)

        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 32  # MD5 hash length

    def test_calculate_content_hash_different_content(self, repo):
        """Test that different content produces different hashes."""
        node_properties1 = {
            'title': 'Test Title',
            'content': 'Test content',
            'level': 1,
            'path': '1',
            'order': 0,
            'parent_id': ''
        }

        node_properties2 = {
            'title': 'Different Title',
            'content': 'Different content',
            'level': 1,
            'path': '1',
            'order': 0,
            'parent_id': ''
        }

        hash1 = repo._calculate_content_hash(node_properties1)
        hash2 = repo._calculate_content_hash(node_properties2)

        assert hash1 != hash2

    def test_detect_changes_no_changes(self, repo):
        """Test detecting no changes between identical node sets."""
        # Mock existing nodes
        existing_nodes = [
            {
                'node_id': 'node1',
                'title': 'Header 1',
                'content': 'Content 1',
                'level': 1,
                'path': '1',
                'order': 0,
                'parent_id': '',
                'weaviate_uuid': 'uuid1',
                'content_hash': 'hash1'
            }
        ]

        # Mock new nodes (identical content)
        class MockNode:
            def __init__(self, node_id, title, content, level, path, order, parent_id):
                self.id = node_id
                self.title = title
                self.content = content
                self.level = level
                self.path = path
                self.order = order
                self.parent_id = parent_id

        new_nodes = [
            MockNode('node1', 'Header 1', 'Content 1', 1, '1', 0, '')
        ]

        # Mock hash calculation to return expected hash
        with patch.object(repo, '_calculate_node_hash', return_value='hash1'):
            changes = repo._detect_changes(existing_nodes, new_nodes)

            assert changes['has_changes'] is False
            assert len(changes['to_add']) == 0
            assert len(changes['to_update']) == 0
            assert len(changes['to_delete']) == 0

    def test_detect_changes_only_additions(self, repo):
        """Test detecting only new nodes to add."""
        existing_nodes = [
            {
                'node_id': 'node1',
                'content_hash': 'hash1'
            }
        ]

        class MockNode:
            def __init__(self, node_id, title, content, level, path, order, parent_id):
                self.id = node_id
                self.title = title
                self.content = content
                self.level = level
                self.path = path
                self.order = order
                self.parent_id = parent_id

        new_nodes = [
            MockNode('node1', 'Header 1', 'Content 1', 1, '1', 0, ''),  # Same as existing
            MockNode('node2', 'Header 2', 'Content 2', 2, '1.1', 1, 'node1')  # New node
        ]

        with patch.object(repo, '_calculate_node_hash', return_value='hash1'):
            changes = repo._detect_changes(existing_nodes, new_nodes)

            assert changes['has_changes'] is True
            assert len(changes['to_add']) == 1
            assert len(changes['to_update']) == 0
            assert len(changes['to_delete']) == 0
            assert changes['to_add'][0].id == 'node2'

    def test_detect_changes_only_deletions(self, repo):
        """Test detecting only nodes to delete."""
        existing_nodes = [
            {
                'node_id': 'node1',
                'content_hash': 'hash1',
                'weaviate_uuid': 'uuid1'
            },
            {
                'node_id': 'node2',
                'content_hash': 'hash2',
                'weaviate_uuid': 'uuid2'
            }
        ]

        new_nodes = []  # All nodes deleted

        changes = repo._detect_changes(existing_nodes, new_nodes)

        assert changes['has_changes'] is True
        assert len(changes['to_add']) == 0
        assert len(changes['to_update']) == 0
        assert len(changes['to_delete']) == 2
        assert changes['to_delete'][0]['node_id'] == 'node1'
        assert changes['to_delete'][1]['node_id'] == 'node2'

    def test_detect_changes_only_updates(self, repo):
        """Test detecting only nodes to update."""
        existing_nodes = [
            {
                'node_id': 'node1',
                'content_hash': 'old_hash',
                'weaviate_uuid': 'uuid1'
            }
        ]

        class MockNode:
            def __init__(self, node_id, title, content, level, path, order, parent_id):
                self.id = node_id
                self.title = title
                self.content = content
                self.level = level
                self.path = path
                self.order = order
                self.parent_id = parent_id

        new_nodes = [
            MockNode('node1', 'Updated Header', 'Updated Content', 1, '1', 0, '')
        ]

        with patch.object(repo, '_calculate_node_hash', return_value='new_hash'):
            changes = repo._detect_changes(existing_nodes, new_nodes)

            assert changes['has_changes'] is True
            assert len(changes['to_add']) == 0
            assert len(changes['to_update']) == 1
            assert len(changes['to_delete']) == 0
            assert changes['to_update'][0]['existing']['node_id'] == 'node1'
            assert changes['to_update'][0]['new'].title == 'Updated Header'

    def test_detect_changes_mixed_operations(self, repo):
        """Test detecting a mix of additions, updates, and deletions."""
        existing_nodes = [
            {
                'node_id': 'node1',
                'content_hash': 'hash1',
                'weaviate_uuid': 'uuid1'
            },
            {
                'node_id': 'node2',
                'content_hash': 'old_hash2',
                'weaviate_uuid': 'uuid2'
            },
            {
                'node_id': 'node3',
                'content_hash': 'hash3',
                'weaviate_uuid': 'uuid3'
            }
        ]

        class MockNode:
            def __init__(self, node_id, title, content, level, path, order, parent_id):
                self.id = node_id
                self.title = title
                self.content = content
                self.level = level
                self.path = path
                self.order = order
                self.parent_id = parent_id

        new_nodes = [
            MockNode('node1', 'Header 1', 'Content 1', 1, '1', 0, ''),  # Unchanged
            MockNode('node2', 'Updated Header 2', 'Updated Content 2', 2, '1.1', 1, 'node1'),  # Updated
            MockNode('node4', 'New Header 4', 'New Content 4', 1, '2', 0, '')  # Added
            # node3 is deleted
        ]

        def mock_calculate_hash(node):
            if node.id == 'node1':
                return 'hash1'  # Unchanged
            elif node.id == 'node2':
                return 'new_hash2'  # Changed
            elif node.id == 'node4':
                return 'hash4'  # New
            return 'unknown'

        with patch.object(repo, '_calculate_node_hash', side_effect=mock_calculate_hash):
            changes = repo._detect_changes(existing_nodes, new_nodes)

            assert changes['has_changes'] is True
            assert len(changes['to_add']) == 1
            assert len(changes['to_update']) == 1
            assert len(changes['to_delete']) == 1

            # Check additions
            assert changes['to_add'][0].id == 'node4'

            # Check updates
            assert changes['to_update'][0]['existing']['node_id'] == 'node2'
            assert changes['to_update'][0]['new'].title == 'Updated Header 2'

            # Check deletions
            assert changes['to_delete'][0]['node_id'] == 'node3'

    def test_calculate_node_hash(self, repo):
        """Test node hash calculation for new nodes."""
        class MockNode:
            def __init__(self, node_id, title, content, level, path, order, parent_id):
                self.id = node_id
                self.title = title
                self.content = content
                self.level = level
                self.path = path
                self.order = order
                self.parent_id = parent_id

        node = MockNode('test_node', 'Test Title', 'Test content', 1, '1.2.3', 2, 'parent_1')

        hash1 = repo._calculate_node_hash(node)
        hash2 = repo._calculate_node_hash(node)

        # Same node should produce same hash
        assert hash1 == hash2
        assert isinstance(hash1, str)
        assert len(hash1) == 32

        # Different node should produce different hash
        different_node = MockNode('test_node', 'Different Title', 'Test content', 1, '1.2.3', 2, 'parent_1')
        different_hash = repo._calculate_node_hash(different_node)
        assert hash1 != different_hash

    def test_node_to_properties_conversion(self, repo):
        """Test conversion of node to Weaviate properties."""
        from app.domain.entities import KnowledgeBaseArticle

        # Mock article
        mock_article = Mock(spec=KnowledgeBaseArticle)
        mock_article.id = 'article_123'
        mock_article.content_markdown = '# Full content\n\nComplete markdown content'

        class MockNode:
            def __init__(self):
                self.id = 'node_456'
                self.title = 'Test Header'
                self.content = 'Test content'
                self.level = 2
                self.path = '1.2'
                self.order = 1
                self.parent_id = 'parent_node'

        node = MockNode()
        properties = repo._node_to_properties(node, mock_article)

        expected_properties = {
            "node_id": 'node_456',
            "article_id": 'article_123',
            "title": 'Test Header',
            "level": 2,
            "content": 'Test content',
            "parent_id": 'parent_node',
            "path": '1.2',
            "order": 1,
            "full_content": '# Full content\n\nComplete markdown content'
        }

        assert properties == expected_properties