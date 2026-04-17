"""
STEP 2 — OCR (Optical Character Recognition)
==============================================
Convierte la imagen preprocesada en texto plano.

Usa pytesseract (wrapper de Python para Tesseract de Google).
Tesseract es el OCR open source más usado en la industria.

En producción, Veryfi usa su propio OCR engine propietario
optimizado para documentos financieros. Tesseract es el
equivalente open source más cercano.
"""

import logging
import numpy as np
import pytesseract
from PIL import Image

log = logging.getLogger("pipeline.ocr")


def run_ocr(image: Image.Image) -> dict:
    """
    Ejecuta OCR sobre la imagen preprocesada.

    Args:
        image: PIL.Image preprocesada

    Returns:
        dict con:
          - text: texto extraído
          - confidence: confianza promedio del OCR (0.0 a 1.0)
          - word_data: DataFrame con datos por palabra (posición, confianza)
    """
    # Configuración de Tesseract:
    # --oem 3  → usar el motor LSTM (más moderno y preciso)
    # --psm 4  → asumir una sola columna de texto de tamaños variables
    #            PSM 4 funciona mejor para recibos y facturas
    #
    # Otros PSM útiles:
    #   psm 6  → bloque de texto uniforme (facturas bien estructuradas)
    #   psm 11 → texto disperso (recibos con layout irregular)
    #   psm 3  → automático (default, bueno para documentos generales)
    config = "--oem 3 --psm 4"

    log.debug("  Ejecutando Tesseract...")

    # Extraer texto plano
    raw_text = pytesseract.image_to_string(image, config=config, lang="eng")

    # Extraer datos detallados por palabra (incluye confianza y posición)
    word_data = pytesseract.image_to_data(
        image,
        config=config,
        lang="eng",
        output_type=pytesseract.Output.DATAFRAME
    )

    # Calcular confianza promedio
    # Tesseract da -1 para palabras que no pudo leer
    valid_confidences = word_data[word_data["conf"] > 0]["conf"]
    avg_confidence = valid_confidences.mean() / 100.0 if len(valid_confidences) > 0 else 0.0

    log.debug(f"  → Palabras detectadas: {len(valid_confidences)}")
    log.debug(f"  → Confianza promedio: {avg_confidence:.2%}")
    log.debug(f"  → Texto extraído ({len(raw_text)} chars)")

    # Alerta si la calidad es baja
    if avg_confidence < 0.70:
        log.warning(f"  ⚠ Confianza OCR baja ({avg_confidence:.2%}) — resultados pueden ser imprecisos")

    return {
        "text": raw_text,
        "confidence": avg_confidence,
        "word_data": word_data
    }