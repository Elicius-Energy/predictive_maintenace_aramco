"""
Document embedding using sentence-transformers and FAISS.
Supports TXT and PDF formats with automatic modification detection.
"""
import os
import logging
import pickle
from typing import List, Optional
import faiss
from sentence_transformers import SentenceTransformer
from pathlib import Path
import pypdf

from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingManager:
    """Handles text chunking, embedding, and FAISS indexing with Smart Rebuild."""
    
    def __init__(self):
        self.model = None
        self.index = None
        self.documents = []
        self.index_path = settings.FAISS_INDEX_PATH
        self.knowledge_dir = settings.KNOWLEDGE_BASE_DIR
        self._model_load_failed = False

    def _ensure_model(self) -> bool:
        """Load embedding model lazily so the backend can still boot offline."""
        if self.model is not None:
          return True
        if self._model_load_failed:
          return False

        try:
            self.model = SentenceTransformer('all-MiniLM-L6-v2', local_files_only=True)
            return True
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self._model_load_failed = True
            self.model = None
            return False
        
    def initialize(self):
        """Load knowledge base, embed, and build index with modification check."""
        if not self._ensure_model():
            logger.warning("Embedding model unavailable. RAG index initialization skipped.")
            self.index = None
            self.documents = []
            return

        index_file = self.index_path + ".index"
        docs_file = self.index_path + ".docs"
        
        rebuild_required = False
        
        # 1. Check if index files exist at all
        if not os.path.exists(index_file) or not os.path.exists(docs_file):
            rebuild_required = True
        else:
            # 2. Smart Rebuild: Check if any knowledge file is newer than the index
            index_mtime = os.path.getmtime(index_file)
            kb_path = Path(self.knowledge_dir)
            
            if kb_path.exists():
                # Check both .txt and .pdf
                for ext in ["*.txt", "*.pdf"]:
                    for file_path in kb_path.glob(ext):
                        if file_path.stat().st_mtime > index_mtime:
                            logger.info(f"Newer file detected: {file_path.name}. Rebuilding index...")
                            rebuild_required = True
                            break
                    if rebuild_required:
                        break
        
        if not rebuild_required:
            self.load_index()
            return

        logger.info("Initializing/Rebuilding FAISS index from knowledge base...")
        self._build_index()
        self.save_index()

    def _build_index(self):
        """Read text and PDF files, chunk them, and create FAISS index."""
        if not self._ensure_model():
            self.index = None
            self.documents = ["Knowledge base unavailable because the embedding model could not be loaded."]
            return

        kb_path = Path(self.knowledge_dir)
        if not kb_path.exists():
            kb_path.mkdir(parents=True, exist_ok=True)
            (kb_path / "init.txt").write_text("Predictive maintenance introduction.")

        all_text = []
        
        # Support both TXT and PDF
        for ext in ["*.txt", "*.pdf"]:
            for file_path in kb_path.glob(ext):
                try:
                    content = ""
                    if file_path.suffix.lower() == ".pdf":
                        content = self._extract_text_from_pdf(file_path)
                    else:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                    
                    if content.strip():
                        chunks = self._chunk_text(content)
                        all_text.extend(chunks)
                        logger.info(f"Processed {file_path.name}: {len(chunks)} chunks.")
                except Exception as e:
                    logger.error(f"Error reading {file_path}: {e}")

        if not all_text:
            all_text = ["Generic predictive maintenance knowledge."]

        self.documents = all_text
        embeddings = self.model.encode(all_text)
        
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(embeddings.astype('float32'))
        logger.info(f"Indexed total {len(all_text)} document chunks.")

    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """Extract text from all pages of a PDF file."""
        text = []
        try:
            reader = pypdf.PdfReader(str(file_path))
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        except Exception as e:
            logger.error(f"Failed to extract PDF text from {file_path}: {e}")
        return "\n".join(text)

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Simple sliding window chunking."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
            if i + chunk_size >= len(words):
                break
        return chunks

    def save_index(self):
        """Persist index and document mapping to disk."""
        if self.index:
            try:
                os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
                faiss.write_index(self.index, self.index_path + ".index")
                with open(self.index_path + ".docs", 'wb') as f:
                    pickle.dump(self.documents, f)
                logger.info("FAISS index saved successfully.")
            except Exception as e:
                logger.error(f"Failed to save FAISS index: {e}")

    def load_index(self):
        """Load index from disk."""
        try:
            self.index = faiss.read_index(self.index_path + ".index")
            with open(self.index_path + ".docs", 'rb') as f:
                self.documents = pickle.load(f)
            logger.info(f"Loaded existing FAISS index with {len(self.documents)} docs.")
        except Exception as e:
            logger.warning(f"Failed to load index, will build new one: {e}")
            self._build_index()

# Singleton
embedding_manager = EmbeddingManager()
