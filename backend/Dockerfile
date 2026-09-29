FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# requirements antes del codigo: la capa de pip se cachea
# mientras requirements.txt no cambie
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# sh -c para expandir $PORT (Railway lo inyecta en runtime; 8000 es el
# fallback local) y exec para que uvicorn reemplace al shell y reciba
# el SIGTERM de los redeploys directamente.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
