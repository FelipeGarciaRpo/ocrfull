from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Vendor(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None

class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total: Optional[float] = None

class ProcessResponse(BaseModel):
    document_type: str
    confidence: float
    ocr_confidence: float
    vendor: Optional[Vendor] = None
    date: Optional[str] = None
    total: Optional[float] = None
    currency_code: Optional[str] = None
    document_number: Optional[str] = None
    payment_method: Optional[str] = None
    line_items: List[LineItem] = []
    summary: Optional[str] = None
    raw_json: Dict[str, Any] = {}
    processing_time_ms: int
    ready_for_training: bool

class HealthResponse(BaseModel):
    status: str
    tesseract_version: str
    pipeline: str

class ErrorResponse(BaseModel):
    error: str
    code: str
    processing_time_ms: int
