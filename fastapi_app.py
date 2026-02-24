from fastapi import FastAPI, UploadFile, File, HTTPException
from typing import List, Dict

import uvicorn
import shutil
import os
import tempfile
from pathlib import Path
from agents.format_detection_agent import FormatDetectionAgent
from agents.conversion_agent import ConversionAgent
from agents.pdf_loader_agent import PDFLoaderAgent
from agents.ocr_agent import OCRAgent
from agents.ocr_merge_agent import OCRMergeAgent

app = FastAPI(
    title="Indexing Pipeline API",
    description="API for preparing documents for indexing, including format detection, conversion, OCR, and merging.",
    version="1.0.0"
)

# Initialize agents
format_agent = FormatDetectionAgent()
conversion_agent = ConversionAgent()
ocr_agent = OCRAgent()
merge_agent = OCRMergeAgent()


# Helper to get the system Downloads folder
def get_downloads_folder():
    return Path.home() / "Downloads"

@app.post("/detect-format")
async def detect_format(file: UploadFile = File(...)):
    try:
        result = format_agent.detect_format(file.filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/convert")
async def convert_document(file: UploadFile = File(...)):
    """
    Endpoint to convert a document (docx, pptx, etc.) to PDF and save it to the Downloads folder.
    Returns JSON with the path and success message.
    """
    downloads_dir = get_downloads_folder()
    downloads_dir.mkdir(exist_ok=True)
    
    # Use a temporary directory for the initial upload to avoid saving in the project folder
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_input_path = Path(temp_dir) / file.filename
        
        try:
            # Save uploaded file to temp directory
            with open(temp_input_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Detect if conversion is needed
            format_info = format_agent.detect_format(str(temp_input_path))
            
            if format_info["needs_conversion"]:
                # Convert to PDF directly into the Downloads folder
                output_pdf_path = conversion_agent.convert_to_pdf(str(temp_input_path), output_dir=str(downloads_dir))
                
                return {
                    "pdf_path": str(output_pdf_path),
                    "message": "success"
                }
            elif format_info["original_type"] == "pdf":
                # If it's already a PDF, save it to the Downloads folder
                dest_path = downloads_dir / file.filename
                shutil.copy2(temp_input_path, dest_path)
                
                return {
                    "pdf_path": str(dest_path),
                    "message": "no conversion needed"
                }
            else:
                return {
                    "message": "File format unsupported for conversion", 
                    "format": format_info
                }
                 
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/load-pdf")
async def load_pdf(file_path: str):
    """
    Endpoint to load a PDF and return page count and serializable references.
    Input: Absolute file path to the PDF.
    """
    try:
        # Strip potential quotes if passed literally in the URL
        clean_path = file_path.strip("\"'")
        loader = PDFLoaderAgent(clean_path)
        return loader.load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ocr")
async def run_ocr(file: UploadFile = File(...)):
    """
    Endpoint to run parallel OCR on all pages of an uploaded PDF file. 
    Returns a sorted list of page results.
    """
    # Use a temporary directory for the uploaded file to avoid saving in project folder
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / file.filename
        
        try:
            # Save uploaded file to temp location
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Run parallel OCR on all pages
            result = ocr_agent.run_ocr(str(temp_path))
            return result
                     
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/merge-ocr")
async def merge_ocr_results(ocr_results: List[Dict]):
    """
    Endpoint to merge EasyOCR and Tesseract results using LLM.
    Input: List of objects containing page, easyocr_text, and tesseract_text.
    """
    try:
        results = merge_agent.merge_results(ocr_results)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
