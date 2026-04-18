import os
from typing import Any, Dict, List, Optional

CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chroma")

_chromadb = None
_embedding_functions = None


def _get_chromadb():
    global _chromadb, _embedding_functions
    if _chromadb is None:
        try:
            import chromadb
            from chromadb.utils import embedding_functions
            _chromadb = chromadb
            _embedding_functions = embedding_functions
        except ImportError as e:
            raise ImportError(
                "chromadb is required for EpisodicMemory. "
                "Install it with: uv add chromadb"
            ) from e
    return _chromadb, _embedding_functions


class EpisodicMemory:
    """Manages long-term episodic memory for research agents using ChromaDB."""

    def __init__(self, persist_directory: str = CHROMA_PATH):
        chromadb, embedding_functions = _get_chromadb()

        if not os.path.exists(persist_directory):
            os.makedirs(persist_directory, exist_ok=True)

        self.client = chromadb.PersistentClient(path=persist_directory)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        self.collection = self.client.get_or_create_collection(
            name="research_episodes",
            embedding_function=self.embedding_fn,
        )
        
    def add_episode(self, query: str, summary: str, report_id: str):
        """Store a research episode in memory."""
        self.collection.add(
            documents=[summary],
            metadatas=[{"query": query, "report_id": report_id}],
            ids=[report_id]
        )
        
    def search_memory(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Search past research episodes for relevant context."""
        results = self.collection.query(
            query_texts=[query],
            n_results=limit
        )
        
        episodes = []
        if results["documents"]:
            for i in range(len(results["documents"][0])):
                episodes.append({
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if "distances" in results else 0
                })
        return episodes
