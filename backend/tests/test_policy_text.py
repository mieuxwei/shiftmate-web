from pathlib import Path

import pytest

from backend.app.services import policy_text
from backend.app.services.policy_text import (
    PolicyPage,
    PolicyTextError,
    chunk_policy_pages,
    clean_policy_text,
    extract_policy_pages,
)


def test_clean_and_chunk_preserve_page_metadata_and_overlap() -> None:
    text = "  第一條   規定\x00\n\n" + "輪班規則。" * 40
    cleaned = clean_policy_text(text)
    chunks = chunk_policy_pages(
        [PolicyPage(page_number=3, text=cleaned)],
        max_chars=100,
        overlap_chars=15,
    )

    assert cleaned.startswith("第一條 規定")
    assert len(chunks) > 1
    assert {chunk.page_number for chunk in chunks} == {3}
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.content for chunk in chunks)


def test_extract_rejects_pdf_without_text(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class BlankPage:
        def extract_text(self) -> str:
            return "  \n"

    class BlankReader:
        pages = [BlankPage()]

        def __init__(self, path: Path, strict: bool) -> None:
            assert path == tmp_path / "blank.pdf"
            assert strict is True

    monkeypatch.setattr(policy_text, "PdfReader", BlankReader)
    with pytest.raises(PolicyTextError, match="POLICY_TEXT_NOT_FOUND"):
        extract_policy_pages(tmp_path / "blank.pdf")


def test_extracts_text_from_a_real_pdf_with_page_number(tmp_path: Path) -> None:
    path = tmp_path / "policy.pdf"
    path.write_bytes(_single_page_pdf("Break policy: 30 minutes."))

    pages = extract_policy_pages(path)

    assert len(pages) == 1
    assert pages[0].page_number == 1
    assert "Break policy: 30 minutes." in pages[0].text


def _single_page_pdf(text: str) -> bytes:
    content = f"BT /F1 12 Tf 72 100 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ),
        (
            b"<< /Length "
            + str(len(content)).encode()
            + b" >>\nstream\n"
            + content
            + b"\nendstream"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    result = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, body in enumerate(objects, start=1):
        offsets.append(len(result))
        result.extend(f"{index} 0 obj\n".encode())
        result.extend(body)
        result.extend(b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    result.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode()
    )
    return bytes(result)
