from io import BytesIO
from pathlib import Path

import pytest
from pypdf import PdfWriter
from starlette.datastructures import Headers, UploadFile

from backend.app.services.upload_validation import (
    UploadValidationError,
    cleanup_temporary_upload,
    validate_to_temporary_file,
)


def uploaded(filename: str, media_type: str, content: bytes) -> UploadFile:
    return UploadFile(
        BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": media_type}),
    )


@pytest.mark.anyio
async def test_valid_png_is_renamed_hashed_and_cleaned() -> None:
    source = uploaded("synthetic.png", "image/png", b"\x89PNG\r\n\x1a\nfixture")

    result = await validate_to_temporary_file(source, max_bytes=100, pdf_max_pages=40)

    assert result.filename != "synthetic.png"
    assert result.filename.endswith(".png")
    assert result.media_type == "image/png"
    assert len(result.sha256) == 64
    assert result.path.exists()
    cleanup_temporary_upload(result)
    assert not result.path.exists()


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("filename", "media_type", "content", "code"),
    [
        ("schedule.zip", "application/zip", b"PK", "UPLOAD_TYPE_NOT_ALLOWED"),
        (
            "schedule.png",
            "image/jpeg",
            b"\x89PNG\r\n\x1a\n",
            "UPLOAD_MEDIA_TYPE_MISMATCH",
        ),
        ("schedule.png", "image/png", b"not-a-png", "UPLOAD_MAGIC_MISMATCH"),
        ("schedule.jpg", "image/jpeg", b"\xff\xd8\xfftoo-large", "UPLOAD_TOO_LARGE"),
    ],
)
async def test_invalid_upload_is_rejected_and_temp_file_removed(
    filename: str, media_type: str, content: bytes, code: str
) -> None:
    before = set(Path("/tmp").glob("shiftmate-import-*"))
    with pytest.raises(UploadValidationError, match=code):
        await validate_to_temporary_file(
            uploaded(filename, media_type, content),
            max_bytes=8 if code == "UPLOAD_TOO_LARGE" else 100,
            pdf_max_pages=40,
        )
    assert set(Path("/tmp").glob("shiftmate-import-*")) == before


@pytest.mark.anyio
async def test_pdf_page_limit_is_enforced(tmp_path: Path) -> None:
    pdf_path = tmp_path / "synthetic.pdf"
    writer = PdfWriter()
    for _ in range(41):
        writer.add_blank_page(width=100, height=100)
    with pdf_path.open("wb") as destination:
        writer.write(destination)

    with pytest.raises(UploadValidationError, match="UPLOAD_PDF_PAGE_LIMIT"):
        await validate_to_temporary_file(
            uploaded("synthetic.pdf", "application/pdf", pdf_path.read_bytes()),
            max_bytes=5 * 1024 * 1024,
            pdf_max_pages=40,
        )


@pytest.mark.anyio
async def test_malformed_pdf_is_rejected() -> None:
    with pytest.raises(UploadValidationError, match="UPLOAD_PDF_INVALID"):
        await validate_to_temporary_file(
            uploaded("synthetic.pdf", "application/pdf", b"%PDF-not-valid"),
            max_bytes=5 * 1024 * 1024,
            pdf_max_pages=40,
        )
