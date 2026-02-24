"""
Native Text Extraction Agent
Extracts selectable text with coordinates and hyperlinks from PDFs using PyMuPDF (fitz).
Preserves precise positioning and link information.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import fitz  # PyMuPDF


@dataclass
class BoundingBox:
    """Represents a bounding box with coordinates."""
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
    def area(self) -> float:
        return self.width * self.height
    
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
    block_id: int
    block_type: str = "text"  # text, image, line, etc.
    font: Optional[str] = None
    font_size: Optional[float] = None
    is_bold: bool = False
    is_italic: bool = False
    color: Optional[Tuple[int, int, int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "text": self.text,
            "bbox": asdict(self.bbox),
            "block_id": self.block_id,
            "block_type": self.block_type,
        }


@dataclass
class Hyperlink:
    """Represents a hyperlink in the document."""
    url: str
    bbox: BoundingBox
    link_type: str  # "uri", "page", "gotor", etc.
    page: int
    text: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "url": self.url,
            "bbox": asdict(self.bbox),
            "page": self.page
        }


class NativeTextExtractionAgent:
    """
    Extracts selectable text, coordinates, and hyperlinks from PDF documents.
    Uses PyMuPDF (fitz) for high-precision text extraction.
    """
    
    def __init__(self, extract_font_info: bool = True, 
                 extract_colors: bool = False):
        """
        Initialize the Native Text Extraction Agent.
        
        Args:
            extract_font_info: Whether to extract font names and sizes
            extract_colors: Whether to extract text color information
        """
        self.extract_font_info = extract_font_info
        self.extract_colors = extract_colors
    
    def extract_from_file(self, pdf_path: str) -> Dict[str, Any]:
        """
        Extract text blocks and hyperlinks from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
        
        Returns:
            Dict with 'text_blocks' and 'hyperlinks' for all pages combined
        """
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            raise ValueError(f"Failed to open PDF file: {str(e)}")
        
        try:
            all_text_blocks = []
            all_hyperlinks = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_results = self._extract_page(page, page_num)
                all_text_blocks.extend(page_results["text_blocks"])
                all_hyperlinks.extend(page_results["hyperlinks"])
            
            return {
                "text_blocks": all_text_blocks,
                "hyperlinks": all_hyperlinks
            }
        
        finally:
            doc.close()
    
    def extract_page(self, pdf_path: str, page_num: int) -> Dict[str, Any]:
        """
        Extract text blocks and hyperlinks from a specific page.
        
        Args:
            pdf_path: Path to the PDF file
            page_num: Page number (0-indexed)
        
        Returns:
            Dict with 'text_blocks' and 'hyperlinks'
        """
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            raise ValueError(f"Failed to open PDF file: {str(e)}")
        
        try:
            if page_num >= len(doc):
                raise ValueError(f"Page {page_num} not found (document has {len(doc)} pages)")
            
            page = doc[page_num]
            return self._extract_page(page, page_num)
        
        finally:
            doc.close()
    
    def _extract_page(self, page: fitz.Page, page_num: int) -> Dict[str, Any]:
        """
        Internal method to extract content from a single page.
        
        Args:
            page: The fitz page object
            page_num: The page number
        
        Returns:
            Dict with text_blocks and hyperlinks
        """
        text_blocks = []
        hyperlinks = []
        
        # Extract text blocks with detailed layout
        block_id = 0
        try:
            # Use get_text with dict format for detailed position info
            text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
            
            for block in text_dict.get("blocks", []):
                if block["type"] == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                bbox = fitz.Rect(span["bbox"])
                                
                                # Extract font information
                                font = None
                                font_size = None
                                if self.extract_font_info:
                                    font = span.get("font", None)
                                    font_size = span.get("size", None)
                                
                                # Extract color information
                                color = None
                                if self.extract_colors and "color" in span:
                                    color = span["color"]
                                
                                # Check for font attributes
                                flags = span.get("flags", 0)
                                is_bold = bool(flags & (1 << 3))
                                is_italic = bool(flags & (1 << 0))
                                
                                text_block = TextBlock(
                                    text=text,
                                    bbox=BoundingBox(
                                        x0=bbox.x0,
                                        y0=bbox.y0,
                                        x1=bbox.x1,
                                        y1=bbox.y1
                                    ),
                                    block_id=block_id,
                                    block_type="text",
                                    font=font,
                                    font_size=font_size,
                                    is_bold=is_bold,
                                    is_italic=is_italic,
                                    color=color
                                )
                                text_blocks.append(text_block)
                                block_id += 1
                
                elif block["type"] == 1:  # Image block
                    # Include image blocks with their coordinates
                    bbox = fitz.Rect(block["bbox"])
                    text_block = TextBlock(
                        text=f"[IMAGE: {block.get('name', 'embedded')}]",
                        bbox=BoundingBox(
                            x0=bbox.x0,
                            y0=bbox.y0,
                            x1=bbox.x1,
                            y1=bbox.y1
                        ),
                        block_id=block_id,
                        block_type="image"
                    )
                    text_blocks.append(text_block)
                    block_id += 1
        
        except Exception as e:
            # Fallback to simple extraction if dict extraction fails
            text_blocks = self._extract_text_simple(page, page_num)
        
        # Extract hyperlinks
        try:
            hyperlinks = self._extract_hyperlinks(page, page_num)
        except Exception as e:
            # Continue without hyperlinks if extraction fails
            pass
        
        return {
            "text_blocks": [block.to_dict() for block in text_blocks],
            "hyperlinks": [link.to_dict() for link in hyperlinks]
        }
    
    def _extract_text_simple(self, page: fitz.Page, page_num: int) -> List[TextBlock]:
        """
        Fallback simple text extraction using get_text with blocks.
        """
        text_blocks = []
        
        try:
            blocks = page.get_text("blocks")
            block_id = 0
            
            for block in blocks:
                if len(block) >= 4:
                    bbox = fitz.Rect(block[:4])
                    text = block[4].strip() if len(block) > 4 else ""
                    
                    if text:
                        text_block = TextBlock(
                            text=text,
                            bbox=BoundingBox(
                                x0=bbox.x0,
                                y0=bbox.y0,
                                x1=bbox.x1,
                                y1=bbox.y1
                            ),
                            block_id=block_id,
                            block_type="text"
                        )
                        text_blocks.append(text_block)
                        block_id += 1
        
        except Exception:
            pass
        
        return text_blocks
    
    def _extract_hyperlinks(self, page: fitz.Page, page_num: int) -> List[Hyperlink]:
        """
        Extract all hyperlinks from the page.
        """
        hyperlinks = []
        
        try:
            for link_dict in page.get_links():
                link_type = link_dict.get("type", "unknown")
                bbox_rect = link_dict.get("from", None)
                
                if not bbox_rect:
                    continue
                
                # Normalize link_type names
                if link_type == 3:
                    link_type = "uri"
                    url = link_dict.get("uri", "")
                elif link_type == 1:
                    link_type = "page"
                    url = f"page_{link_dict.get('page', -1)}"
                elif link_type == 2:
                    link_type = "gotor"
                    url = link_dict.get("file", "")
                else:
                    url = str(link_dict.get("uri", link_dict.get("page", "")))
                
                bbox = fitz.Rect(bbox_rect)
                
                hyperlink = Hyperlink(
                    url=url,
                    bbox=BoundingBox(
                        x0=bbox.x0,
                        y0=bbox.y0,
                        x1=bbox.x1,
                        y1=bbox.y1
                    ),
                    link_type=link_type,
                    page=page_num
                )
                hyperlinks.append(hyperlink)
        
        except Exception:
            pass
        
        return hyperlinks
    
    def extract_text_with_positions(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Extract all text with precise positions across all pages.
        Simple format: text and bbox per block.
        
        Args:
            pdf_path: Path to the PDF file
        
        Returns:
            List of text blocks with positions
        """
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            raise ValueError(f"Failed to open PDF file: {str(e)}")
        
        all_blocks = []
        
        try:
            for page_num in range(len(doc)):
                page = doc[page_num]
                blocks = page.get_text("blocks")
                
                for block in blocks:
                    if len(block) >= 4:
                        bbox = fitz.Rect(block[:4])
                        text = block[4].strip() if len(block) > 4 else ""
                        
                        if text:
                            all_blocks.append({
                                "text": text,
                                "page": page_num,
                                "bbox": {
                                    "x0": bbox.x0,
                                    "y0": bbox.y0,
                                    "x1": bbox.x1,
                                    "y1": bbox.y1
                                }
                            })
        
        finally:
            doc.close()
        
        return all_blocks


def create_text_extraction_agent(extract_font_info: bool = True,
                                 extract_colors: bool = False) -> NativeTextExtractionAgent:
    """
    Factory function to create a Native Text Extraction Agent.
    
    Args:
        extract_font_info: Whether to extract font information
        extract_colors: Whether to extract color information
    
    Returns:
        NativeTextExtractionAgent instance
    """
    return NativeTextExtractionAgent(
        extract_font_info=extract_font_info,
        extract_colors=extract_colors
    )
