import fitz  # PyMuPDF
from PIL import Image
import io
import pytesseract
import easyocr
import numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Union
 
class OCRAgent:
    def __init__(self, tesseract_cmd: str = r"C:\Users\VennelaMunagala\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"):
        """
        Initialize the OCR Agent.
        :param tesseract_cmd: Path to the Tesseract executable.
        """
        self.tesseract_cmd = tesseract_cmd
        if Path(self.tesseract_cmd).exists():
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_cmd
       
        # Initialize EasyOCR Reader (English by default)
        try:
            self.reader = easyocr.Reader(['en'])
        except Exception as e:
            print(f"EasyOCR initialization warning: {e}")
            self.reader = None
 
    def _render_and_ocr(self, pdf_path: str, page_number: int) -> Dict:
        """
        Worker function: Opens document locally in thread, renders, and runs OCR.
        """
        doc = fitz.open(pdf_path)
        try:
            page = doc.load_page(page_number - 1)
            zoom = 300 / 72
            matrix = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
           
            # Tesseract OCR
            try:
                tesseract_text = pytesseract.image_to_string(image).strip()
            except Exception as e:
                tesseract_text = f"Tesseract Error: {str(e)}"
 
            # EasyOCR
            try:
                if self.reader:
                    img_np = np.array(image)
                    results = self.reader.readtext(img_np, detail=0)
                    easyocr_text = " ".join(results).strip()
                else:
                    easyocr_text = "EasyOCR reader not initialized."
            except Exception as e:
                easyocr_text = f"EasyOCR Error: {str(e)}"
 
            return {
                "page": page_number,
                "easyocr_text": easyocr_text,
                "tesseract_text": tesseract_text
            }
        finally:
            doc.close()
 
    def run_ocr(self, pdf_path: str, max_workers: int = 2) -> List[Dict]:
        """
        Runs OCR on the entire document in parallel with reduced workers.
        """
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
       
        print(f"Starting OCR for {total_pages} pages using {max_workers} workers...")
       
        pages_to_process = list(range(1, total_pages + 1))
        results = []
       
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._render_and_ocr, pdf_path, p): p for p in pages_to_process}
            for future in futures:
                page_num = futures[future]
                try:
                    res = future.result()
                    results.append(res)
                    print(f"✅ Page {page_num} completed.")
                except Exception as e:
                    print(f"❌ Page {page_num} failed: {e}")
                    results.append({"page": page_num, "error": str(e)})
       
        results.sort(key=lambda x: x["page"])
        return results
 
if __name__ == "__main__":
    pass