# DocuScan AI Backend

FastAPI server for DocuScan AI. It orchestrates the existing OCR pipeline and uses Anthropic's Claude AI for document classification and intelligent field extraction.

## Requirements

- Python 3.9+
- Tesseract OCR installed on the system (e.g., `apt install tesseract-ocr`)

## Setup & Running

1. Copy `.env.example` to `.env` and configure your API key:
   ```bash
   cp .env.example .env
   # Edit .env with your ANTHROPIC_API_KEY
   ```

2. Create a virtual environment inside `/backend`:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate
   ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Make sure your OCR pipeline is available at `../verify/pipeline.py` (relative to the backend folder).

5. Run the FastAPI server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

## Endpoints

* **POST /process**
  - Upload a `.jpg`, `.png`, `.tiff`, or `.pdf` document via `multipart/form-data` with the key `file`.
  - Returns a merged JSON combining OCR results and Claude's classification.

* **GET /health**
  - Check server and dependencies status.
