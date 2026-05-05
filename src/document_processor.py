"""Loads and parses markdown files from the knowledge base."""

import os
from pathlib import Path
from dataclasses import dataclass


@dataclass
class Document:
    path: str
    category: str  # "primary" or "secondary"
    name: str
    content: str


def load_knowledge_base(kb_root: str = None) -> list[Document]:
    if kb_root is None:
        kb_root = Path(__file__).parent.parent / "knowledge_base"
    else:
        kb_root = Path(kb_root)

    docs = []
    for category in ("primary", "secondary"):
        category_path = kb_root / category
        if not category_path.exists():
            continue
        for md_file in sorted(category_path.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            docs.append(Document(
                path=str(md_file),
                category=category,
                name=md_file.stem,
                content=content,
            ))
    return docs


def get_document(name: str, kb_root: str = None) -> Document | None:
    docs = load_knowledge_base(kb_root)
    return next((d for d in docs if d.name == name), None)


def build_context_block(docs: list[Document], max_chars: int = 8000) -> str:
    """Concatenates KB docs into a single context string for prompt injection."""
    sections = []
    total = 0
    for doc in docs:
        header = f"## [{doc.category.upper()}] {doc.name}\n"
        block = header + doc.content + "\n\n"
        if total + len(block) > max_chars:
            break
        sections.append(block)
        total += len(block)
    return "".join(sections)
