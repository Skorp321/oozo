from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class QueryRequest(BaseModel):
    question: str
    return_sources: bool = True


class FeedbackRequest(BaseModel):
    """Запрос на сохранение оценки ответа (like/dislike)."""
    query_log_id: int
    feedback: str  # "like" | "dislike"


class FeedbackResponse(BaseModel):
    """Ответ после сохранения оценки."""
    ok: bool
    message: str


class Source(BaseModel):
    title: str
    content: str
    score: float
    metadata: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: Optional[List[Source]] = None


class HealthResponse(BaseModel):
    status: str
    message: str


class StatsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    index_size_mb: float
    last_updated: Optional[str] = None


class InfoResponse(BaseModel):
    name: str
    version: str
    description: str
    embedding_model: str
    llm_model: str


class SimilarityRequest(BaseModel):
    query: str
    top_k: int = 5


class SimilarityResponse(BaseModel):
    query: str
    results: List[Source]


class IngestResponse(BaseModel):
    message: str
    documents_processed: int
    chunks_created: int
    index_size_mb: float


class LogEntry(BaseModel):
    timestamp: str
    request: Dict[str, Any]
    response: Dict[str, Any]
    processing_time_seconds: Optional[float] = None
    error: Optional[str] = None
    status: str
    type: Optional[str] = None


class LogsResponse(BaseModel):
    logs: List[LogEntry]
    total_count: int 


# -------------------- Async task support --------------------

class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class TaskCreateResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: datetime


class TaskStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    created_at: datetime
    completed_at: Optional[datetime] = None
    result: Optional[QueryResponse] = None
    error: Optional[str] = None


class AdminHrRow(BaseModel):
    id: int
    data: int
    date: datetime
    operation: str
    content: str
    status: str
    hour: int
    question: str
    answer: Optional[str] = None


class AdminHrHourlyStat(BaseModel):
    hour: int
    count: int


class AdminHrDailyStat(BaseModel):
    day: str
    count: int


class AdminHrReportResponse(BaseModel):
    total_records: int
    like_count: int
    dislike_count: int
    context_found: int
    dao: int
    mao: int
    rows: List[AdminHrRow]
    hourly_stats: List[AdminHrHourlyStat]
    daily_stats: List[AdminHrDailyStat]
