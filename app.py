from fastapi import FastAPI, File, UploadFile, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import time
import uuid
from datetime import datetime
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import json

from rag_engine import RAGEngine
from document_processor import DocumentProcessor

# rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="RAG Question Answering System", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# RAG engine
rag_engine = RAGEngine()
doc_processor = DocumentProcessor()

# In-memory job tracker
job_store = {}
metrics_store = []

# Pydantic
class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)
    
    @validator('question')
    def question_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be empty or whitespace')
        return v.strip()

class QueryResponse(BaseModel):
    answer: str
    source_chunks: List[dict]
    metrics: dict

class UploadResponse(BaseModel):
    job_id: str
    status: str
    message: str

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: Optional[str] = None
    error: Optional[str] = None

# Background document processing
async def process_document_background(job_id: str, file_path: str, filename: str):
    """Process document in background: chunk, embed, and store"""
    try:
        job_store[job_id]["status"] = "processing"
        job_store[job_id]["progress"] = "Loading document..."
        
        # Load and chunk document
        documents, ids = doc_processor.process_file(file_path, filename)
        
        job_store[job_id]["progress"] = f"Created {len(documents)} chunks, generating embeddings..."
        
        # Add to vector store
        rag_engine.add_documents(documents, ids)
        
        job_store[job_id]["status"] = "completed"
        job_store[job_id]["progress"] = f"Successfully processed {len(documents)} chunks"
        job_store[job_id]["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        job_store[job_id]["status"] = "failed"
        job_store[job_id]["error"] = str(e)
    finally:
        # Cleanup uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/upload", response_model=UploadResponse)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a document (PDF or TXT) for processing.
    Processing happens in background to avoid timeout.
    """
    # Validate file type
    allowed_extensions = {".txt", ".pdf"}
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type {file_ext} not supported. Use: {', '.join(allowed_extensions)}"
        )
    
    # Validate file size (max 10MB)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Max size: 10MB")
    
    # Save file temporarily
    job_id = str(uuid.uuid4())
    upload_dir = "./uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{job_id}_{file.filename}")
    with open(file_path, "wb") as f:
        f.write(content)
    
    # job tracking entry
    job_store[job_id] = {
        "job_id": job_id,
        "filename": file.filename,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
        "progress": "Queued for processing"
    }
    
    # background processing
    background_tasks.add_task(
        process_document_background,
        job_id,
        file_path,
        file.filename
    )
    
    return UploadResponse(
        job_id=job_id,
        status="queued",
        message=f"Document '{file.filename}' queued for processing. Check status at /job/{job_id}"
    )

@app.get("/job/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Check the status of a document processing job"""
    if job_id not in job_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = job_store[job_id]
    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job.get("progress"),
        error=job.get("error")
    )

@app.post("/query", response_model=QueryResponse)
@limiter.limit("5/minute")
async def query_documents(request: Request, query: QueryRequest):
    """
    Ask a question based on uploaded documents.
    Returns answer with source chunks and performance metrics.
    """
    start_time = time.time()
    
    try:
        # chunks retriev 
        retrieval_start = time.time()
        retrieved_docs = rag_engine.retrieve(query.question, k=5)
        retrieval_time = time.time() - retrieval_start
        
        if not retrieved_docs:
            raise HTTPException(
                status_code=404,
                detail="No relevant documents found. Please upload documents first."
            )
        
        # Generate ans
        generation_start = time.time()
        answer = rag_engine.generate_answer(query.question, retrieved_docs)
        generation_time = time.time() - generation_start
        
        # format similarity scores
        source_chunks = []
        for i, doc in enumerate(retrieved_docs, 1):
            similarity_score = getattr(doc, 'metadata', {}).get('score', 'N/A')
            
            source_chunks.append({
                "chunk_id": i,
                "content": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "similarity_score": similarity_score
            })
        
        # total latency
        total_latency = time.time() - start_time
        
        # Prepare metrics
        metrics = {
            "total_latency_ms": round(total_latency * 1000, 2),
            "retrieval_latency_ms": round(retrieval_time * 1000, 2),
            "generation_latency_ms": round(generation_time * 1000, 2),
            "s_retrieved": lchunken(retrieved_docs),
            "timestamp": datetime.now().isoformat()
        }
        
        # metrics storage
        metrics_store.append({
            "question": query.question,
            "metrics": metrics
        })
        
        return QueryResponse(
            answer=answer,
            source_chunks=source_chunks,
            metrics=metrics
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")

@app.get("/metrics")
async def get_metrics():
    """Get aggregated metrics for system performance"""
    if not metrics_store:
        return {"message": "No metrics available yet"}
    
    latencies = [m["metrics"]["total_latency_ms"] for m in metrics_store]
    
    return {
        "total_queries": len(metrics_store),
        "average_latency_ms": round(sum(latencies) / len(latencies), 2),
        "min_latency_ms": round(min(latencies), 2),
        "max_latency_ms": round(max(latencies), 2),
        "recent_queries": metrics_store[-10:]  # Last 10 queries
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "vector_store_initialized": rag_engine.is_initialized(),
        "timestamp": datetime.now().isoformat()
    }

@app.get("/")
async def root():
    """API documentation"""
    return {
        "message": "RAG Question Answering System",
        "version": "1.0.0",
        "endpoints": {
            "POST /upload": "Upload a document (PDF/TXT)",
            "GET /job/{job_id}": "Check document processing status",
            "POST /query": "Ask a question",
            "GET /metrics": "View system metrics",
            "GET /health": "Health check"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
