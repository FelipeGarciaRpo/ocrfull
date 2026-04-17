# Veryfi-inspired Document Processing Pipeline
 
Pipeline de procesamiento de documentos financieros que convierte
imágenes de recibos/facturas en JSON estructurado.
 
Simula el flujo interno de Veryfi:
**Imagen → Preprocesamiento → OCR → Limpieza → Extracción → Validación → JSON**
 
---
 
## Arquitectura
 
```
veryfi-pipeline/
├── pipeline.py              ← orquestador principal
├── steps/
│   ├── preprocessor.py      ← STEP 1: limpieza de imagen (OpenCV)
│   ├── ocr.py               ← STEP 2: imagen → texto (Tesseract)
│   ├── cleaner.py           ← STEP 3: corrección de errores OCR
│   ├── extractor.py         ← STEP 4: regex + pandas → campos
│   ├── validator.py         ← STEP 5: reglas de negocio
│   └── formatter.py         ← STEP 6: JSON estandarizado
├── requirements.txt
└── README.md
```
 
---
 
## Setup
 
### 1. Instalar Tesseract (OCR engine)
 
**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-spa  # soporte español (opcional)
```
 
**macOS:**
```bash
brew install tesseract
brew install tesseract-lang  # todos los idiomas
```
 
**Windows:**
Descargar instalador: https://github.com/UB-Mannheim/tesseract/wiki
 
### 2. Instalar dependencias Python
 
```bash
python -m venv venv
source venv/bin/activate      # Linux/Mac
# venv\Scripts\activate       # Windows
 
pip install -r requirements.txt
```
 
---
 
## Uso
 
```bash
# Procesar una imagen
python pipeline.py --image receipt.jpg
 
# Con modo debug (guarda archivos intermedios)
python pipeline.py --image receipt.jpg --debug
 
# Guardar resultado en archivo
python pipeline.py --image receipt.jpg --output resultado.json
 
# Todo junto
python pipeline.py --image receipt.jpg --debug --output resultado.json
```
 
---
 
## Output de ejemplo
 
```json
{
  "id": "A3F9C2B1E8D4",
  "created_date": "2024-04-15 10:23:45",
  "source_file": "walgreens_receipt.jpg",
  "document_type": "receipt",
  "document_reference_number": "4782",
  "vendor": {
    "name": "Walgreens",
    "address": "#03298 191 E 3RD AVE SAN MATEO CA 94401",
    "phone": "650-342-2725",
    "logo": null
  },
  "date": "2023-03-28",
  "currency_code": "USD",
  "subtotal": 27.80,
  "tax": 1.33,
  "discount": 1.20,
  "total": 29.13,
  "payment_method": "VISA",
  "line_items": [
    {
      "id": 1,
      "description": "RED BULL ENRGY DRNK CNS 8.4OZ 6PK",
      "quantity": 1,
      "unit_price": 8.79,
      "total": 8.79
    },
    {
      "id": 2,
      "description": "COCA COLA MINICAN 7.5Z 6PK",
      "quantity": 1,
      "unit_price": 4.99,
      "total": 4.99
    }
  ],
  "_quality": {
    "ocr_confidence": 0.8923,
    "validation_score": 84,
    "is_valid": true,
    "errors": [],
    "warnings": ["LINE_ITEMS_SUM_MISMATCH: Suma de items difiere del total en 12%"],
    "ready_for_training": true
  }
}
```
 
---
 
## Tecnologías
 
| Librería | Para qué |
|---|---|
| `opencv-python` | Preprocesamiento de imagen (binarización, orientación) |
| `pytesseract` | OCR — imagen a texto |
| `Pillow` | Manipulación básica de imágenes |
| `re` (built-in) | Extracción de campos con regex |
| `pandas` | Limpieza y procesamiento de line items |
| `numpy` | Detección de outliers en montos |
 
---
 
## Limitaciones vs Veryfi real
 
| Capacidad | Este pipeline | Veryfi |
|---|---|---|
| OCR engine | Tesseract (open source) | Motor propietario |
| Modelos ML | Solo regex | LayoutLM, modelos custom |
| Idiomas | Inglés/Español básico | 30+ idiomas |
| Formatos | JPG, PNG | JPG, PNG, PDF, TIFF |
| Precisión en campos | ~70-85% | ~95%+ |
| Velocidad | ~3-5s por doc | <1s por doc |
 
---
 
## Autor
 
Proyecto de práctica para entender el stack de procesamiento
de documentos de Veryfi — construido como preparación de entrevista.