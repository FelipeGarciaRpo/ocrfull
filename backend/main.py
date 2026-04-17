import os
import time
import uuid
import logging
import subprocess
from typing import Dict, Any
from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import asyncio
from services.vision_service import classify_with_vision
import json
import numpy as np

from models.schemas import ProcessResponse, HealthResponse, ErrorResponse
from services.ocr_service import process_file_with_pipeline
from services.claude_service import classify_and_extract_with_claude

# Load env variables (if .env is present)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="DocuScan AI", description="Document Scanning AI Backend", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", 10))
TMP_DIR = os.getenv("TMP_DIR", "/tmp/docuscan")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"

os.makedirs(TMP_DIR, exist_ok=True)

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=str(exc),
            code="UNKNOWN_ERROR",
            processing_time_ms=0
        ).model_dump()
    )

@app.get("/health", response_model=HealthResponse)
def health_check():
    tesseract_version = "unknown"
    try:
        result = subprocess.run(['tesseract', '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.stdout:
            tesseract_version = result.stdout.split('\n')[0].split(' ')[1]
    except Exception:
        pass
        
    return HealthResponse(
        status="ok",
        tesseract_version=tesseract_version,
        pipeline="ready"
    )

@app.post("/process", response_model=ProcessResponse)
async def process_document(file: UploadFile = File(...)):
    start_time = time.time()
    temp_file_path = None
    temp_img_path = None
    
    try:
        # Validate extension
        _, ext = os.path.splitext(file.filename)
        ext = ext.lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.tiff', '.pdf', '.webp', '.heic', '.jfif', '.bmp']:
            raise HTTPException(status_code=415, detail="INVALID_FORMAT")
            
        # Write to temp file while checking size
        file_id = str(uuid.uuid4())
        temp_file_path = os.path.join(TMP_DIR, f"{file_id}{ext}")
        
        file_size = 0
        with open(temp_file_path, "wb") as buffer:
            while chunk := await file.read(8192):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="FILE_TOO_LARGE")
                buffer.write(chunk)
                
        logger.info(f"Received file: {file.filename}, saved as {temp_file_path}, size: {file_size} bytes")
        
        # 1. Run Pipeline
        try:
            pipeline_result, temp_img_path = process_file_with_pipeline(temp_file_path, ext, debug=DEBUG)
            if not pipeline_result or "error" in pipeline_result:
                raise ValueError(pipeline_result.get("error", "Pipeline returned no result"))
        except Exception as e:
            logger.error(f"OCR Pipeline failed: {e}")
            return JSONResponse(
                status_code=422,
                content=ErrorResponse(
                    error=f"OCR processing failed: {str(e)}",
                    code="OCR_FAILED",
                    processing_time_ms=int((time.time() - start_time) * 1000)
                ).model_dump()
            )
            
        # Extract fields from pipeline result
        ocr_text = pipeline_result.get("raw_text", "")
        if not ocr_text: # Fallback just in case pipeline implementation varies
            ocr_text = str(pipeline_result)
            
        # 2. Call Claude API
        try:
            claude_result = classify_and_extract_with_claude(ocr_text, pipeline_result)
        except Exception as e:
            logger.error(f"Claude extraction failed: {e}")
            return JSONResponse(
                status_code=502,
                content=ErrorResponse(
                    error=f"Smart classification failed: {str(e)}",
                    code="CLAUDE_ERROR",
                    processing_time_ms=int((time.time() - start_time) * 1000)
                ).model_dump()
            )
            
        # 3. Merge Results
        document_type = claude_result.get("document_type", "UNKNOWN")
        confidence = float(claude_result.get("confidence", 0.0))
        summary = claude_result.get("summary", "")
        claude_keys = claude_result.get("key_fields", {})
        
        # Merge Vendor (Pipeline > Claude preference)
        vendor_data = pipeline_result.get("vendor") or claude_keys.get("vendor") or {}
        if isinstance(vendor_data, dict) and vendor_data:
            vendor = {
                "name": vendor_data.get("name"),
                "address": vendor_data.get("address"),
                "phone": vendor_data.get("phone")
            }
        else:
            vendor = None
            
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        response = ProcessResponse(
            document_type=document_type,
            confidence=confidence,
            ocr_confidence=pipeline_result.get("ocr_confidence", 0.85),
            vendor=vendor,
            date=pipeline_result.get("date") or claude_keys.get("date"),
            total=pipeline_result.get("total") or claude_keys.get("total"),
            currency_code=pipeline_result.get("currency_code") or claude_keys.get("currency_code"),
            document_number=pipeline_result.get("document_number") or claude_keys.get("document_number"),
            payment_method=pipeline_result.get("payment_method") or claude_keys.get("payment_method"),
            line_items=pipeline_result.get("line_items", []) or claude_keys.get("line_items", []),
            summary=summary,
            raw_json={"pipeline": pipeline_result, "claude": claude_result},
            processing_time_ms=processing_time_ms,
            ready_for_training=True
        )
        
        return response
        
    except HTTPException as e:
        status_map = {413: "FILE_TOO_LARGE", 415: "INVALID_FORMAT"}
        code = status_map.get(e.status_code, "UNKNOWN_ERROR")
        return JSONResponse(
            status_code=e.status_code,
            content=ErrorResponse(
                error=e.detail,
                code=code,
                processing_time_ms=int((time.time() - start_time) * 1000)
            ).model_dump()
        )
    finally:
        # Cleanup temp files
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except Exception as e:
                logger.warning(f"Could not remove temp file {temp_file_path}: {e}")
        
        if temp_img_path and temp_file_path != temp_img_path and os.path.exists(temp_img_path):
            try:
                os.remove(temp_img_path)
            except Exception as e:
                logger.warning(f"Could not remove temp image file {temp_img_path}: {e}")


def sanitize(obj):
    """Convierte tipos NumPy a tipos nativos de Python."""
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(i) for i in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

@app.post("/benchmark")
async def benchmark_document(file: UploadFile = File(...)):
    """
    Corre los 3 pipelines en paralelo y devuelve comparación.
    OCR Only | Vision Only | OCR + Vision Combined
    """
    start_time = time.time()
    temp_file_path = None
    temp_img_path = None

    # Guardar archivo temporal
    _, ext = os.path.splitext(file.filename)
    ext = ext.lower()

    if ext not in ['.jpg', '.jpeg', '.png', '.tiff', '.pdf', '.webp', '.heic', '.jfif', '.bmp']:
        raise HTTPException(status_code=415, detail="INVALID_FORMAT")

    file_id = str(uuid.uuid4())
    temp_file_path = os.path.join(TMP_DIR, f"{file_id}{ext}")

    with open(temp_file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    logger.info(f"Benchmark started: {file.filename} ({len(content)} bytes)")

    try:
        # ── STEP 1: OCR Pipeline ──────────────────────────────────
        # process_file_with_pipeline nunca lanza — devuelve fallback si falla
        pipeline_result, temp_img_path = process_file_with_pipeline(
            temp_file_path, ext, debug=False
        )
        image_path = temp_img_path or temp_file_path
        ocr_text   = pipeline_result.get("raw_text", "") or ""

        logger.info(f"OCR done. Confidence: {pipeline_result.get('ocr_confidence', 0):.2%}")

        # ── STEP 2: Correr los 3 en paralelo ──────────────────────
        loop = asyncio.get_event_loop()

        ocr_task = loop.run_in_executor(
            None,
            lambda: _run_ocr_only(pipeline_result)
        )
        vision_task = loop.run_in_executor(
            None,
            lambda: _safe_vision(image_path)
        )
        combined_task = loop.run_in_executor(
            None,
            lambda: _safe_combined(ocr_text, pipeline_result)
        )

        ocr_result, vision_result, combined_result = await asyncio.gather(
            ocr_task, vision_task, combined_task
        )

        total_time = int((time.time() - start_time) * 1000)
        logger.info(f"Benchmark complete in {total_time}ms")

        pipeline_result = sanitize(pipeline_result)
        ocr_result      = sanitize(ocr_result)
        vision_result   = sanitize(vision_result)
        combined_result = sanitize(combined_result)

        return JSONResponse(
        content={
            "processing_time_ms": total_time,
            "ocr_only": {
                "document_type":  ocr_result.get("document_type", "UNKNOWN"),
                "confidence":     ocr_result.get("confidence", 0.0),
                "ocr_confidence": pipeline_result.get("ocr_confidence", 0.0),
                "fields":         ocr_result.get("fields", {}),
                "summary":        ocr_result.get("summary", ""),
                "processing_ms":  ocr_result.get("processing_ms", 0),
            },
            "vision_only": {
                "document_type": vision_result.get("document_type", "UNKNOWN"),
                "confidence":    vision_result.get("confidence", 0.0),
                "fields":        vision_result.get("key_fields", {}),
                "summary":       vision_result.get("summary", ""),
            },
            "combined": {
                "document_type":  combined_result.get("document_type", "UNKNOWN"),
                "confidence":     combined_result.get("confidence", 0.0),
                "ocr_confidence": pipeline_result.get("ocr_confidence", 0.0),
                "fields":         combined_result.get("key_fields", {}),
                "summary":        combined_result.get("summary", ""),
            },
        },
        media_type="application/json"
    )

    except Exception as e:
        logger.error(f"Benchmark failed unexpectedly: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error=str(e),
                code="UNKNOWN_ERROR",
                processing_time_ms=int((time.time() - start_time) * 1000)
            ).model_dump()
        )

    finally:
        for path in [temp_file_path, temp_img_path]:
            if path and path != temp_file_path or path == temp_img_path:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except Exception as ex:
                        logger.warning(f"Could not remove temp file {path}: {ex}")


# ── Helpers seguros para el benchmark ─────────────────────────

def _safe_vision(image_path: str) -> dict:
    """Vision con fallback si falla."""
    try:
        return classify_with_vision(image_path)
    except Exception as e:
        logger.error(f"Vision pipeline failed: {e}")
        return {
            "document_type": "UNKNOWN",
            "confidence":    0.0,
            "summary":       f"Vision model failed: {str(e)}",
            "key_fields":    {}
        }


def _safe_combined(ocr_text: str, pipeline_result: dict) -> dict:
    """Combined con fallback si falla."""
    try:
        # Sanitizar ANTES de pasar al LLM — json.dumps explota con numpy.bool_
        clean_pipeline = sanitize(pipeline_result)
        return classify_and_extract_with_claude(ocr_text, clean_pipeline)
    except Exception as e:
        logger.error(f"Combined pipeline failed: {e}")
        return {
            "document_type": "UNKNOWN",
            "confidence":    0.0,
            "summary":       f"Combined model failed: {str(e)}",
            "key_fields":    {}
        }


def _run_ocr_only(pipeline_result: dict) -> dict:
    """
    Extrae campos solo del pipeline OCR — sin llamar al LLM.
    """
    vendor = pipeline_result.get("vendor", {}) or {}
    return {
        "document_type": pipeline_result.get("document_type", "UNKNOWN").upper(),
        "confidence":    pipeline_result.get("_quality", {}).get("validation_score", 0) / 100,
        "summary":       f"OCR extracted document. Type: {pipeline_result.get('document_type', 'unknown')}.",
        "fields": {
            "vendor":          vendor.get("name"),
            "date":            pipeline_result.get("date"),
            "total":           pipeline_result.get("total"),
            "currency":        pipeline_result.get("currency_code"),
            "document_number": pipeline_result.get("document_number"),
            "payment_method":  pipeline_result.get("payment_method"),
        },
        "processing_ms": 0
    }