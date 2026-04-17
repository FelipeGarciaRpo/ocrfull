"""
STEP 3 — Limpieza de texto OCR
================================
Corrige los errores típicos que introduce el OCR antes
de que el extractor intente detectar patrones.

Errores comunes de Tesseract en documentos financieros:
  - Confunde O (letra) con 0 (número) en contextos numéricos
  - Confunde l (ele minúscula) con 1 (uno)
  - Confunde S con 5 en precios
  - Introduce espacios extra o saltos de línea innecesarios
  - Lee $ como S o viceversa
  - Caracteres de control basura (null bytes, etc.)
"""

import re
import logging

log = logging.getLogger("pipeline.cleaner")


def clean_text(raw_text: str) -> str:
    """
    Aplica la cadena de limpieza sobre el texto crudo del OCR.

    Args:
        raw_text: texto tal como lo entrega Tesseract

    Returns:
        texto limpio listo para extracción de campos
    """
    text = raw_text

    # 1. Eliminar caracteres de control y null bytes
    text = _remove_control_chars(text)

    # 2. Normalizar saltos de línea
    text = _normalize_newlines(text)

    # 3. Corregir errores típicos de OCR en contextos numéricos
    text = _fix_ocr_number_errors(text)

    # 4. Normalizar símbolo de moneda
    text = _normalize_currency_symbol(text)

    # 5. Eliminar líneas de ruido (separadores, páginas, etc.)
    text = _remove_noise_lines(text)

    # 6. Normalizar espacios múltiples dentro de cada línea
    text = _normalize_spaces(text)

    log.debug(f"  → Texto limpio: {len(text)} chars")
    return text


def _remove_control_chars(text: str) -> str:
    """Elimina caracteres de control excepto newlines y tabs."""
    # \x00-\x08 y \x0b-\x1f son caracteres de control no imprimibles
    return re.sub(r'[\x00-\x08\x0b-\x1f\x7f]', '', text)


def _normalize_newlines(text: str) -> str:
    """
    Normaliza saltos de línea.
    Windows usa \r\n, Mac antiguo usa \r, Linux usa \n.
    """
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Más de 2 líneas vacías seguidas → 2 máximo
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text

def _fix_ocr_number_errors(text: str) -> str:
    """
    Corrige confusiones letra/número del OCR en contextos numéricos.

    Importante: NO aplicar estas correcciones globalmente — solo
    dentro de secuencias que parecen números con precio/monto.

    Ejemplo:
      "Total: $1,23O.5O"  → "Total: $1,230.50"  ✅ correcto
      "OREO cookies"      → "0RE0 cookies"       ❌ no queremos esto
    """
    def fix_amount(match):
        s = match.group()
        s = s.replace('O', '0').replace('o', '0')
        s = s.replace('l', '1').replace('I', '1')
        s = s.replace('S', '5')
        s = s.replace('B', '8')
        return s

    # Aplicar solo sobre secuencias que parecen montos con $
    text = re.sub(r'\$[\dOolISB,\.]+', fix_amount, text)

    # Para montos sin $ pero con etiqueta (TOTAL, TAX, etc.)
    # Usamos grupos normales en vez de lookbehind (más compatible con Python)
    def fix_labeled_amount(match):
        label  = match.group(1)
        space  = match.group(2)
        amount = match.group(3)
        amount = amount.replace('O','0').replace('l','1').replace('S','5')
        return label + space + amount

    text = re.sub(
        r'(TOTAL|TAX|SUBTOTAL|AMOUNT|DUE|CHANGE)(\s{0,5})([\dOolISB,\.]+)',
        fix_labeled_amount,
        text,
        flags=re.IGNORECASE
    )

    return text


def _normalize_currency_symbol(text: str) -> str:
    """
    El OCR a veces lee $ como S o viceversa cuando está solo.
    Intentamos corregir el caso más obvio: "S1,234.50" → "$1,234.50"
    """
    # "S" seguida de dígitos al inicio de lo que parece un monto
    text = re.sub(r'\bS(\d)', r'$\1', text)
    return text


def _remove_noise_lines(text: str) -> str:
    """
    Elimina líneas que son puro ruido y no contienen información útil.
    Ejemplos: "------", "======", líneas de un solo carácter, etc.
    """
    lines = text.split('\n')
    clean_lines = []

    for line in lines:
        stripped = line.strip()

        # Línea de separación: solo guiones, asteriscos, igual, etc.
        if re.match(r'^[-=_*#~]{3,}$', stripped):
            continue

        # Línea de un solo carácter no significativo
        if len(stripped) == 1 and stripped not in ('$', '#', '%'):
            continue

        clean_lines.append(line)

    return '\n'.join(clean_lines)


def _normalize_spaces(text: str) -> str:
    """
    Normaliza espacios múltiples dentro de cada línea.
    Preserva los saltos de línea (importantes para el extractor).
    """
    lines = text.split('\n')
    # Reemplaza 2+ espacios por uno solo, dentro de cada línea
    lines = [re.sub(r'[ \t]{2,}', ' ', line) for line in lines]
    return '\n'.join(lines)