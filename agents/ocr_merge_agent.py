from typing import List, Dict
from utils.llm_client import llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class OCRMergeAgent:
    def __init__(self):
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert in OCR text cleanup and merging. Your task is to compare two OCR outputs (EasyOCR and Tesseract) and generate the most accurate cleaned text. Remove artifacts, fix broken words, and preserve the original structure and data integrity. Return only the cleaned text."),
            ("user", "Compare these OCR outputs and generate the most accurate cleaned text:\n\nEasyOCR Output:\n{easyocr_text}\n\nTesseract Output:\n{tesseract_text}")
        ])
        self.chain = self.prompt | llm | StrOutputParser()

    def merge_results(self, ocr_results: List[Dict]) -> List[Dict]:
        """
        Processes a list of OCR results and merges the text for each page using an LLM.
        """
        merged_results = []
        for result in ocr_results:
            page_num = result.get("page", "Unknown")
            easy_text = result.get("easyocr_text", "")
            tess_text = result.get("tesseract_text", "")

            print(f"Merging OCR results for page {page_num}...")
            
            try:
                cleaned_text = self.chain.invoke({
                    "easyocr_text": easy_text,
                    "tesseract_text": tess_text
                })
                
                merged_results.append({
                    "page": page_num,
                    "merged_ocr_text": cleaned_text
                })
            except Exception as e:
                print(f"Error merging page {page_num}: {e}")
                merged_results.append({
                    "page": page_num,
                    "error": str(e),
                    "merged_ocr_text": None
                })
        
        return merged_results

if __name__ == "__main__":
    # Example usage logic
    pass
