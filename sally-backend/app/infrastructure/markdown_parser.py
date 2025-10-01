"""
Markdown Parser for Tree Structure Extraction

This module provides functionality to parse markdown content and extract
hierarchical tree structure based on heading levels (#, ##, ###, etc.)
"""

import re
import uuid
from typing import List, Dict, Any, Optional, Tuple
from app.domain.entities import MarkdownNode, MarkdownTree


class MarkdownParser:
    """Parser for extracting tree structure from markdown content."""

    def __init__(self):
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

    def parse_to_tree(self, markdown_content: str, article_id: str, article_title: str = None) -> MarkdownTree:
        """
        Parse markdown content into a hierarchical tree structure.

        Args:
            markdown_content: The markdown content to parse
            article_id: ID of the article this tree belongs to
            article_title: Title of the article from MongoDB (will be root node)

        Returns:
            MarkdownTree: Hierarchical tree structure with article title as root
        """
        lines = markdown_content.split('\n')
        nodes = []
        current_node = None
        content_buffer = []
        
        # محتوای قبل از اولین heading را برای root node ذخیره می‌کنیم
        preamble_content = []

        i = 0
        first_heading_found = False
        
        while i < len(lines):
            line = lines[i]

            # Check if this line is a heading
            heading_match = self.heading_pattern.match(line.strip())

            if heading_match:
                first_heading_found = True
                
                # Save content for previous node if exists
                if current_node:
                    current_node.content = '\n'.join(content_buffer).strip()
                    nodes.append(current_node)

                # Create new node for this heading (level + 1 چون root در level 0 است)
                level = len(heading_match.group(1)) + 1
                title = heading_match.group(2).strip()

                current_node = MarkdownNode(
                    id=str(uuid.uuid4()),
                    title=title,
                    level=level,
                    content="",  # Will be filled later
                    parent_id=None,  # Will be set later
                    path="",  # Will be set later
                    order=0  # Will be set later
                )

                content_buffer = []
            else:
                # Add line to current content buffer
                if not first_heading_found:
                    preamble_content.append(line)
                else:
                    content_buffer.append(line)

            i += 1

        # Don't forget the last node
        if current_node:
            current_node.content = '\n'.join(content_buffer).strip()
            nodes.append(current_node)

        # ✅ ایجاد Root Node با عنوان مقاله از MongoDB
        root_node = MarkdownNode(
            id=str(uuid.uuid4()),
            title=article_title or "مقاله",  # عنوان از MongoDB یا پیش‌فرض
            level=0,  # Root node همیشه level 0
            content='\n'.join(preamble_content).strip(),  # محتوای قبل از اولین heading
            parent_id="-1",  # Root has no parent
            path="0",
            order=0
        )

        # Build hierarchical structure with root
        tree = self._build_hierarchy_with_root(root_node, nodes)
        tree.article_id = article_id

        return tree

    def _build_hierarchy_with_root(self, root_node: MarkdownNode, nodes: List[MarkdownNode]) -> MarkdownTree:
        """
        Build hierarchical structure with a root node and child nodes.

        Args:
            root_node: The root node (article title from MongoDB)
            nodes: Flat list of all markdown heading nodes

        Returns:
            MarkdownTree: Hierarchical tree structure
        """
        # همه nodes فرزندان root هستند
        parent_stack = [(0, root_node)]  # شروع با root node
        
        for i, node in enumerate(nodes):
            node.order = i + 1  # Root node is order 0

            # Find the appropriate parent for this node
            parent = self._find_parent(node, parent_stack)

            if parent:
                node.parent_id = parent.id
                parent.children.append(node)
            else:
                # اگر parent پیدا نشد، root را parent قرار بده
                node.parent_id = root_node.id
                root_node.children.append(node)
                parent = root_node

            # Update parent stack
            # Remove parents that are at the same level or higher
            while parent_stack and parent_stack[-1][0] >= node.level:
                parent_stack.pop()

            # Add current node as potential parent
            parent_stack.append((node.level, node))

            # Set path
            node.path = self._calculate_path(node, parent_stack)

        # Return tree with single root node
        return MarkdownTree(article_id="", root_nodes=[root_node])
    
    def _build_hierarchy(self, nodes: List[MarkdownNode]) -> MarkdownTree:
        """
        Build hierarchical structure from flat list of nodes (legacy method).

        Args:
            nodes: Flat list of all markdown nodes

        Returns:
            MarkdownTree: Hierarchical tree structure
        """
        if not nodes:
            return MarkdownTree(article_id="", root_nodes=[])

        # Sort nodes by their position in the document (we'll use their order in the list)
        # and group by level
        level_groups = {}
        for i, node in enumerate(nodes):
            node.order = i
            if node.level not in level_groups:
                level_groups[node.level] = []
            level_groups[node.level].append(node)

        # Build hierarchy starting from level 1
        root_nodes = []
        parent_stack = []  # Stack to keep track of parents: [(level, node), ...]

        for node in nodes:
            # Find the appropriate parent for this node
            parent = self._find_parent(node, parent_stack)

            if parent:
                node.parent_id = parent.id
                parent.children.append(node)
            else:
                # This is a root node
                node.parent_id = "-1"
                root_nodes.append(node)

            # Update parent stack
            # Remove parents that are at the same level or higher
            while parent_stack and parent_stack[-1][0] >= node.level:
                parent_stack.pop()

            # Add current node as potential parent
            parent_stack.append((node.level, node))

            # Set path
            node.path = self._calculate_path(node, parent_stack)

        return MarkdownTree(article_id="", root_nodes=root_nodes)

    def _find_parent(self, node: MarkdownNode, parent_stack: List[Tuple[int, MarkdownNode]]) -> Optional[MarkdownNode]:
        """
        Find the parent node for the given node.

        Args:
            node: Node to find parent for
            parent_stack: Stack of potential parents

        Returns:
            Parent node or None if this should be a root node
        """
        # Parent should be the last node with level = current_level - 1
        for level, parent_node in reversed(parent_stack):
            if level == node.level - 1:
                return parent_node

        return None

    def _calculate_path(self, node: MarkdownNode, parent_stack: List[Tuple[int, MarkdownNode]]) -> str:
        """
        Calculate the path for a node based on its position in hierarchy.

        Args:
            node: Node to calculate path for
            parent_stack: Current parent stack

        Returns:
            Path string like "1.2.3"
        """
        if not parent_stack:
            return "1"

        # Build path by following parent chain
        path_parts = []
        current = node

        # Find the immediate parent
        parent = None
        for level, parent_node in reversed(parent_stack):
            if level == node.level - 1:
                parent = parent_node
                break

        if parent and parent.path:
            # Count siblings at this level under the same parent
            sibling_count = 1
            if parent.children:
                sibling_count = len([child for child in parent.children if child.order <= node.order])

            path_parts = parent.path.split('.') + [str(sibling_count)]
        else:
            # This is a root level node
            root_count = len([n for n in parent_stack if n[0] == 1]) + 1
            path_parts = [str(root_count)]

        return '.'.join(path_parts)

    def extract_headings_only(self, markdown_content: str) -> List[Dict[str, Any]]:
        """
        Extract only headings from markdown content without building full tree.

        Args:
            markdown_content: Markdown content

        Returns:
            List of heading dictionaries
        """
        headings = []

        for match in self.heading_pattern.finditer(markdown_content):
            level = len(match.group(1))
            title = match.group(2).strip()
            start_pos = match.start()

            headings.append({
                'level': level,
                'title': title,
                'position': start_pos
            })

        return headings

    def get_table_of_contents(self, markdown_content: str) -> str:
        """
        Generate table of contents from markdown headings.

        Args:
            markdown_content: Markdown content

        Returns:
            Table of contents as markdown string
        """
        headings = self.extract_headings_only(markdown_content)

        if not headings:
            return ""

        toc_lines = ["# Table of Contents\n"]

        for heading in headings:
            indent = "  " * (heading['level'] - 1)
            link = f"#{heading['title'].lower().replace(' ', '-')}"
            toc_lines.append(f"{indent}- [{heading['title']}]({link})")

        return "\n".join(toc_lines)


# Global instance
markdown_parser = MarkdownParser()
