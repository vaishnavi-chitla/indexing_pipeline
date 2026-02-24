"""
Layout Analysis Agent
Detects columns, preserves reading order, and identifies header/footer zones.
No LLM required - purely algorithmic approach.
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass, asdict
import numpy as np
from collections import defaultdict


@dataclass
class BoundingBox:
    """Represents a bounding box with x, y coordinates."""
    x0: float
    y0: float
    x1: float
    y1: float
    
    @property
    def width(self) -> float:
        return self.x1 - self.x0
    
    @property
    def height(self) -> float:
        return self.y1 - self.y0
    
    @property
    def center_x(self) -> float:
        return (self.x0 + self.x1) / 2
    
    @property
    def center_y(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class TextBlock:
    """Represents a text block with content and position."""
    text: str
    bbox: BoundingBox
    block_id: int = None


class LayoutAnalysisAgent:
    """
    Analyzes document layout to detect columns, reading order, and header/footer zones.
    """
    
    def __init__(self, page_height: float = 792, page_width: float = 612, 
                 margin_ratio: float = 0.1, column_gap_threshold: float = 50):
        """
        Initialize the Layout Analysis Agent.
        
        Args:
            page_height: Height of the page in points (default: Letter height 792)
            page_width: Width of the page in points (default: Letter width 612)
            margin_ratio: Ratio of page height for header/footer detection (default: 0.1)
            column_gap_threshold: Minimum gap between columns (default: 50)
        """
        self.page_height = page_height
        self.page_width = page_width
        self.margin_ratio = margin_ratio
        self.column_gap_threshold = column_gap_threshold
    
    def analyze(self, text_blocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze page layout and return ordered text blocks with metadata.
        
        Args:
            text_blocks: List of dicts with 'text' and 'bbox' keys
                        bbox should be dict with 'x0', 'y0', 'x1', 'y1'
        
        Returns:
            Dict with 'ordered_text_blocks' and 'layout_metadata'
        """
        if not text_blocks:
            return {
                "ordered_text_blocks": [],
                "layout_metadata": {
                    "columns": 1,
                    "header_bbox": None,
                    "footer_bbox": None
                }
            }
        
        # Convert input to TextBlock objects
        blocks = self._parse_text_blocks(text_blocks)
        
        # Detect header and footer zones
        header_bbox, footer_bbox = self._detect_header_footer(blocks)
        
        # Separate header, footer, and content blocks
        content_blocks = self._filter_content_blocks(blocks, header_bbox, footer_bbox)
        
        if not content_blocks:
            content_blocks = blocks
        
        # Detect columns in content area
        num_columns = self._detect_columns(content_blocks)
        
        # Assign blocks to columns
        block_columns = self._assign_to_columns(content_blocks, num_columns)
        
        # Order blocks: top-to-bottom within each column, then left-to-right across columns
        ordered_blocks = self._order_blocks(content_blocks, block_columns, num_columns)
        
        return {
            "ordered_text_blocks": ordered_blocks,
            "layout_metadata": {
                "columns": num_columns,
                "header_bbox": asdict(header_bbox) if header_bbox else None,
                "footer_bbox": asdict(footer_bbox) if footer_bbox else None
            }
        }
    
    def _parse_text_blocks(self, text_blocks: List[Dict[str, Any]]) -> List[TextBlock]:
        """Convert input dicts to TextBlock objects."""
        blocks = []
        for idx, block in enumerate(text_blocks):
            bbox_dict = block['bbox']
            bbox = BoundingBox(
                x0=bbox_dict['x0'],
                y0=bbox_dict['y0'],
                x1=bbox_dict['x1'],
                y1=bbox_dict['y1']
            )
            text_block = TextBlock(text=block['text'], bbox=bbox, block_id=idx)
            blocks.append(text_block)
        return blocks
    
    def _detect_header_footer(self, blocks: List[TextBlock]) -> Tuple[BoundingBox, BoundingBox]:
        """
        Detect header and footer zones based on vertical position.
        
        Header: top margin_ratio of page
        Footer: bottom margin_ratio of page
        """
        header_threshold = self.page_height * self.margin_ratio
        footer_threshold = self.page_height * (1 - self.margin_ratio)
        
        header_blocks = [b for b in blocks if b.bbox.y1 < header_threshold]
        footer_blocks = [b for b in blocks if b.bbox.y0 > footer_threshold]
        
        header_bbox = None
        footer_bbox = None
        
        if header_blocks:
            min_y0 = min(b.bbox.y0 for b in header_blocks)
            max_y1 = max(b.bbox.y1 for b in header_blocks)
            min_x0 = min(b.bbox.x0 for b in header_blocks)
            max_x1 = max(b.bbox.x1 for b in header_blocks)
            header_bbox = BoundingBox(min_x0, min_y0, max_x1, max_y1)
        
        if footer_blocks:
            min_y0 = min(b.bbox.y0 for b in footer_blocks)
            max_y1 = max(b.bbox.y1 for b in footer_blocks)
            min_x0 = min(b.bbox.x0 for b in footer_blocks)
            max_x1 = max(b.bbox.x1 for b in footer_blocks)
            footer_bbox = BoundingBox(min_x0, min_y0, max_x1, max_y1)
        
        return header_bbox, footer_bbox
    
    def _filter_content_blocks(self, blocks: List[TextBlock], 
                               header_bbox: BoundingBox, 
                               footer_bbox: BoundingBox) -> List[TextBlock]:
        """Filter out header and footer blocks from content."""
        content = []
        for block in blocks:
            is_header = header_bbox and (
                block.bbox.y1 <= header_bbox.y1 or 
                block.bbox.y0 >= header_bbox.y0 and block.bbox.y1 <= header_bbox.y1
            )
            is_footer = footer_bbox and (
                block.bbox.y0 >= footer_bbox.y0 or
                block.bbox.y0 >= footer_bbox.y0 and block.bbox.y1 <= footer_bbox.y1
            )
            
            if not (is_header or is_footer):
                content.append(block)
        
        return content
    
    def _detect_columns(self, blocks: List[TextBlock]) -> int:
        """
        Detect number of columns using clustering of x-coordinates.
        """
        if len(blocks) < 2:
            return 1
        
        # Get all x-coordinates (left and right edges)
        x_coords = []
        for block in blocks:
            x_coords.append(block.bbox.x0)
            x_coords.append(block.bbox.x1)
        
        x_coords = sorted(set(x_coords))
        
        if len(x_coords) < 2:
            return 1
        
        # Calculate gaps between consecutive x-coordinates
        gaps = []
        gap_positions = []
        for i in range(len(x_coords) - 1):
            gap = x_coords[i + 1] - x_coords[i]
            gaps.append(gap)
            gap_positions.append((x_coords[i], x_coords[i + 1]))
        
        # Find significant gaps (potential column separators)
        if not gaps:
            return 1
        
        mean_gap = np.mean(gaps)
        significant_gaps = [
            (i, gap) for i, gap in enumerate(gaps) 
            if gap > max(mean_gap * 1.5, self.column_gap_threshold)
        ]
        
        # Number of columns = number of significant gaps + 1
        num_columns = len(significant_gaps) + 1
        
        # Limit to reasonable number of columns
        return min(num_columns, 5)
    
    def _assign_to_columns(self, blocks: List[TextBlock], 
                          num_columns: int) -> Dict[int, List[TextBlock]]:
        """Assign blocks to columns based on x-coordinate clustering."""
        if num_columns == 1:
            return {0: blocks}
        
        # Calculate column boundaries
        min_x = min(b.bbox.x0 for b in blocks)
        max_x = max(b.bbox.x1 for b in blocks)
        col_width = (max_x - min_x) / num_columns
        
        block_columns = defaultdict(list)
        for block in blocks:
            col_idx = int((block.bbox.center_x - min_x) / col_width)
            col_idx = min(col_idx, num_columns - 1)  # Ensure within bounds
            block_columns[col_idx].append(block)
        
        return block_columns
    
    def _order_blocks(self, blocks: List[TextBlock], 
                     block_columns: Dict[int, List[TextBlock]], 
                     num_columns: int) -> List[Dict[str, Any]]:
        """
        Order blocks: top-to-bottom within columns, then left-to-right across columns.
        """
        ordered = []
        
        # For each column from left to right
        for col_idx in range(num_columns):
            if col_idx not in block_columns:
                continue
            
            # Sort blocks in this column top-to-bottom (ascending y)
            col_blocks = sorted(block_columns[col_idx], key=lambda b: b.bbox.y0)
            
            for block in col_blocks:
                ordered.append({
                    "text": block.text,
                    "bbox": asdict(block.bbox),
                    "block_id": block.block_id
                })
        
        return ordered


def create_layout_analysis_agent(page_height: float = 792, 
                                 page_width: float = 612) -> LayoutAnalysisAgent:
    """
    Factory function to create a Layout Analysis Agent.
    
    Args:
        page_height: Height of the page (default: Letter page height)
        page_width: Width of the page (default: Letter page width)
    
    Returns:
        LayoutAnalysisAgent instance
    """
    return LayoutAnalysisAgent(page_height=page_height, page_width=page_width)
