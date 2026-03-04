from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import uvicorn
import shutil
import os
import tempfile
import pdfplumber
from pathlib import Path

# Agent Imports
from agents.format_detection_agent import FormatDetectionAgent
from agents.conversion_agent import ConversionAgent
from agents.pdf_loader_agent import PDFLoaderAgent
from agents.ocr_agent import OCRAgent
from agents.ocr_merge_agent import OCRMergeAgent
from agents.layout_analysis_agent import create_layout_analysis_agent, BoundingBox
from agents.native_text_extraction_agent import create_text_extraction_agent
from agents.link_preservation_agent import create_link_preservation_agent

app = FastAPI(
    title="Indexing Pipeline API",
    description="Unified API for document processing, conversion, OCR, layout analysis, and text extraction.",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize agents
format_agent = FormatDetectionAgent()
conversion_agent = ConversionAgent()
ocr_agent = OCRAgent()
merge_agent = OCRMergeAgent()

# --- Helper Functions ---

def get_downloads_folder():
    """Returns the system Downloads folder path."""
    return Path.home() / "Downloads"

def extract_text_blocks_alternative(pdf_path: str) -> List[Dict[str, Any]]:
    """Alternative method to extract text blocks using word/character boundaries."""
    text_blocks = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                words = page.extract_words(keep_blank_chars=False)
                lines = {}
                for word in words:
                    y_coord = round(word['top'], 1)
                    if y_coord not in lines:
                        lines[y_coord] = []
                    lines[y_coord].append(word)
                
                for y_coord in sorted(lines.keys()):
                    line_words = sorted(lines[y_coord], key=lambda w: w['x0'])
                    text = ' '.join([w['text'] for w in line_words])
                    x0 = min(w['x0'] for w in line_words)
                    y0 = min(w['top'] for w in line_words)
                    x1 = max(w['x1'] for w in line_words)
                    y1 = max(w['bottom'] for w in line_words)
                    
                    text_blocks.append({
                        'text': text,
                        'bbox': {'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1},
                        'page': page_num
                    })
    except Exception as e:
        raise ValueError(f"Failed to extract text blocks: {str(e)}")
    return text_blocks

# --- Endpoints ---

@app.post("/detect-format")
async def detect_format(file: UploadFile = File(...)):
    """Detects the file format and determines if conversion is needed."""
    try:
        result = format_agent.detect_format(file.filename)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/convert")
async def convert_document(file: UploadFile = File(...)):
    """Converts docx/pptx to PDF and saves to the Downloads folder."""
    downloads_dir = get_downloads_folder()
    downloads_dir.mkdir(exist_ok=True)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_input_path = Path(temp_dir) / file.filename
        try:
            with open(temp_input_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            format_info = format_agent.detect_format(str(temp_input_path))
            
            if format_info["needs_conversion"]:
                output_pdf_path = conversion_agent.convert_to_pdf(str(temp_input_path), output_dir=str(downloads_dir))
                return {"pdf_path": str(output_pdf_path), "message": "success"}
            elif format_info["original_type"] == "pdf":
                dest_path = downloads_dir / file.filename
                shutil.copy2(temp_input_path, dest_path)
                return {"pdf_path": str(dest_path), "message": "no conversion needed"}
            else:
                return {"message": "File format unsupported for conversion", "format": format_info}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/load-pdf")
async def load_pdf(file_path: str):
    """Loads a PDF and returns page count and references."""
    try:
        clean_path = file_path.strip("\"'")
        loader = PDFLoaderAgent(clean_path)
        return loader.load()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ocr")
async def post_ocr(file: UploadFile = File(...)):
    """Runs parallel OCR on all pages of an uploaded PDF."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / file.filename
        try:
            with open(temp_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            return ocr_agent.run_ocr(str(temp_path))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/ocr-agent")
async def post_ocr_agent(file: UploadFile = File(...)):
    """Runs parallel OCR on all pages of an uploaded PDF (Alias for /ocr)."""
    return await post_ocr(file)

@app.post("/merge-ocr")
async def merge_ocr_results(ocr_results: List[Dict]):
    """Merges EasyOCR and Tesseract results using LLM."""
    try:
        return merge_agent.merge_results(ocr_results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/layout-analyze-pdf-agent")
async def layout_analyze_pdf(file: UploadFile = File(...)):
    """Analyzes PDF layout to detect columns, headers, and footers."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = os.path.join(temp_dir, file.filename)
        try:
            with open(temp_path, 'wb') as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            text_blocks = extract_text_blocks_alternative(temp_path)
            if not text_blocks:
                raise HTTPException(status_code=400, detail="No text blocks found in PDF")
            
            agent = create_layout_analysis_agent()
            results_by_page = {}
            for block in text_blocks:
                page_num = block.get('page', 0)
                results_by_page.setdefault(page_num, []).append(block.copy())
            
            page_results = {}
            for page_num in sorted(results_by_page.keys()):
                page_blocks = results_by_page[page_num]
                # Cleanup 'page' key before analysis as per previous logic
                for b in page_blocks: b.pop('page', None)
                page_results[f"page_{page_num}"] = agent.analyze(page_blocks)
            
            return {"filename": file.filename, "total_pages": len(results_by_page), "status": "success", "analysis": page_results}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/native-extract-text-agent")
async def native_extract_text(file: UploadFile = File(...)):
    """Extracts selectable text with coordinates and hyperlinks."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = os.path.join(temp_dir, file.filename)
        try:
            with open(temp_path, 'wb') as buffer:
                shutil.copyfileobj(file.file, buffer)
            agent = create_text_extraction_agent(extract_font_info=True, extract_colors=False)
            results = agent.extract_from_file(temp_path)
            return JSONResponse(content=results)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/link-preservation-agent")
async def link_preservation(file: UploadFile = File(...)):
    """Extracts hyperlinks and converts them to markdown."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = os.path.join(temp_dir, file.filename)
        try:
            with open(temp_path, 'wb') as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            extraction_agent = create_text_extraction_agent(extract_font_info=False, extract_colors=False)
            extraction_results = extraction_agent.extract_from_file(temp_path)
            
            preservation_agent = create_link_preservation_agent()
            markdown_results = preservation_agent.extract_and_convert(extraction_results)
            
            return {
                "filename": file.filename,
                "status": "success",
                "markdown_links": markdown_results["markdown_links"],
                "markdown_links_with_metadata": markdown_results["markdown_links_with_metadata"],
                "total_links_converted": markdown_results["total_links_converted"]
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
