"""Document ingestion and recursive text chunking module."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class DocumentChunk:
    """Represents a discrete semantic chunk of text with metadata."""
    chunk_id: str
    text: str
    source_file: str
    section: str = "General"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source_file": self.source_file,
            "section": self.section,
            "metadata": self.metadata,
        }


class RecursiveTextSplitter:
    """Splits text recursively by paragraphs, sentences, and words to maintain semantic context."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = ["\n\n", "\n", ". ", "; ", ", ", " "]

    def split_text(self, text: str) -> List[str]:
        """Split text into chunks of maximum size while respecting boundary separators."""
        text = text.strip()
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        # Find best separator present in the text
        chosen_sep = " "
        for sep in self.separators:
            if sep in text:
                chosen_sep = sep
                break

        parts = text.split(chosen_sep)
        chunks = []
        current_chunk = []
        current_length = 0

        for part in parts:
            part_len = len(part) + len(chosen_sep)
            if current_length + part_len > self.chunk_size and current_chunk:
                merged = chosen_sep.join(current_chunk).strip()
                if merged:
                    chunks.append(merged)
                # Overlap handling: retain the last element(s) if within overlap budget
                overlap_size = 0
                overlap_items = []
                for item in reversed(current_chunk):
                    if overlap_size + len(item) <= self.chunk_overlap:
                        overlap_items.insert(0, item)
                        overlap_size += len(item) + len(chosen_sep)
                    else:
                        break
                current_chunk = list(overlap_items)
                current_length = sum(len(x) + len(chosen_sep) for x in current_chunk)

            current_chunk.append(part)
            current_length += part_len

        if current_chunk:
            merged = chosen_sep.join(current_chunk).strip()
            if merged:
                chunks.append(merged)

        return chunks


class DocumentIngestor:
    """Loads documents from disk and parses them into enriched semantic chunks."""

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 100):
        self.splitter = RecursiveTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)

    def load_file(self, file_path: Path) -> List[DocumentChunk]:
        """Load and chunk a single text or markdown file."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        filename = file_path.name

        # Parse markdown sections if present
        sections = self._extract_sections(content)
        chunks = []
        global_idx = 0

        for section_title, section_text in sections:
            split_pieces = self.splitter.split_text(section_text)
            for piece in split_pieces:
                if len(piece.strip()) < 30:
                    continue  # Ignore trivial headers or empty fragments
                chunk = DocumentChunk(
                    chunk_id=f"{filename}_{global_idx}",
                    text=piece.strip(),
                    source_file=filename,
                    section=section_title,
                    metadata={"char_count": len(piece), "chunk_index": global_idx},
                )
                chunks.append(chunk)
                global_idx += 1

        return chunks

    def load_directory(self, dir_path: Path) -> List[DocumentChunk]:
        """Load all markdown and text files from a directory."""
        if not dir_path.exists() or not dir_path.is_dir():
            raise NotADirectoryError(f"Directory not found: {dir_path}")

        all_chunks = []
        for file_path in sorted(dir_path.glob("*.*")):
            if file_path.suffix.lower() in [".md", ".txt", ".markdown"]:
                chunks = self.load_file(file_path)
                all_chunks.extend(chunks)

        return all_chunks

    def _extract_sections(self, content: str) -> List[tuple[str, str]]:
        """Split markdown content by heading tags into (section_title, section_body) pairs."""
        header_pattern = re.compile(r"^(#{1,3}\s+.+)$", re.MULTILINE)
        splits = header_pattern.split(content)

        if len(splits) == 1:
            return [("General", content)]

        sections = []
        # First part before first header
        if splits[0].strip():
            sections.append(("Introduction", splits[0].strip()))

        for i in range(1, len(splits), 2):
            header = splits[i].lstrip("#").strip()
            body = splits[i + 1].strip() if i + 1 < len(splits) else ""
            if body:
                sections.append((header, body))

        return sections
