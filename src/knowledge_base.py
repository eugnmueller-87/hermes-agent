"""Knowledge base manager — loads and queries KB documents."""

from .document_processor import load_knowledge_base, build_context_block, Document


class KnowledgeBase:
    def __init__(self, kb_root: str = None):
        self._docs = load_knowledge_base(kb_root)

    def all(self) -> list[Document]:
        return self._docs

    def primary(self) -> list[Document]:
        return [d for d in self._docs if d.category == "primary"]

    def secondary(self) -> list[Document]:
        return [d for d in self._docs if d.category == "secondary"]

    def get(self, name: str) -> Document | None:
        return next((d for d in self._docs if d.name == name), None)

    def context(self, categories: list[str] = None, max_chars: int = 8000) -> str:
        docs = self._docs
        if categories:
            docs = [d for d in docs if d.category in categories]
        return build_context_block(docs, max_chars=max_chars)

    def brand_voice_context(self) -> str:
        """Returns primary KB context optimised for LinkedIn post generation."""
        return self.context(categories=["primary"], max_chars=4000)

    def signals_context(self) -> str:
        """Returns secondary KB context with market signals."""
        return self.context(categories=["secondary"], max_chars=4000)

    def reload(self):
        self._docs = load_knowledge_base()
