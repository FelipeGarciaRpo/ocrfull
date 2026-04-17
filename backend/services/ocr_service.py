# services/ocr_service.py

import logging
import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERIFY_DIR = os.path.join(BASE_DIR, 'verify')
sys.path.insert(0, VERIFY_DIR)
from pipeline import run_pipeline

logger = logging.getLogger(__name__)


def extract_first_page_from_pdf(pdf_path: str, output_image_path: str):
    """Converts the first page of a PDF to a PNG image."""
    try:
        import fitz  # pymupdf
        doc = fitz.open(pdf_path)
        page = doc[0]
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR quality
        pix = page.get_pixmap(matrix=mat)
        pix.save(output_image_path)
        doc.close()
        logger.info(f"PDF converted to image: {output_image_path}")
    except Exception as e:
        logger.error(f"PDF conversion failed: {e}")
        raise


def process_file_with_pipeline(file_path: str, file_ext: str, debug: bool = False):
    """
    Processes the file (converting PDF to image if necessary)
    and runs the OCR pipeline.
    Returns (result_dict, image_path) — never raises, always returns
    a safe fallback if something fails.
    """
    image_to_process = file_path

    # Convertir PDF a imagen si es necesario
    if file_ext.lower() == '.pdf':
        image_to_process = file_path.replace('.pdf', '_page0.png')
        try:
            extract_first_page_from_pdf(file_path, image_to_process)
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
            return _empty_pipeline_result(str(e)), file_path

    # Correr el pipeline OCR
    try:
        result = run_pipeline(image_to_process, debug=debug)
        return result, image_to_process
    except Exception as e:
        logger.warning(f"Pipeline failed, returning empty result: {e}")
        return _empty_pipeline_result(str(e)), image_to_process


def _empty_pipeline_result(error_msg: str = "") -> dict:
    """
    Resultado vacío seguro para cuando el pipeline falla.
    Permite que el benchmark continúe con Vision y Combined
    aunque el OCR no pueda extraer nada.
    """
    return {
        "document_type":   "unknown",
        "document_number": None,
        "vendor": {
            "name":    None,
            "address": None,
            "phone":   None,
        },
        "date":            None,
        "currency_code":   "USD",
        "subtotal":        None,
        "tax":             None,
        "discount":        None,
        "total":           None,
        "payment_method":  None,
        "line_items":      [],
        "ocr_confidence":  0.0,
        "raw_text":        "",
        "_quality": {
            "validation_score": 0,
            "is_valid":         False,
            "errors":           [error_msg] if error_msg else [],
            "warnings":         [],
            "ready_for_training": False,
        }
    }