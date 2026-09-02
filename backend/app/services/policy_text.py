import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PolicyTextError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class PolicyPage:
    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class TextChunk:
    page_number: int
    chunk_index: int
    content: str


def extract_policy_pages(path: Path) -> list[PolicyPage]:
    try:
        reader = PdfReader(path, strict=True)
        pages = [
            PolicyPage(index, clean_policy_text(page.extract_text() or ""))
            for index, page in enumerate(reader.pages, start=1)
        ]
    except (PdfReadError, KeyError, TypeError, ValueError, OSError) as error:
        raise PolicyTextError("POLICY_PDF_EXTRACTION_FAILED") from error
    if not any(page.text for page in pages):
        raise PolicyTextError("POLICY_TEXT_NOT_FOUND")
    return pages


def clean_policy_text(value: str) -> str:
    lines = []
    for raw_line in value.replace("\x00", " ").splitlines():
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def chunk_policy_pages(
    pages: list[PolicyPage], max_chars: int = 1200, overlap_chars: int = 180
) -> list[TextChunk]:
    if max_chars < 100 or overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("Invalid chunk sizing")
    chunks: list[TextChunk] = []
    chunk_index = 0
    for page in pages:
        start = 0
        while start < len(page.text):
            hard_end = min(start + max_chars, len(page.text))
            end = hard_end
            if hard_end < len(page.text):
                split = max(
                    page.text.rfind("\n", start, hard_end),
                    page.text.rfind("。", start, hard_end),
                    page.text.rfind(". ", start, hard_end),
                )
                if split > start + max_chars // 2:
                    end = split + 1
            content = page.text[start:end].strip()
            if content:
                chunks.append(TextChunk(page.page_number, chunk_index, content))
                chunk_index += 1
            if end >= len(page.text):
                break
            start = max(end - overlap_chars, start + 1)
    if not chunks:
        raise PolicyTextError("POLICY_TEXT_NOT_FOUND")
    return chunks
