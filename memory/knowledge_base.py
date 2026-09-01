from typing import Dict, List


class KnowledgeBase:
    """In-memory Vector/Document RAG Retriever for static docs and dynamic FAQs."""

    def __init__(self):
        self.documents: List[Dict[str, str]] = []

    def add_document(self, doc_id: str, text: str) -> None:
        self.documents.append({"id": doc_id, "text": text})

    def search(self, query: str, top_k: int = 2) -> List[str]:
        """Simple keyword TF-IDF match retriever for dynamic knowledge augmentation."""
        if not query or not self.documents:
            return []

        keywords = [k.lower() for k in query.split() if len(k) > 3]
        results = []
        for doc in self.documents:
            score = sum(1 for kw in keywords if kw in doc["text"].lower())
            if score > 0:
                results.append((score, doc["text"]))

        results.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in results[:top_k]]
