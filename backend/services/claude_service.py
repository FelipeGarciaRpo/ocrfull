import os
import json
import logging
from groq import Groq

logger = logging.getLogger(__name__)

def classify_and_extract_with_claude(ocr_text: str, pipeline_fields: dict) -> dict:
    """
    Sends the OCR text and pipeline fields to Llama 4 Scout via Groq
    to get document classification and summary.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your_key_here":
        logger.error("ANTHROPIC_API_KEY is not set or is using placeholder.")
        raise ValueError("Groq API Key configuration is missing.")

    client = Groq(api_key=api_key)

    prompt = f"""You are a document classification and data extraction AI.
   
Given the following text extracted via OCR from a document,
return ONLY a valid JSON object with these fields:

{{
  "document_type": "one of: INVOICE, RECEIPT, CONTRACT, ID_CARD, BANK_STATEMENT, W2_TAX_FORM, CHECK, MEDICAL_RECORD, UNKNOWN",
  "confidence": 0.0,
  "summary": "2-3 sentence description in English",
  "key_fields": {{}}
}}

OCR Text:
{ocr_text[:3000]}

Pipeline extracted fields:
{json.dumps(pipeline_fields)}

Return ONLY the JSON. No explanation. No markdown."""

    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            max_tokens=1024,
            temperature=0.0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        response_text = response.choices[0].message.content.strip()
        return json.loads(response_text)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON response: {response_text}")
        raise ValueError("Invalid JSON response from LLM")
    except Exception as e:
        logger.error(f"Unexpected error calling Groq: {e}")
        raise e