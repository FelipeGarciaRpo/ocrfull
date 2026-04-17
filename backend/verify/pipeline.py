"""
Veryfi-inspired Document Processing Pipeline
=============================================
Receipt / Invoice image → Standardized JSON

Flow:
  Image → Preprocess → OCR → Clean → Extract → Validate → JSON

Run:
  python pipeline.py --image receipt.jpg
  python pipeline.py --image receipt.jpg --debug
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

from steps.preprocessor import preprocess_image
from steps.ocr import run_ocr
from steps.cleaner import clean_text
from steps.extractor import extract_fields
from steps.validator import validate_document
from steps.formatter import format_json
import numpy as np

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("pipeline")


# ── Pipeline ───────────────────────────────────────────────────────────────────
def run_pipeline(image_path: str, debug: bool = False) -> dict:
    """
    Ejecuta el pipeline completo sobre una imagen de documento.

    Args:
        image_path: ruta a la imagen (jpg, png, pdf)
        debug:      si True, guarda resultados intermedios

    Returns:
        dict con el JSON estandarizado al estilo Veryfi
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Imagen no encontrada: {image_path}")

    log.info(f"📄 Procesando: {path.name}")
    results = {"_meta": {"source_file": path.name, "processed_at": datetime.utcnow().isoformat()}}

    # ── STEP 1: Preprocesamiento de imagen ─────────────────────────────────────
    log.info("STEP 1/6 ── Preprocesamiento de imagen")
    processed_image = preprocess_image(str(path))
    if debug:
        processed_image.save("debug_1_preprocessed.png")
        log.debug("  → debug_1_preprocessed.png guardada")

    # ── STEP 2: OCR ────────────────────────────────────────────────────────────
    log.info("STEP 2/6 ── OCR: imagen → texto")
    ocr_result = run_ocr(processed_image)
    results["_meta"]["ocr_confidence"] = ocr_result["confidence"]
    raw_text = ocr_result["text"]

    if debug:
        Path("debug_2_ocr_raw.txt").write_text(raw_text, encoding="utf-8")
        log.debug(f"  → OCR confidence: {ocr_result['confidence']:.2%}")

    # ── STEP 3: Limpieza de texto ───────────────────────────────────────────────
    log.info("STEP 3/6 ── Limpieza de texto OCR")
    clean = clean_text(raw_text)

    if debug:
        Path("debug_3_clean.txt").write_text(clean, encoding="utf-8")

    # ── STEP 4: Extracción de campos ───────────────────────────────────────────
    log.info("STEP 4/6 ── Extracción de campos (regex + pandas)")
    fields = extract_fields(clean)
    results.update(fields)

    if debug:
        log.debug(f"  → Campos extraídos: {list(fields.keys())}")

    # ── STEP 5: Validación ─────────────────────────────────────────────────────
    log.info("STEP 5/6 ── Validación de reglas de negocio")
    validation = validate_document(fields)
    results["_meta"]["validation"] = validation

    if validation["errors"]:
        log.warning(f"  ⚠ Errores de validación: {validation['errors']}")
    if validation["warnings"]:
        log.warning(f"  ⚠ Warnings: {validation['warnings']}")

    # ── STEP 6: Formateo JSON ──────────────────────────────────────────────────
    log.info("STEP 6/6 ── Formateando JSON final")
    output = format_json(results)

    return output

class NumpyEncoder(json.JSONEncoder):
    """Convierte tipos de NumPy a tipos nativos de Python para JSON."""
    def default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Veryfi-inspired pipeline")
    parser.add_argument("--image", required=True, help="Ruta a la imagen del documento")
    parser.add_argument("--debug", action="store_true", help="Guardar archivos intermedios")
    parser.add_argument("--output", default=None, help="Guardar JSON en archivo")
    args = parser.parse_args()

    try:
        result = run_pipeline(args.image, debug=args.debug)

        json_str = json.dumps(result, indent=2, ensure_ascii=False, cls=NumpyEncoder)
        print("\n" + "─" * 60)
        print(json_str)
        print("─" * 60)

        if args.output:
            Path(args.output).write_text(json_str, encoding="utf-8")
            log.info(f"✅ JSON guardado en: {args.output}")

        # Resumen
        meta = result.get("_meta", {})
        validation = meta.get("validation", {})
        status = "✅ VÁLIDO" if not validation.get("errors") else "⚠ CON ERRORES"
        log.info(f"\n{'─'*40}")
        log.info(f"  Estado:     {status}")
        log.info(f"  Confianza OCR: {meta.get('ocr_confidence', 0):.2%}")
        log.info(f"  Vendor:     {result.get('vendor', {}).get('name', 'No detectado')}")
        log.info(f"  Total:      {result.get('total', 'No detectado')}")
        log.info(f"  Fecha:      {result.get('date', 'No detectada')}")
        log.info(f"{'─'*40}\n")

    except FileNotFoundError as e:
        log.error(str(e))
        sys.exit(1)
    except Exception as e:
        log.exception(f"Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()