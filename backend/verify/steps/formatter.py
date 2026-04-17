"""
STEP 6 — Formateador JSON
==========================
Toma todos los campos extraídos y validados y los convierte
en el JSON estandarizado final — al estilo del output de Veryfi.

El JSON sigue el schema de la API de Veryfi para que sea familiar
a cualquiera que haya trabajado con su producto.

Referencia: https://www.veryfi.com/api/docs/
"""

import logging
from datetime import datetime
from typing import Optional

log = logging.getLogger("pipeline.formatter")


def format_json(data: dict) -> dict:
    """
    Construye el JSON final estandarizado.

    Args:
        data: dict con todos los campos extraídos + _meta

    Returns:
        JSON al estilo de la API de Veryfi
    """
    meta       = data.get("_meta", {})
    vendor     = data.get("vendor", {}) or {}
    validation = meta.get("validation", {})

    output = {
        # ── Identificación ─────────────────────────────────────────────────
        "id":                     _generate_id(meta.get("source_file", "")),
        "created_date":           datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "source_file":            meta.get("source_file"),

        # ── Tipo de documento ──────────────────────────────────────────────
        "document_type":          data.get("document_type", "unknown"),
        "document_reference_number": data.get("document_number"),

        # ── Vendor / Proveedor ─────────────────────────────────────────────
        "vendor": {
            "name":    vendor.get("name"),
            "address": vendor.get("address"),
            "phone":   vendor.get("phone"),
            "logo":    None,  # requeriría búsqueda externa
        },

        # ── Fechas ──────────────────────────────────────────────────────────
        "date":         data.get("date"),

        # ── Montos ──────────────────────────────────────────────────────────
        "currency_code": data.get("currency_code", "USD"),
        "subtotal":      _round_amount(data.get("subtotal")),
        "tax":           _round_amount(data.get("tax")),
        "discount":      _round_amount(data.get("discount")),
        "total":         _round_amount(data.get("total")),

        # ── Pago ────────────────────────────────────────────────────────────
        "payment_method": data.get("payment_method"),

        # ── Line Items ──────────────────────────────────────────────────────
        "line_items": _format_line_items(data.get("line_items", [])),

        # ── Metadatos de calidad ─────────────────────────────────────────────
        # Estos campos son internos — en Veryfi no van en el output al cliente
        # pero sí en el sistema interno de calidad de datos
        "_quality": {
            "ocr_confidence":  round(meta.get("ocr_confidence", 0), 4),
            "validation_score": validation.get("score", 0),
            "is_valid":         validation.get("is_valid", False),
            "errors":           validation.get("errors", []),
            "warnings":         validation.get("warnings", []),
            "ready_for_training": _is_ready_for_training(meta, validation),
        }
    }

    log.debug("  ✓ JSON formateado correctamente")
    return output


def _format_line_items(items: list) -> list:
    """Estandariza el formato de cada line item."""
    formatted = []
    for i, item in enumerate(items):
        formatted.append({
            "id":          i + 1,
            "description": item.get("description", ""),
            "quantity":    item.get("quantity", 1),
            "unit_price":  _round_amount(item.get("unit_price")),
            "total":       _round_amount(item.get("total")),
        })
    return formatted


def _round_amount(value: Optional[float]) -> Optional[float]:
    """Redondea un monto a 2 decimales. None si no hay valor."""
    if value is None:
        return None
    return round(value, 2)


def _generate_id(source_file: str) -> str:
    """
    Genera un ID único para el documento basado en el archivo y timestamp.
    En producción se usaría UUID o el ID de la base de datos.
    """
    import hashlib
    timestamp = datetime.utcnow().isoformat()
    raw = f"{source_file}_{timestamp}"
    return hashlib.md5(raw.encode()).hexdigest()[:12].upper()


def _is_ready_for_training(meta: dict, validation: dict) -> bool:
    """
    Determina si el documento está listo para usarse en entrenamiento.

    Criterios:
    - OCR confidence >= 70%
    - Sin errores de validación críticos
    - Score de calidad >= 60
    """
    ocr_ok         = meta.get("ocr_confidence", 0) >= 0.70
    no_errors      = len(validation.get("errors", [])) == 0
    score_ok       = validation.get("score", 0) >= 60

    return ocr_ok and no_errors and score_ok