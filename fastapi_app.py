"""
FastAPI application for Document Layout Analysis
Provides endpoints for PDF upload and layout analysis
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import tempfile
import os
import shutil
from pathlib import Path

from typing import List, Dict, Any
from agents.layout_analysis_agent import create_layout_analysis_agent, BoundingBox
from agents.native_text_extraction_agent import create_text_extraction_agent
from agents.link_preservation_agent import create_link_preservation_agent
from agents.ocr_agent import OCRAgent

app = FastAPI(
    title="Document Layout Analysis API",
    description="Analyze PDF document layout to detect columns, reading order, and header/footer zones",
    version="1.0.0"
)
ocr_agent=OCRAgent()  # Initialize OCR agent with default Tesseract path

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_text_blocks_from_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Extract text blocks with bounding boxes from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file
    
    Returns:
        List of text blocks with bbox information
    """
    text_blocks = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Extract text with detailed layout information
                text_objects = page.extract_text_structure()
                
                # If text_structure is not available, fall back to simple extraction
                if text_objects is None:
                    # Use an alternative approach with char-level data
                    chars = page.chars
                    if not chars:
                        continue
                    
                    # Group characters into words/blocks based on proximity
                    for line in page.extract_text() or "":
                        if line.strip():
                            # Get bounding box for the entire line
                            line_chars = [c for c in chars if c.get('text', '').strip() == line.strip()[:20]]
                            if line_chars:
                                x0 = min(c['x0'] for c in line_chars)
                                y0 = min(c['top'] for c in line_chars)
                                x1 = max(c['x1'] for c in line_chars)
                                y1 = max(c['bottom'] for c in line_chars)
                                
                                text_blocks.append({
                                    'text': line.strip(),
                                    'bbox': {
                                        'x0': x0,
                                        'y0': y0,
                                        'x1': x1,
                                        'y1': y1
                                    },
                                    'page': page_num
                                })
                else:
                    # Use the structured text with bounding boxes
                    for text_obj in text_objects:
                        if isinstance(text_obj, dict) and 'text' in text_obj:
                            bbox = text_obj.get('bbox', {})
                            text_blocks.append({
                                'text': text_obj['text'],
                                'bbox': {
                                    'x0': bbox.get('x0', 0),
                                    'y0': bbox.get('y0', 0),
                                    'x1': bbox.get('x1', 0),
                                    'y1': bbox.get('y1', 0)
                                },
                                'page': page_num
                            })
    
    except Exception as e:
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")
    
    return text_blocks


def extract_text_blocks_alternative(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Alternative method to extract text blocks using word/character boundaries.
    """
    text_blocks = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                # Get words with their bounding boxes
                words = page.extract_words(keep_blank_chars=False)
                
                # Group words into lines based on y-coordinate proximity
                lines = {}
                for word in words:
                    y_coord = round(word['top'], 1)  # Round to group words on same line
                    if y_coord not in lines:
                        lines[y_coord] = []
                    lines[y_coord].append(word)
                
                # Create text blocks from lines
                for y_coord in sorted(lines.keys()):
                    line_words = sorted(lines[y_coord], key=lambda w: w['x0'])
                    
                    # Combine words into a single block
                    text = ' '.join([w['text'] for w in line_words])
                    x0 = min(w['x0'] for w in line_words)
                    y0 = min(w['top'] for w in line_words)
                    x1 = max(w['x1'] for w in line_words)
                    y1 = max(w['bottom'] for w in line_words)
                    
                    text_blocks.append({
                        'text': text,
                        'bbox': {
                            'x0': x0,
                            'y0': y0,
                            'x1': x1,
                            'y1': y1
                        },
                        'page': page_num
                    })
    
    except Exception as e:
        raise ValueError(f"Failed to extract text blocks: {str(e)}")
    
    return text_blocks



@app.post("/layout-analyze-pdf-agent")
async def analyze_pdf(file: UploadFile = File(...)):
    """
    Upload and analyze a PDF document for layout analysis.
    
    Detects:
    - Column layout
    - Header and footer zones
    - Reading order of text blocks
    
    Args:
        file: PDF file to analyze
    
    Returns:
        JSON with ordered text blocks and layout metadata
    """
    
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    # Create temporary file to store the upload
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        # Save uploaded file temporarily
        with open(temp_path, 'wb') as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Extract text blocks from PDF
        try:
            text_blocks = extract_text_blocks_alternative(temp_path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to extract text: {str(e)}")
        
        if not text_blocks:
            raise HTTPException(status_code=400, detail="No text blocks found in PDF")
        
        # Initialize layout analysis agent
        agent = create_layout_analysis_agent()
        
        # Analyze layout per page
        results_by_page = {}
        for block in text_blocks:
            page_num = block.get('page', 0)
            if page_num not in results_by_page:
                results_by_page[page_num] = []
            
            # Remove page number from block before analysis
            block_copy = block.copy()
            block_copy.pop('page', None)
            results_by_page[page_num].append(block_copy)
        
        # Analyze each page
        page_results = {}
        for page_num in sorted(results_by_page.keys()):
            page_blocks = results_by_page[page_num]
            analysis = agent.analyze(page_blocks)
            page_results[f"page_{page_num}"] = analysis
        
        return JSONResponse(content={
            "filename": file.filename,
            "total_pages": len(results_by_page),
            "status": "success",
            "analysis": page_results
        })
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing PDF: {str(e)}")
    
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/native-extract-text-agent")
async def extract_text(file: UploadFile = File(...)):
    """
    Upload a PDF and extract all selectable text with coordinates and hyperlinks.
    
    Requirements:
    - Extract selectable text via fitz/any other parser
    - Preserve coordinates (bounding boxes)
    - Preserve hyperlinks
    
    Args:
        file: PDF file to extract text from
    
    Returns:
        JSON with exact format:
        {
          "text_blocks": [...],
          "hyperlinks": [...]
        }
    """
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        # Save uploaded file temporarily
        with open(temp_path, 'wb') as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Initialize text extraction agent
        agent = create_text_extraction_agent(extract_font_info=True, extract_colors=False)
        
        # Extract text and hyperlinks from all pages
        try:
            results = agent.extract_from_file(temp_path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to extract text: {str(e)}")
        
        # Return exact required format
        return JSONResponse(content=results)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error extracting text: {str(e)}")
    
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/link-preservation-agent")
async def extract_and_preserve_links(file: UploadFile = File(...)):
    """
    Upload a PDF, extract hyperlinks, and convert them to markdown format.
    
    This combines text extraction and link preservation in one endpoint.
    
    Args:
        file: PDF file to process
    
    Returns:
        JSON with:
        {
          "filename": str,
          "status": str,
          "markdown_links": ["[text](url)", ...],
          "markdown_links_with_metadata": [...],
          "total_links_converted": number
        }
    """
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, file.filename)
    
    try:
        # Save uploaded file temporarily
        with open(temp_path, 'wb') as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Extract hyperlinks from PDF
        try:
            extraction_agent = create_text_extraction_agent(extract_font_info=False, extract_colors=False)
            extraction_results = extraction_agent.extract_from_file(temp_path)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to extract hyperlinks: {str(e)}")
        
        # Convert hyperlinks to markdown
        try:
            preservation_agent = create_link_preservation_agent()
            markdown_results = preservation_agent.extract_and_convert(extraction_results)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to convert links: {str(e)}")
        
        return JSONResponse(content={
            "filename": file.filename,
            "status": "success",
            "markdown_links": markdown_results["markdown_links"],
            "markdown_links_with_metadata": markdown_results["markdown_links_with_metadata"],
            "total_links_converted": markdown_results["total_links_converted"]
        })
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@app.post("/ocr-agent")
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
 

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
