import os
import base64
import json
import logging
from groq import Groq

logger = logging.getLogger(__name__)

# Debe ser un modelo multimodal de Groq (acepta image_url).
# Configurable porque Groq retira modelos: si este desaparece, se cambia
# la env var en vez de redesplegar codigo.
VISION_MODEL = os.getenv("GROQ_VISION_MODEL", "qwen/qwen3.8-27b")

def classify_with_vision(image_path: str) -> dict:
    """
    Manda la imagen directamente al modelo multimodal.
    El modelo VE la imagen — no necesita OCR previo.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    client = Groq(api_key=api_key)

    # Convertir imagen a base64
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    # Detectar mime type
    ext = image_path.lower().split(".")[-1]
    mime_map = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png",  "tiff": "image/tiff",
        "webp": "image/webp"
    }
    mime_type = mime_map.get(ext, "image/jpeg")

    prompt = """You are a document classification and data extraction AI.

Look at this document image and return ONLY a valid JSON object:

{
  "document_type": "one of: INVOICE, RECEIPT, CONTRACT, ID_CARD, BANK_STATEMENT, W2_TAX_FORM, CHECK, MEDICAL_RECORD, UNKNOWN",
  "confidence": 0.0,
  "summary": "2-3 sentence description in English",
  "key_fields": {
    "vendor": "string or null",
    "date": "YYYY-MM-DD or null",
    "total": number or null,
    "currency": "USD/COP/EUR or null",
    "document_number": "string or null",
    "payment_method": "string or null"
  }
}

Return ONLY the JSON. No explanation. No markdown."""

    try:
        response = client.chat.completions.create(
            model=VISION_MODEL,
            max_tokens=1024,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )

        result = json.loads(response.choices[0].message.content.strip())
        logger.info(f"Vision clasificó como: {result.get('document_type')}")
        return result

    except Exception as e:
        logger.error(f"Vision extraction failed: {e}")
        return {
            "document_type": "UNKNOWN",
            "confidence": 0.0,
            "summary": "Vision model could not classify document.",
            "key_fields": {}
        }