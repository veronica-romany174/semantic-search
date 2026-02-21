"""
app/chunker/text_chunker.py

Sliding-window character-level text chunker.

Single responsibility: take a dict of {page_num: text} and produce a flat
list of TextChunk objects. Each chunk carries page-level metadata so the
final search results can tell users exactly where in a document a passage
came from.
"""

from __future__ import annotations

from typing import Dict, List

from app.core.config import settings
from app.core.logger import get_logger
from app.vector_store.base import TextChunk

logger = get_logger(__name__)


class TextChunker:
    """
    Splits page text into overlapping fixed-size character windows.

    Chunking strategy — sliding window:

        [  chunk_0  ]
               [ chunk_1  ]          ← overlaps with chunk_0 by `overlap` chars
                      [ chunk_2  ]

    Step size = chunk_size - chunk_overlap
    This ensures no information is lost at chunk boundaries and that
    semantic context carries over between adjacent chunks.
    """

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        """
        Args:
            chunk_size    : Maximum characters per chunk.
                            Defaults to ``settings.chunk_size``.
            chunk_overlap : Characters shared between consecutive chunks.
                            Defaults to ``settings.chunk_overlap``.
        """
        self.chunk_size: int = chunk_size or settings.chunk_size
        self.chunk_overlap: int = chunk_overlap or settings.chunk_overlap

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) must be less than "
                f"chunk_size ({self.chunk_size})."
            )

    # ── Public API ─────────────────────────────────────────────────────────────

    def chunk(self, pages: Dict[int, str], source_file: str) -> List[TextChunk]:
        """
        Split all pages into overlapping TextChunk objects.

        Args:
            pages       : ``{page_number: text}`` produced by PDFReader.
            source_file : Original filename stored in each chunk's metadata.

        Returns:
            Flat list of TextChunk objects ordered page-by-page.
            Each chunk has an empty ``embedding`` field — the Embedder
            is responsible for populating that before upsert.
        """
        if not pages:
            return []

        chunks: List[TextChunk] = []
        global_index = 0              # unique chunk counter across the whole doc
        step = self.chunk_size - self.chunk_overlap

        for page_num in sorted(pages.keys()):
            text = pages[page_num].strip()
            if not text:
                continue

            page_chunks = self._split_text(text)

            for fragment in page_chunks:
                chunks.append(
                    TextChunk(
                        text=fragment,
                        source_file=source_file,
                        page_number=page_num,
                        chunk_index=global_index,
                    )
                )
                global_index += 1

        logger.debug(
            "'%s' — produced %d chunk(s) from %d page(s).",
            source_file,
            len(chunks),
            len(pages),
        )
        return chunks

    # ── Internals ──────────────────────────────────────────────────────────────

    def _split_text(self, text: str) -> List[str]:
        """
        Apply the sliding window to a single block of text.

        Returns at least one chunk even if ``text`` is shorter than
        ``chunk_size``.
        """
        step = self.chunk_size - self.chunk_overlap
        fragments: List[str] = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            fragment = text[start:end].strip()
            if fragment:
                fragments.append(fragment)
            start += step

        return fragments
