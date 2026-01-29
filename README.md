# RAG-Based Question Answering System

A production-ready Retrieval-Augmented Generation (RAG) system built with FastAPI, LangChain, and Ollama for document-based question answering.

## 🎯 Features

- **Multi-format Document Support**: Upload and process PDF and TXT files
- **Background Processing**: Asynchronous document ingestion to prevent API timeouts
- **Vector Storage**: ChromaDB for efficient similarity search
- **Rate Limiting**: Built-in protection against API abuse
- **Request Validation**: Pydantic schemas for robust input validation
- **Performance Metrics**: Track latency, similarity scores, and system health
- **RESTful API**: Clean, well-documented endpoints

## 🏗️ Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────────┐
│           FastAPI Server                │
│  ┌─────────────────────────────────┐   │
│  │  Rate Limiter (slowapi)         │   │
│  │  Request Validation (Pydantic)  │   │
│  └─────────────────────────────────┘   │
│                                         │
│  Endpoints:                             │
│  • POST /upload → Background Jobs       │
│  • POST /query  → RAG Pipeline         │
│  • GET  /job/{id} → Status Check       │
│  • GET  /metrics → Performance Data    │
└──────────┬──────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│      Document Processor                  │
│  • PDF Parser (PyPDF2)                   │
│  • TXT Parser                            │
│  • Chunking Strategy (500 words, 50 overlap) │
└──────────┬───────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────┐
│         RAG Engine                       │
│  ┌────────────────────────────────────┐ │
│  │  Embeddings (Ollama MiniLM)        │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │  Vector Store (ChromaDB)           │ │
│  │  • Similarity Search               │ │
│  │  • Score Calculation               │ │
│  └────────────────────────────────────┘ │
│  ┌────────────────────────────────────┐ │
│  │  LLM (Ollama Mistral)             │ │
│  │  • Answer Generation               │ │
│  └────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

## 📋 Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai/) installed and running
- Required Ollama models:
  ```bash
  ollama pull mistral:latest
  ollama pull all-minilm:l6-v2
  ```

## 🚀 Setup

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd rag-qa-system
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Ollama is Running

```bash
# Check if Ollama is accessible
curl http://localhost:11434/api/tags
```

### 5. Start the Server

```bash
python app.py
```

The API will be available at `http://localhost:8000`

## 📖 API Usage

### 1. Upload a Document

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@path/to/your/document.pdf"
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "queued",
  "message": "Document 'document.pdf' queued for processing. Check status at /job/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

### 2. Check Processing Status

```bash
curl "http://localhost:8000/job/a1b2c3d4-e5f6-7890-abcd-ef1234567890"
```

**Response:**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "progress": "Successfully processed 12 chunks"
}
```

### 3. Ask a Question

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the main topic of the document?"}'
```

**Response:**
```json
{
  "answer": "The document discusses...",
  "source_chunks": [
    {
      "chunk_id": 1,
      "content": "Excerpt from the document...",
      "source": "document.pdf",
      "similarity_score": 0.8542
    }
  ],
  "metrics": {
    "total_latency_ms": 1247.32,
    "retrieval_latency_ms": 45.21,
    "generation_latency_ms": 1202.11,
    "chunks_retrieved": 5,
    "timestamp": "2024-01-29T10:30:45.123456"
  }
}
```

### 4. View System Metrics

```bash
curl "http://localhost:8000/metrics"
```

### 5. Health Check

```bash
curl "http://localhost:8000/health"
```

## 🧪 Testing with Python

```python
import requests

# Upload document
with open("document.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/upload",
        files={"file": f}
    )
    job_id = response.json()["job_id"]

# Wait for processing
import time
while True:
    status = requests.get(f"http://localhost:8000/job/{job_id}").json()
    if status["status"] == "completed":
        break
    time.sleep(1)

# Ask question
response = requests.post(
    "http://localhost:8000/query",
    json={"question": "What is the main topic?"}
)
print(response.json()["answer"])
```

## ⚙️ Configuration

### Chunking Strategy

**Chunk Size: 500 words**
- **Why?** Balances context preservation with retrieval precision
- Too small (100-200): Loses semantic context, may miss relevant info
- Too large (1000+): Reduces retrieval accuracy, dilutes relevance scores

**Overlap: 50 words**
- **Why?** Prevents concept splitting at chunk boundaries
- Ensures continuity in retrieved context
- 10% overlap is optimal based on testing

### Rate Limits

- **Upload**: 10 requests/minute per IP
- **Query**: 5 requests/minute per IP

Modify in `app.py`:
```python
@limiter.limit("10/minute")  # Adjust as needed
```

## 📊 Metrics Tracked

1. **Latency Metrics**
   - Total query latency
   - Retrieval time
   - Generation time

2. **Retrieval Quality**
   - Similarity scores for each chunk
   - Number of chunks retrieved

3. **System Health**
   - Document count
   - Query success rate

## 🔍 Retrieval Failure Cases

### Observed Failure Case: Semantic Gap

**Scenario**: User asks "What are the financial implications?"

**Problem**: 
- Document uses terms like "cost impact", "budget effects", "economic consequences"
- Query uses "financial implications"
- Embedding model doesn't bridge the semantic gap

**Evidence**:
- Similarity scores < 0.5 (threshold for relevance)
- Retrieved chunks don't contain answer

**Solution**:
- Use query expansion (add synonyms)
- Consider hybrid search (keyword + semantic)
- Fine-tune embedding model on domain-specific data

## 🛡️ Security Considerations

- File size limit: 10MB (prevent DoS)
- Allowed file types: PDF, TXT only
- Rate limiting enabled
- Input validation via Pydantic
- Uploaded files cleaned after processing

## 🐛 Troubleshooting

### Ollama Connection Error
```bash
# Ensure Ollama is running
ollama serve

# Verify models are available
ollama list
```

### ChromaDB Errors
```bash
# Clear vector store and restart
rm -rf ./chroma_db
python app.py
```

### Rate Limit Issues
Increase limits in `app.py` or wait 60 seconds between requests.

## 📁 Project Structure

```
.
├── app.py                 # FastAPI application
├── rag_engine.py         # RAG core logic
├── document_processor.py # Document parsing & chunking
├── requirements.txt      # Python dependencies
├── README.md            # This file
└── explanations.md      # Detailed technical explanations
```

## 🎓 Design Decisions

See `explanations.md` for detailed rationale on:
- Chunking strategy
- Retrieval failure analysis
- Metrics selection
- Technology choices

## 📝 License

MIT

## 🤝 Contributing

PRs welcome! Please ensure all endpoints have proper validation and error handling.
