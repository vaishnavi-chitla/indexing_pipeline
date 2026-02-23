from pathlib import Path
from typing import Dict, List
from pypdf import PdfReader


class PDFLoaderAgent:
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)

        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")

        self.reader = PdfReader(str(self.pdf_path))

    def load(self) -> Dict:
        """
        Extracts total page count and returns serializable page references for JSON output.
        """
        total_pages = len(self.reader.pages)

        # page_refs as serializable strings for the JSON output
        pages = [f"page_{i + 1}" for i in range(total_pages)]

        return {
            "total_pages": total_pages,
            "pages": pages
        }

    def get_page_iterator(self):
        """
        Provides a page iterator as requested in the responsibility.
        """
        for page in self.reader.pages:
            yield page
