from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
import os

class RAGEngine:
    """
    Core RAG engine handling embeddings, vector storage, and answer generation.
    """
    
    def __init__(
        self,
        db_location="./chroma_db",
        collection_name="rag_documents",
        model_name="mistral:latest",
        embedding_model="all-minilm:l6-v2"
    ):
        self.db_location = db_location
        self.collection_name = collection_name
        self.model_name = model_name
        self.embedding_model = embedding_model
        
        # Initialize embeddings
        self.embeddings = OllamaEmbeddings(model=self.embedding_model)
        
        # Initialize vector store
        self.vector_store = Chroma(
            collection_name=self.collection_name,
            persist_directory=self.db_location,
            embedding_function=self.embeddings
        )
        
        # Initialize LLM
        self.llm = OllamaLLM(model=self.model_name)
        
        # Create prompt template
        self.prompt_template = """You are an expert assistant that answers questions based on provided document excerpts.

Use the following relevant excerpts to answer the question accurately and concisely.
If the answer cannot be found in the excerpts, say "I cannot find that information in the provided documents."

Relevant excerpts:
{context}

Question: {question}

Answer:"""
        
        self.prompt = ChatPromptTemplate.from_template(self.prompt_template)
        self.chain = self.prompt | self.llm
    
    def add_documents(self, documents: list, ids: list):
        """Add documents to the vector store"""
        self.vector_store.add_documents(documents=documents, ids=ids)
    
    def retrieve(self, query: str, k: int = 5):
        """
        Retrieve top-k most relevant document chunks for a query.
        Returns documents with similarity scores.
        """
        retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )
        
        # Get documents with scores
        docs_and_scores = self.vector_store.similarity_search_with_score(query, k=k)
        
        # Attach scores to document metadata
        retrieved_docs = []
        for doc, score in docs_and_scores:
            doc.metadata["score"] = round(float(score), 4)
            retrieved_docs.append(doc)
        
        return retrieved_docs
    
    def generate_answer(self, question: str, retrieved_docs: list) -> str:
        """Generate an answer using the LLM based on retrieved chunks"""
        # Format context from retrieved documents
        context = self._format_documents(retrieved_docs)
        
        # Generate answer
        result = self.chain.invoke({
            "context": context,
            "question": question
        })
        
        return result
    
    def _format_documents(self, docs):
        """Format retrieved documents for the prompt"""
        formatted = []
        for i, doc in enumerate(docs, 1):
            formatted.append(f"[Excerpt {i}]\n{doc.page_content}\n")
        return "\n".join(formatted)
    
    def is_initialized(self) -> bool:
        """Check if the vector store has any documents"""
        try:
            # Try to get collection count
            collection = self.vector_store._collection
            return collection.count() > 0
        except:
            return False
