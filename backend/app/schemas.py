from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime


class QueryRequest(BaseModel):
    question: str
    return_sources: bool = True


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