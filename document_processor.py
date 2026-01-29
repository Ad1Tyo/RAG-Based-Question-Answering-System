from langchain_core.documents import Document
import PyPDF2
import os

class DocumentProcessor:
    """
    Handles document loading, parsing, and chunking for different file types.
    """
    
    def __init__(self, chunk_size=500, overlap=50):
        """
        Initialize document processor.
        
        Args:
            chunk_size: Number of words per chunk (500 chosen for balance)
            overlap: Word overlap between chunks (maintains context)
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def process_file(self, file_path: str, filename: str):
        """
        Process a file based on its extension.
        Returns (documents, ids) tuple.
        """
        file_ext = os.path.splitext(filename)[1].lower()
        
        if file_ext == ".txt":
            content = self._load_txt(file_path)
        elif file_ext == ".pdf":
            content = self._load_pdf(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        # Chunk the content
        chunks = self._chunk_text(content)
        
        # Create Document objects
        documents = []
        ids = []
        
        for i, chunk in enumerate(chunks, start=1):
            doc_id = f"{filename}_{i}"
            document = Document(
                page_content=chunk,
                metadata={
                    "chunk_id": i,
                    "source": filename,
                    "total_chunks": len(chunks)
                },
                id=doc_id
            )
            documents.append(document)
            ids.append(doc_id)
        
        return documents, ids
    
    def _load_txt(self, file_path: str) -> str:
        """Load text from a .txt file"""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def _load_pdf(self, file_path: str) -> str:
        """Load text from a PDF file"""
        text = ""
        
        with open(file_path, "rb") as f:
            pdf_reader = PyPDF2.PdfReader(f)
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
        
        return text
    
    def _chunk_text(self, text: str):
        """
        Split text into overlapping chunks.
        
        Chunk size strategy:
        - 500 words chosen as optimal balance between:
          * Context preservation (enough info for coherent answers)
          * Retrieval precision (not too broad)
          * Embedding quality (within model limits)
        
        - 50-word overlap ensures:
          * Continuity across chunk boundaries
          * Reduced risk of splitting related concepts
        """
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), self.chunk_size - self.overlap):
            chunk = ' '.join(words[i:i + self.chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks
