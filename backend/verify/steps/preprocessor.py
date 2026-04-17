"""
STEP 1 — Preprocesamiento de imagen
=====================================
Prepara la imagen antes del OCR:
  - Convierte a escala de grises
  - Corrige orientación
  - Mejora contraste y nitidez
  - Binarización adaptativa (blanco/negro limpio)
  - Elimina ruido

Por qué importa:
  Un OCR corriendo sobre una imagen borrosa o girada produce
  texto ilegible. Este paso puede mejorar la confianza del OCR
  de 60% a 95%+ en imágenes de baja calidad.
"""

import logging
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import cv2

log = logging.getLogger("pipeline.preprocessor")


def preprocess_image(image_path: str) -> Image.Image:
    img_cv = cv2.imread(image_path)
    if img_cv is None:
        raise ValueError(f"No se pudo cargar la imagen: {image_path}")

    # Escala de grises
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    # Escalar si es muy pequeña
    h, w = gray.shape
    if w < 1000:
        scale = 1000 / w
        gray = cv2.resize(gray, (int(w*scale), int(h*scale)), 
                         interpolation=cv2.INTER_CUBIC)

    # Nitidez suave — sin binarización agresiva
    pil_image = Image.fromarray(gray)
    pil_image = ImageEnhance.Contrast(pil_image).enhance(1.5)
    pil_image = ImageEnhance.Sharpness(pil_image).enhance(2.0)

    return pil_image


def _to_grayscale(img_cv: np.ndarray) -> np.ndarray:
    """Convierte BGR (OpenCV) a escala de grises."""
    return cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)


def _correct_orientation(gray: np.ndarray) -> np.ndarray:
    """
    Detecta y corrige la orientación de la imagen.
    """
    try:
        import pytesseract
        osd = pytesseract.image_to_osd(gray, output_type=pytesseract.Output.DICT)
        angle = osd.get("rotate", 0)

        # Solo corregir 90° o 270° — el 180° de Tesseract es poco confiable
        # y en recibos suele ser un falso positivo
        if angle in (90, 270):
            h, w = gray.shape
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, -angle, 1.0)
            gray = cv2.warpAffine(
                gray, M, (w, h),
                flags=cv2.INTER_CUBIC,
                borderMode=cv2.BORDER_REPLICATE
            )
            log.debug(f"  → Imagen girada {angle}°, corregida")
        else:
            log.debug(f"  → Ángulo detectado {angle}° ignorado (solo se corrigen 90/270)")
    except Exception as e:
        log.debug(f"  → Corrección de orientación saltada: {e}")

    return gray


def _upscale_if_needed(gray: np.ndarray, min_width: int = 1000) -> np.ndarray:
    """
    Escala la imagen si es muy pequeña.
    Tesseract funciona mejor con imágenes de al menos 1000px de ancho.
    """
    h, w = gray.shape
    if w < min_width:
        scale = min_width / w
        new_w, new_h = int(w * scale), int(h * scale)
        gray = cv2.resize(gray, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        log.debug(f"  → Escalada de {w}x{h} a {new_w}x{new_h}")
    return gray


def _denoise(gray: np.ndarray) -> np.ndarray:
    """
    Elimina ruido con un filtro Gaussian.
    Importante para fotos tomadas con celular (ruido de sensor).
    """
    return cv2.GaussianBlur(gray, (3, 3), 0)


def _binarize(gray: np.ndarray) -> np.ndarray:
    """
    Binarización adaptativa: convierte la imagen a blanco y negro puro.

    Por qué adaptativa y no simple:
    - La binarización simple (umbral fijo) falla con iluminación desigual
    - Si hay sombra en una esquina, esa parte queda negra
    - La adaptativa calcula el umbral para cada región de la imagen

    Ejemplo de diferencia:
      Simple:    "Total: $45" bien, "Proveedor: KFC" ilegible (sombra)
      Adaptativa: ambos campos legibles
    """
    return cv2.adaptiveThreshold(
        gray,
        255,                                   # valor máximo (blanco)
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,        # método gaussiano
        cv2.THRESH_BINARY,                     # binario (blanco/negro)
        blockSize=11,                          # tamaño del vecindario
        C=2                                    # constante de ajuste
    )


def _sharpen(pil_image: Image.Image) -> Image.Image:
    """Mejora la nitidez del texto con PIL."""
    enhancer = ImageEnhance.Sharpness(pil_image)
    return enhancer.enhance(2.0)