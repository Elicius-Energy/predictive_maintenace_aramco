"""
Retriever for RAG system.
"""
import logging
from typing import List, Tuple
import numpy as np
from app.rag.embeddings import embedding_manager

logger = logging.getLogger(__name__)

class Retriever:
    """Retrieves relevant document chunks from FAISS index."""
    
    def retrieve(self, query: str, k: int = 3) -> List[str]:
        """Search index for top-k matches."""
        if not embedding_manager.index:
            embedding_manager.initialize()
            
        if not embedding_manager.index:
            return ["No knowledge base available."]

        query_vector = embedding_manager.model.encode([query]).astype('float32')
        distances, indices = embedding_manager.index.search(query_vector, k)
        
        results = []
        for idx in indices[0]:
            if idx != -1 and idx < len(embedding_manager.documents):
                results.append(embedding_manager.documents[idx])
                
        return results

# Singleton
retriever = Retriever()
