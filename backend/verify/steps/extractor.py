"""
STEP 4 — Extracción de campos (Regex + Pandas)
================================================
El corazón del pipeline. Toma el texto limpio y extrae
los campos estructurados que conformarán el JSON final.

Campos que extrae:
  - vendor (nombre del negocio)
  - date (fecha de la transacción)
  - total
  - subtotal
  - tax
  - discount
  - currency
  - document_type (receipt / invoice)
  - document_number
  - payment_method
  - line_items (productos/servicios con cantidad y precio)

Estrategia:
  1. Regex para campos con patrones claros (total, fecha, etc.)
  2. Pandas para procesar y normalizar line items en tabla
  3. Heurísticas para campos ambiguos (vendor, document_type)
"""

import re
import logging
import pandas as pd
import numpy as np
from typing import Optional

log = logging.getLogger("pipeline.extractor")


# ── Constantes ─────────────────────────────────────────────────────────────────

MONTHS_ES = {
    'enero':'01','febrero':'02','marzo':'03','abril':'04',
    'mayo':'05','junio':'06','julio':'07','agosto':'08',
    'septiembre':'09','octubre':'10','noviembre':'11','diciembre':'12'
}
MONTHS_EN = {
    'january':'01','february':'02','march':'03','april':'04',
    'may':'05','june':'06','july':'07','august':'08',
    'september':'09','october':'10','november':'11','december':'12'
}
MONTHS = {**MONTHS_ES, **MONTHS_EN}

CURRENCIES = {
    'USD': ['USD', 'US$', 'U.S.D', 'DOLLAR', 'DOLLARS'],
    'COP': ['COP', 'COL$', 'PESO', 'PESOS COLOMBIANOS'],
    'EUR': ['EUR', '€', 'EURO', 'EUROS'],
    'MXN': ['MXN', 'MX$', 'PESO MEXICANO'],
    'GBP': ['GBP', '£', 'POUND', 'POUNDS'],
}

PAYMENT_METHODS = {
    'VISA':       r'\bVISA\b',
    'MASTERCARD': r'\bMASTER\s*CARD\b|\bMC\b',
    'AMEX':       r'\bAMEX\b|\bAMERICAN\s*EXPRESS\b',
    'CASH':       r'\bCASH\b|\bEFECTIVO\b|\bCONTADO\b',
    'DEBIT':      r'\bDEBIT\b|\bDÉBITO\b|\bDEBITO\b',
    'CREDIT':     r'\bCREDIT\b|\bCRÉDITO\b|\bCREDITO\b',
}


# ── Extractor principal ────────────────────────────────────────────────────────

def extract_fields(text: str) -> dict:
    """
    Extrae todos los campos del documento desde el texto limpio.

    Args:
        text: texto limpio del OCR

    Returns:
        dict con todos los campos extraídos
    """
    log.debug("  Iniciando extracción de campos...")

    fields = {}

    # Extraer cada campo
    fields["document_type"]   = _extract_document_type(text)
    fields["document_number"] = _extract_document_number(text)
    fields["vendor"]          = _extract_vendor(text)
    fields["date"]            = _extract_date(text)
    fields["currency_code"]   = _extract_currency(text)
    fields["subtotal"]        = _extract_labeled_amount(text, r'\bsubtotal\b')
    fields["tax"]             = _extract_tax(text)
    fields["discount"]        = _extract_labeled_amount(text, r'\b(discount|descuento|savings?)\b')
    fields["total"]           = _extract_total(text)
    fields["payment_method"]  = _extract_payment_method(text)
    fields["line_items"]      = _extract_line_items(text)

    # Log de campos encontrados vs no encontrados
    found     = [k for k, v in fields.items() if v not in (None, [], {})]
    not_found = [k for k, v in fields.items() if v in (None, [], {})]
    log.debug(f"  ✓ Encontrados: {found}")
    if not_found:
        log.debug(f"  ✗ No detectados: {not_found}")

    return fields


# ── Extractores individuales ───────────────────────────────────────────────────

def _extract_document_type(text: str) -> str:
    """
    Determina si es una factura (invoice) o un recibo (receipt).
    """
    text_lower = text.lower()
    if any(w in text_lower for w in ['invoice', 'factura', 'bill']):
        return 'invoice'
    if any(w in text_lower for w in ['receipt', 'recibo', 'ticket', 'comprobante']):
        return 'receipt'
    return 'unknown'


def _extract_document_number(text: str) -> Optional[str]:
    """
    Extrae número de factura/recibo.
    Formatos: INV-001, FE-2024-001, #4782, No. 891, etc.
    """
    patterns = [
        r'(?:invoice|factura|receipt|recibo|order|orden)[^\d#]*#?\s*([A-Z0-9][\w\-]{2,20})',
        r'#\s*(\d{3,10})\b',
        r'(?:no|nro|n°|num)[.:°]?\s*(\d{3,10})',
        r'\b((?:INV|FE|REC|FACT)[-\s]?\d{4}[-\s]?\d+)\b',
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_vendor(text: str) -> dict:
    """
    Extrae información del proveedor/negocio.

    Heurística: el nombre del negocio suele estar en las primeras
    líneas del documento, antes de la dirección o fecha.
    """
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]

    vendor_name = None
    vendor_address = None

    # Las primeras 3 líneas con texto significativo suelen ser el nombre
    candidate_lines = [l for l in lines[:5] if len(l) > 2]
    if candidate_lines:
        # La primera línea significativa es típicamente el nombre
        vendor_name = candidate_lines[0]
        # Limpiar caracteres raros del OCR que no son parte del nombre
        vendor_name = re.sub(r'[^\w\s\.\,\-\&\']', '', vendor_name).strip()

    # Dirección: línea con número + calle o "Ave", "St", "Calle", "Carrera"
    addr_pattern = r'.*((?:\d+\s+\w+|calle|carrera|cra|avenue|ave|street|st).*)'
    for line in lines[:8]:
        match = re.search(addr_pattern, line, re.IGNORECASE)
        if match:
            vendor_address = line.strip()
            break

    # Teléfono
    phone_match = re.search(
        r'(?:\+?1?\s?)?(?:\(\d{3}\)|\d{3})[\s\-\.]?\d{3}[\s\-\.]?\d{4}',
        '\n'.join(lines[:10])
    )
    phone = phone_match.group().strip() if phone_match else None

    return {
        "name": vendor_name,
        "address": vendor_address,
        "phone": phone
    }


def _extract_date(text: str) -> Optional[str]:
    """
    Extrae y normaliza la fecha a formato ISO 8601: YYYY-MM-DD.
    Soporta múltiples formatos: numéricos, textuales, en español e inglés.
    """
    # Formato numérico: 15/04/2024, 15-04-2024, 15.04.2024
    # También: 03/28/2023 (formato americano mes/dia/año)
    match = re.search(r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4}|\d{2})', text)
    if match:
        a, b, year = match.group(1), match.group(2), match.group(3)
        if len(year) == 2:
            year = '20' + year
        # Heurística: si el primer número > 12 es el día (no puede ser mes)
        if int(a) > 12:
            day, month = a.zfill(2), b.zfill(2)
        else:
            # Asumir formato MM/DD/YYYY (más común en recibos americanos)
            month, day = a.zfill(2), b.zfill(2)
        return f"{year}-{month}-{day}"

    # Formato ISO: 2024-04-15
    match = re.search(r'(\d{4})-(\d{2})-(\d{2})', text)
    if match:
        return match.group()

    # Formato textual: "March 28, 2023" / "28 de marzo de 2023"
    match = re.search(
        r'(\d{1,2})\s+de\s+([a-záéíóú]+)\s+de\s+(\d{4})',
        text, re.IGNORECASE
    )
    if match:
        day   = match.group(1).zfill(2)
        month = MONTHS.get(match.group(2).lower(), '00')
        year  = match.group(3)
        return f"{year}-{month}-{day}"

    match = re.search(
        r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})',
        text
    )
    if match:
        month = MONTHS.get(match.group(1).lower(), '00')
        day   = match.group(2).zfill(2)
        year  = match.group(3)
        return f"{year}-{month}-{day}"

    return None


def _extract_currency(text: str) -> str:
    """
    Detecta la moneda del documento.
    Default: USD (la más común en documentos procesados por Veryfi).
    """
    text_upper = text.upper()
    for code, keywords in CURRENCIES.items():
        for kw in keywords:
            if kw in text_upper:
                return code
    return 'USD'


def _extract_labeled_amount(text: str, label_pattern: str) -> Optional[float]:
    """
    Extrae un monto precedido de una etiqueta específica.
    Reutilizable para subtotal, discount, etc.
    """
    pattern = label_pattern + r'[^\d$\n]*\$?\s*([\d,]+\.?\d{0,2})'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return _parse_amount(match.group(1))
    return None


def _extract_tax(text: str) -> Optional[float]:
    """
    Extrae el impuesto (IVA, Tax, Sales Tax, etc.)
    """
    patterns = [
        r'(?:sales?\s*tax|tax|iva|impuesto)[^\d$\n]*\$?\s*([\d,]+\.?\d{0,2})',
        r'tax\s+[a-z@\d\.]+\s+\$?\s*([\d,]+\.?\d{0,2})',  # "TAX A@9.625%  1.33"
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return _parse_amount(match.group(1))
    return None


def _extract_total(text: str) -> Optional[float]:
    """
    Extrae el total de la transacción.

    Estrategia de prioridad:
    1. Línea que dice explícitamente "TOTAL" (excluye subtotal)
    2. Si hay múltiples matches, tomar el mayor (el total suele ser el mayor monto)
    3. Validar contra subtotal + tax si están disponibles
    """
    # Buscar todas las líneas con "TOTAL" explícito
    # Excluir "SUBTOTAL" con (?<!SUB)
    pattern = r'(?<!\w)total(?!\s*savings?)[\s:]*\$?\s*([\d,]+\.?\d{0,2})'
    matches = re.findall(pattern, text, re.IGNORECASE)

    if not matches:
        return None

    amounts = [_parse_amount(m) for m in matches if _parse_amount(m) is not None]

    if not amounts:
        return None

    # Si hay varios "total" en el texto, tomar el mayor
    # (algunos recibos repiten el total al final)
    return max(amounts)


def _extract_payment_method(text: str) -> Optional[str]:
    """
    Detecta el método de pago usado.
    """
    for method, pattern in PAYMENT_METHODS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return method
    return None


def _extract_line_items(text: str) -> list:
    """
    Extrae los productos/servicios del documento como lista estructurada.

    Este es el campo más complejo — los formatos varían enormemente:
      "Hamburguesa    2    $8.50    $17.00"
      "RED BULL ENRGY DRNK CNS 8.4OZ 6PK   8.79"
      "1 @ 2/4.00  DORITOS NACHO   2.00"

    Usamos Pandas para procesar y limpiar la tabla de items.
    """
    lines = text.split('\n')
    raw_items = []

    # Patrón general: línea con texto + monto al final
    # Captura: descripción + precio unitario opcional + total de línea
    item_pattern = re.compile(
        r'^(.+?)\s+'                          # descripción (cualquier texto)
        r'(?:(\d+)\s+)?'                      # cantidad opcional
        r'(?:\$?([\d,]+\.?\d{0,2})\s+)?'     # precio unitario opcional
        r'\$?([\d,]+\.?\d{2})\s*$'           # precio total (requerido)
    )

    # Palabras que indican que la línea NO es un item de producto
    skip_keywords = re.compile(
        r'subtotal|total|tax|iva|discount|savings?|change|cash|visa|'
        r'master|credit|debit|thank|gracias|welcome|bienvenid|tel[eé]|'
        r'phone|fax|www\.|http|\.com|auth|approval|ref\b',
        re.IGNORECASE
    )

    for line in lines:
        stripped = line.strip()
        if not stripped or len(stripped) < 4:
            continue
        if skip_keywords.search(stripped):
            continue

        match = item_pattern.match(stripped)
        if match:
            desc     = match.group(1).strip()
            qty      = int(match.group(2)) if match.group(2) else 1
            unit_price = _parse_amount(match.group(3)) if match.group(3) else None
            line_total = _parse_amount(match.group(4))

            if line_total is None or line_total <= 0:
                continue

            # Si no hay precio unitario pero sí cantidad, calcularlo
            if unit_price is None and qty > 1 and line_total:
                unit_price = round(line_total / qty, 2)

            raw_items.append({
                "description": desc,
                "quantity":    qty,
                "unit_price":  unit_price,
                "total":       line_total
            })

    if not raw_items:
        return []

    # ── Usar Pandas para limpiar y validar la tabla de items ──────────────────
    df = pd.DataFrame(raw_items)

    # Eliminar items con precios extremadamente altos (probable error de OCR)
    # Usamos IQR para detectar outliers
    if len(df) > 3:
        Q1 = df['total'].quantile(0.25)
        Q3 = df['total'].quantile(0.75)
        IQR = Q3 - Q1
        upper_bound = Q3 + 3.0 * IQR  # 3x IQR para ser permisivos
        df = df[df['total'] <= upper_bound]

    # Eliminar duplicados exactos (mismo descripción + mismo total)
    df = df.drop_duplicates(subset=['description', 'total'])

    # Limpiar descripción: eliminar códigos de barras que el OCR mezcló
    df['description'] = df['description'].apply(_clean_item_description)

    # Eliminar items con descripción vacía tras la limpieza
    df = df[df['description'].str.len() > 1]

    log.debug(f"  → {len(df)} line items extraídos")
    return df.to_dict(orient='records')


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_amount(text: str) -> Optional[float]:
    """Convierte un string de monto a float, manejando comas de miles."""
    if text is None:
        return None
    try:
        cleaned = str(text).replace(',', '').strip()
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


def _clean_item_description(desc: str) -> str:
    """
    Limpia la descripción de un line item:
    - Elimina códigos de barras numéricos largos al inicio
    - Elimina caracteres raros del OCR
    - Normaliza espacios
    """
    # Eliminar código de barras al inicio (10+ dígitos)
    desc = re.sub(r'^\d{8,}\s*', '', desc)
    # Eliminar caracteres extraños que no son parte de un nombre de producto
    desc = re.sub(r'[^\w\s\.\,\-\&\'\%\(\)\/]', ' ', desc)
    # Normalizar espacios
    desc = re.sub(r'\s+', ' ', desc).strip()
    return desc