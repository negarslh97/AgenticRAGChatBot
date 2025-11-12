"""
Markdown Parser for Tree Structure Extraction

This module provides functionality to parse markdown content and extract
hierarchical tree structure based on heading levels (#, ##, ###, etc.)

🆕 Enhanced with Smart Chunking:
- Maximum chunk size limit (configurable)
- Chunk overlap for context preservation
- Semantic chunking for better retrieval
"""

import re
import uuid
import logging
from typing import List, Dict, Any, Optional, Tuple
from app.domain.entities import MarkdownNode, MarkdownTree

logger = logging.getLogger(__name__)


class MarkdownParser:
    """Parser for extracting tree structure from markdown content with smart chunking."""

    def __init__(
        self, 
        max_chunk_size: int = 512,   # 🔥 OPTIMIZED: حداکثر اندازه chunk (کاراکتر) - کاهش یافته برای دقت بالاتر
        chunk_overlap: int = 50       # 🔥 OPTIMIZED: همپوشانی بین chunks (کاراکتر) - برای حفظ پیوستگی
    ):
        """
        Initialize parser with chunking parameters.
        
        🔥 SMALL-TO-BIG RETRIEVAL STRATEGY:
        - chunk_size=512: قطعات کوچکتر برای دقت بالاتر در جستجو
        - chunk_overlap=50: همپوشانی برای حفظ context بین chunks
        
        Args:
            max_chunk_size: حداکثر تعداد کاراکتر در هر chunk
            chunk_overlap: تعداد کاراکتر همپوشانی بین chunks متوالی
        """
        self.heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

    def parse_to_tree(self, markdown_content: str, article_id: str, article_title: str = None, filename: str = None) -> MarkdownTree:
        """
        Parse markdown content into a hierarchical tree structure.

        Args:
            markdown_content: The markdown content to parse
            article_id: ID of the article this tree belongs to
            article_title: Title of the article from MongoDB (fallback)
            filename: Original filename for fallback title extraction

        Returns:
            MarkdownTree: Hierarchical tree structure with actual H1 as root
        """
        lines = markdown_content.split('\n')
        nodes = []
        current_node = None
        content_buffer = []
        
        # محتوای قبل از اولین heading را برای root node ذخیره می‌کنیم
        preamble_content = []
        
        # برای استخراج عنوان اصلی (H1) از markdown
        main_title = None
        root_content = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            line_stripped = line.strip()

            # Check if this line is a heading
            heading_match = self.heading_pattern.match(line_stripped)

            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                
                # Save content for previous node if exists
                if current_node:
                    current_node.content = '\n'.join(content_buffer).strip()
                    nodes.append(current_node)
                    content_buffer = []

                # Check if this is the first H1 heading
                if level == 1 and main_title is None:
                    # First H1 found - this becomes the main article title
                    main_title = title
                    # Content before this H1 goes to root
                    root_content = preamble_content.copy()
                    # Don't create a node for this H1 - it becomes the root
                else:
                    # This is a regular heading (H2+ or second H1+) - create a node
                    # Adjust level to be relative to root (H2 should be level 1 when H1 exists)
                    actual_level = level
                    if main_title is not None:
                        # If H1 exists, shift down by 1 (H2->1, H3->2, etc.)
                        actual_level = level - 1
                    else:
                        # If no H1 found, shift down by 2 (H2->1, H3->2, etc.)
                        actual_level = level - 2
                    
                    current_node = MarkdownNode(
                        id=str(uuid.uuid4()),
                        title=title,
                        level=actual_level,
                        content="",  # Will be filled later
                        parent_id=None,
                        path="",
                        order=0
                    )

            else:
                # This is regular content
                if main_title is None and not nodes and not current_node:
                    # No H1 found and no current node yet, this goes to preamble (until first heading)
                    preamble_content.append(line)
                elif current_node:
                    # We have a current node, collect content for it
                    content_buffer.append(line)
                elif main_title is not None:
                    # We have an H1 but no current node, this goes to root content
                    root_content.append(line)
                else:
                    # No H1 but we have nodes, collect for current node if exists
                    if current_node:
                        content_buffer.append(line)
                    else:
                        # Wait for first node to be created
                        pass

            i += 1

        # Don't forget the last node
        if current_node:
            current_node.content = '\n'.join(content_buffer).strip()
            nodes.append(current_node)
        
        # 🆕 تقسیم chunks بزرگ با overlap
        nodes = self._split_large_chunks(nodes)

        # تعیین عنوان اصلی مقاله
        final_title = main_title
        if not final_title:
            # اگر H1 پیدا نشد، از article_title یا filename استفاده کن
            if article_title:
                final_title = article_title
            elif filename:
                # استخراج عنوان از نام فایل
                name_without_ext = filename.rsplit('.', 1)[0] if '.' in filename else filename
                final_title = name_without_ext.replace('_', ' ').replace('-', ' ').title()
            else:
                final_title = "مقاله بدون عنوان"  # Fallback نهایی
        
        # محتوای root node
        if not root_content and not main_title:
            # اگر H1 پیدا نشد، preamble_content را به root بده
            root_content = preamble_content
        
        # ✅ ایجاد Root Node با عنوان واقعی از H1
        root_node = MarkdownNode(
            id=str(uuid.uuid4()),
            title=final_title,
            level=0,  # Root node همیشه level 0
            content='\n'.join(root_content).strip(),
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

    def _split_large_chunks(self, nodes: List[MarkdownNode]) -> List[MarkdownNode]:
        """
        تقسیم chunks بزرگ به قطعات کوچکتر با overlap.
        
        این تابع chunks بزرگتر از max_chunk_size را به قطعات کوچکتر تقسیم می‌کند
        و همپوشانی بین آنها را حفظ می‌کند تا اطلاعات در مرز chunks از دست نرود.
        
        Args:
            nodes: لیست nodes اولیه
            
        Returns:
            لیست nodes با chunks بهینه شده
        """
        result_nodes = []
        
        for node in nodes:
            content_length = len(node.content)
            
            # اگر chunk کوچک است، همان را نگه دار
            if content_length <= self.max_chunk_size:
                result_nodes.append(node)
                continue
            
            # chunk بزرگ است، باید تقسیم شود
            # 🎯 استراتژی: تقسیم بر اساس پاراگراف (برای حفظ معنا)
            paragraphs = node.content.split('\n\n')
            
            # اگر پاراگراف‌ها وجود ندارند، بر اساس جمله تقسیم کن
            if len(paragraphs) == 1:
                paragraphs = node.content.split('. ')
                separator = '. '
            else:
                separator = '\n\n'
            
            current_chunk = ""
            chunk_parts = []
            
            for para in paragraphs:
                # اگر اضافه کردن این پاراگراف، chunk را بزرگتر از حد کند
                if len(current_chunk) + len(para) + len(separator) > self.max_chunk_size and current_chunk:
                    chunk_parts.append(current_chunk.strip())
                    # شروع chunk جدید با overlap از انتهای chunk قبلی
                    if self.chunk_overlap > 0:
                        overlap_start = max(0, len(current_chunk) - self.chunk_overlap)
                        current_chunk = current_chunk[overlap_start:] + separator + para
                    else:
                        current_chunk = para
                else:
                    if current_chunk:
                        current_chunk += separator + para
                    else:
                        current_chunk = para
            
            # اضافه کردن chunk آخر
            if current_chunk:
                chunk_parts.append(current_chunk.strip())
            
            # ایجاد node های جدید برای هر chunk
            for idx, chunk_content in enumerate(chunk_parts):
                if idx == 0:
                    # اولین chunk: node اصلی را به‌روز کن
                    node.content = chunk_content
                    result_nodes.append(node)
                else:
                    # chunks بعدی: node های جدید بساز
                    new_node = MarkdownNode(
                        id=str(uuid.uuid4()),
                        title=f"{node.title} (بخش {idx + 1})",
                        level=node.level,
                        content=chunk_content,
                        parent_id=node.parent_id,
                        path=f"{node.path}.{idx + 1}",
                        order=node.order
                    )
                    result_nodes.append(new_node)
        
        return result_nodes
    
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

    def add_contextual_info_to_chunk(self, chunk_content: str, node: 'MarkdownNode',
                                   article_title: str, tree: 'MarkdownTree') -> str:
        """
        🔥 Contextual Retrieval: افزودن اطلاعات زمینه‌ای به chunk قبل از embedding

        استراتژی Anthropic برای بهبود retrieval accuracy تا 67%:
        - افزودن عنوان مقاله
        - افزودن مسیر سلسله مراتبی
        - افزودن اطلاعات والدین
        - استفاده از LLM برای contextualization هوشمند

        Args:
            chunk_content: محتوای اصلی chunk
            node: گره مربوط به chunk
            article_title: عنوان مقاله
            tree: درخت کامل برای دسترسی به اطلاعات والدین

        Returns:
            contextualized_content: محتوای غنی‌سازی شده با context
        """
        try:
            # استخراج اطلاعات پایه
            section_path = node.path
            section_title = node.title

            # استخراج اطلاعات والدین
            parent_info = []
            current_node = node
            while current_node.parent_id:
                parent_node = tree.get_node_by_id(current_node.parent_id)
                if parent_node:
                    parent_info.append(f"بخش: {parent_node.title}")
                    current_node = parent_node
                else:
                    break

            # ساختار context اولیه
            context_parts = [
                f"[عنوان مقاله: {article_title}]",
                f"[بخش فعلی: {section_title}]",
                f"[مسیر: {section_path}]"
            ]

            # اضافه کردن اطلاعات والدین
            if parent_info:
                context_parts.extend([f"[والد: {info}]" for info in parent_info[::-1]])  # از بالاترین والد شروع کن

            context_header = " | ".join(context_parts)

            # 🔥 Contextualization پیشرفته با LLM (اختیاری - اگر فعال باشد)
            contextualized_chunk = self._contextualize_with_llm(
                chunk_content, context_header, article_title, section_title
            )

            # ترکیب نهایی
            final_content = f"{context_header}\n\n{contextualized_chunk}"

            return final_content

        except Exception as e:
            # در صورت خطا، از contextualization ساده استفاده کن
            logger.warning(f"⚠️ Contextual retrieval failed: {e}, using simple context")
            simple_context = f"[عنوان مقاله: {article_title}] [بخش: {section_title}]\n\n{chunk_content}"
            return simple_context

    def _contextualize_with_llm(self, chunk_content: str, context_header: str,
                               article_title: str, section_title: str) -> str:
        """
        استفاده از LLM برای contextualization هوشمند chunk

        این متد یک جمله زمینه‌ای کوتاه تولید می‌کند که به chunk اضافه می‌شود.
        """
        try:
            # اگر contextualization فعال نیست، محتوای اصلی را برگردان
            if not getattr(self, 'enable_llm_contextualization', False):
                return chunk_content

            # استفاده از LLM برای تولید context
            from app.infrastructure.model_factory import model_factory

            prompt = f"""
            این یک بخش از مقاله "{article_title}" است.
            بخش: "{section_title}"

            محتوای بخش:
            {chunk_content[:200]}...

            یک جمله بسیار کوتاه (کمتر از ۲۰ کلمه) بنویس که زمینه این بخش را توضیح دهد.
            جمله باید به صورت: "این بخش درباره [موضوع] است و [توضیح کوتاه]"

            جمله زمینه‌ای کوتاه:
            """

            llm = model_factory.create_model("fast")
            response = llm.generate(prompt)

            if hasattr(response, 'content') and response.content.strip():
                llm_context = response.content.strip()
                return f"{llm_context}\n\n{chunk_content}"

            return chunk_content

        except Exception as e:
            logger.debug(f"LLM contextualization failed: {e}")
            return chunk_content


# Global instance با تنظیمات بهینه برای Small-to-Big Retrieval
# 🔥 OPTIMIZED FOR PRECISION:
# max_chunk_size=512: chunks کوچکتر برای دقت بالاتر در retrieval
# chunk_overlap=50: همپوشانی برای حفظ context بین chunks
markdown_parser = MarkdownParser(max_chunk_size=512, chunk_overlap=50)
