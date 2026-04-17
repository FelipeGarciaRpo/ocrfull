"""
STEP 5 — Validación de reglas de negocio
==========================================
Verifica que los campos extraídos son coherentes y válidos.

Separa errores (datos incorrectos) de warnings (datos sospechosos).

Errores → el documento no debería usarse para entrenamiento sin revisión
Warnings → revisar manualmente, puede ser correcto o no

En Veryfi, los documentos con errores de validación se mandan
a un flujo de revisión humana (human-in-the-loop) en vez de
entrar directamente al pipeline de entrenamiento.
"""

import logging
import re
from datetime import datetime
from typing import Optional

log = logging.getLogger("pipeline.validator")

# Límites de negocio
MIN_AMOUNT = 0.01        # monto mínimo razonable
MAX_AMOUNT = 1_000_000   # monto máximo razonable (1 millón)
MIN_DATE   = datetime(2000, 1, 1)
MAX_DATE   = datetime.utcnow()


def validate_document(fields: dict) -> dict:
    """
    Valida los campos extraídos contra reglas de negocio.

    Args:
        fields: dict de campos extraídos por el extractor

    Returns:
        dict con:
          - is_valid: bool
          - errors:   lista de errores críticos
          - warnings: lista de advertencias
          - score:    puntuación de calidad 0-100
    """
    errors   = []
    warnings = []

    # ── Validaciones críticas (errors) ────────────────────────────────────────
    _validate_total(fields, errors, warnings)
    _validate_date(fields, errors, warnings)
    _validate_math_consistency(fields, errors, warnings)

    # ── Validaciones de calidad (warnings) ────────────────────────────────────
    _validate_vendor(fields, warnings)
    _validate_line_items(fields, warnings)
    _validate_currency(fields, warnings)
    _validate_document_number(fields, warnings)

    # ── Score de calidad ──────────────────────────────────────────────────────
    # Cada campo presente suma puntos, cada error resta
    score = _calculate_quality_score(fields, errors, warnings)

    result = {
        "is_valid": len(errors) == 0,
        "errors":   errors,
        "warnings": warnings,
        "score":    score
    }

    log.debug(f"  → Score de calidad: {score}/100")
    return result


# ── Validaciones individuales ──────────────────────────────────────────────────

def _validate_total(fields: dict, errors: list, warnings: list):
    """Valida que el total existe y es razonable."""
    total = fields.get('total')

    if total is None:
        errors.append("TOTAL_MISSING: No se pudo extraer el total del documento")
        return

    if total < MIN_AMOUNT:
        errors.append(f"TOTAL_TOO_LOW: Total {total} es menor al mínimo permitido ({MIN_AMOUNT})")

    if total > MAX_AMOUNT:
        errors.append(f"TOTAL_TOO_HIGH: Total {total} supera el máximo permitido ({MAX_AMOUNT:,})")

    if total != round(total, 2):
        warnings.append(f"TOTAL_PRECISION: Total {total} tiene más de 2 decimales")


def _validate_date(fields: dict, errors: list, warnings: list):
    """Valida que la fecha existe y está en un rango razonable."""
    date_str = fields.get('date')

    if date_str is None:
        warnings.append("DATE_MISSING: No se encontró fecha en el documento")
        return

    try:
        date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        errors.append(f"DATE_INVALID_FORMAT: Fecha '{date_str}' no tiene formato YYYY-MM-DD")
        return

    if date < MIN_DATE:
        warnings.append(f"DATE_TOO_OLD: Fecha {date_str} es anterior al año 2000")

    if date > MAX_DATE:
        errors.append(f"DATE_FUTURE: Fecha {date_str} es una fecha futura")


def _validate_math_consistency(fields: dict, errors: list, warnings: list):
    """
    Verifica que subtotal + tax ≈ total.
    Esta es la validación más potente — detecta errores de OCR
    que pasaron los otros filtros.
    """
    total    = fields.get('total')
    subtotal = fields.get('subtotal')
    tax      = fields.get('tax')

    if total is None:
        return
    if subtotal is None and tax is None:
        return  # no hay suficiente info para validar

    calculated = 0
    if subtotal:
        calculated += subtotal
    if tax:
        calculated += tax

    if calculated == 0:
        return

    # Tolerancia del 2% por errores de redondeo
    tolerance  = total * 0.02
    difference = abs(total - calculated)

    if difference > tolerance:
        warnings.append(
            f"MATH_INCONSISTENCY: subtotal({subtotal}) + tax({tax}) = "
            f"{calculated:.2f} ≠ total({total}). "
            f"Diferencia: {difference:.2f}"
        )


def _validate_vendor(fields: dict, warnings: list):
    """Valida que el vendor tiene información mínima."""
    vendor = fields.get('vendor', {})
    name   = vendor.get('name') if vendor else None

    if not name:
        warnings.append("VENDOR_MISSING: No se detectó nombre del proveedor")
        return

    if len(name) < 2:
        warnings.append(f"VENDOR_TOO_SHORT: Nombre de vendor '{name}' muy corto")

    if re.match(r'^\d+$', name):
        warnings.append(f"VENDOR_NUMERIC: Nombre de vendor '{name}' es solo números — probable error de OCR")


def _validate_line_items(fields: dict, warnings: list):
    """Valida los line items contra el total."""
    items = fields.get('line_items', [])
    total = fields.get('total')

    if not items:
        warnings.append("LINE_ITEMS_EMPTY: No se extrajeron items de línea")
        return

    # Verificar que la suma de items sea cercana al subtotal o total
    items_sum = sum(item.get('total', 0) for item in items)

    if total and items_sum > 0:
        # Permitir hasta 30% de diferencia (el OCR puede perder algunos items)
        ratio = abs(items_sum - total) / total
        if ratio > 0.30:
            warnings.append(
                f"LINE_ITEMS_SUM_MISMATCH: Suma de items ({items_sum:.2f}) "
                f"difiere del total ({total:.2f}) en {ratio:.1%}"
            )


def _validate_currency(fields: dict, warnings: list):
    """Valida que la moneda es un código ISO 4217 conocido."""
    currency = fields.get('currency_code')
    known_currencies = {'USD', 'COP', 'EUR', 'MXN', 'GBP', 'BRL', 'ARS', 'CLP', 'PEN'}

    if currency not in known_currencies:
        warnings.append(f"CURRENCY_UNKNOWN: Moneda '{currency}' no reconocida")


def _validate_document_number(fields: dict, warnings: list):
    """Valida el número de documento."""
    doc_num = fields.get('document_number')
    if doc_num is None:
        warnings.append("DOC_NUMBER_MISSING: No se encontró número de documento")


# ── Score de calidad ───────────────────────────────────────────────────────────

def _calculate_quality_score(fields: dict, errors: list, warnings: list) -> int:
    """
    Calcula un score de calidad de 0 a 100.
    Usado para priorizar revisión manual y filtrar datos de entrenamiento.
    """
    score = 100

    # Penalizar por errores críticos
    score -= len(errors) * 25

    # Penalizar por warnings
    score -= len(warnings) * 8

    # Bonificar por campos completos
    bonus_fields = ['total', 'date', 'vendor', 'subtotal', 'tax',
                    'line_items', 'currency_code', 'document_number']

    for field in bonus_fields:
        val = fields.get(field)
        if val not in (None, [], {}, ''):
            score += 2  # pequeño bonus por campo presente

    return max(0, min(100, score))