# RAG-Based-Question-Answering-System
An applied AI system using embeddings, retrieval, background jobs, and APIs.
Problem Statement:
Create an API that allows users to upload documents and ask questions based on those documents using a Retrieval-Augmented Generation (RAG) approach.
Functional Requirements
Your system should:
1.	Accept documents (minimum two formats, e.g., PDF and TXT)
2.	Chunk and embed documents
3.	Store embeddings in a local vector store or cloud based vector store (e.g., FAISS/ PINECONE)
4.	Retrieve relevant chunks based on user queries
5.	Generate answers using an LLM
Technical Requirements
●	FastAPI or Flask
●	Embedding generation
●	Similarity search
●	Background job for document ingestion
●	Request validation (Pydantic)
●	Basic rate limiting

