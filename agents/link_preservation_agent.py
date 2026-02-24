"""
Link Preservation Agent
Converts extracted hyperlinks into markdown format.
Non-LLM deterministic mapping from hyperlink data to markdown format.
"""

from typing import List, Dict, Any, Optional


class LinkPreservationAgent:
    """
    Converts extracted hyperlinks into markdown format.
    Deterministic mapping with no LLM required.
    """
    
    def __init__(self):
        """Initialize the Link Preservation Agent."""
        pass
    
    def convert_to_markdown(self, hyperlinks: List[Dict[str, Any]]) -> List[str]:
        """
        Convert hyperlinks to markdown format.
        
        Args:
            hyperlinks: List of hyperlink dicts with 'url', 'bbox', 'page' keys
                       May optionally have 'text' key
        
        Returns:
            List of markdown formatted strings [text](url)
        """
        markdown_links = []
        
        for link in hyperlinks:
            url = link.get("url", "")
            text = link.get("text", "")
            
            # Skip if no URL
            if not url:
                continue
            
            # If no text, use URL as text
            if not text or text.strip() == "":
                text = url
            
            # Create markdown format: [text](url)
            markdown = f"[{text}]({url})"
            markdown_links.append(markdown)
        
        return markdown_links
    
    def convert_with_metadata(self, hyperlinks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert hyperlinks to markdown format with metadata preserved.
        
        Args:
            hyperlinks: List of hyperlink dicts
        
        Returns:
            List of dicts with 'markdown', 'url', 'page', 'bbox' keys
        """
        results = []
        
        for link in hyperlinks:
            url = link.get("url", "")
            text = link.get("text", "")
            page = link.get("page", 0)
            bbox = link.get("bbox", {})
            
            # Skip if no URL
            if not url:
                continue
            
            # If no text, use URL as text
            if not text or text.strip() == "":
                text = url
            
            # Create markdown format
            markdown = f"[{text}]({url})"
            
            results.append({
                "markdown": markdown,
                "url": url,
                "page": page,
                "bbox": bbox
            })
        
        return results
    
    def extract_and_convert(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract hyperlinks from text extraction result and convert to markdown.
        
        Args:
            extraction_result: Result from NativeTextExtractionAgent with 'hyperlinks' key
        
        Returns:
            Dict with 'markdown_links' and 'markdown_links_with_metadata'
        """
        hyperlinks = extraction_result.get("hyperlinks", [])
        
        return {
            "markdown_links": self.convert_to_markdown(hyperlinks),
            "markdown_links_with_metadata": self.convert_with_metadata(hyperlinks),
            "total_links_converted": len(self.convert_to_markdown(hyperlinks))
        }


def create_link_preservation_agent() -> LinkPreservationAgent:
    """
    Factory function to create a Link Preservation Agent.
    
    Returns:
        LinkPreservationAgent instance
    """
    return LinkPreservationAgent()
