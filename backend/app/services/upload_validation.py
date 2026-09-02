import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from pypdf import PdfReader
from pypdf.errors import PdfReadError

ALLOWED_UPLOADS = {
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
    ".pdf": ("application/pdf", b"%PDF-"),
}


class UploadValidationError(ValueError):
    """Raised when an uploaded schedule does not meet the safety policy."""


@dataclass(frozen=True, slots=True)
class ValidatedUpload:
    path: Path
    filename: str
    media_type: str
    sha256: str
    size: int
    page_count: int | None


async def validate_to_temporary_file(
    upload: UploadFile, max_bytes: int, pdf_max_pages: int
) -> ValidatedUpload:
    original_suffix = Path(upload.filename or "").suffix.lower()
    expected = ALLOWED_UPLOADS.get(original_suffix)
    if expected is None:
        await upload.close()
        raise UploadValidationError("UPLOAD_TYPE_NOT_ALLOWED")
    expected_media_type, magic = expected
    if upload.content_type != expected_media_type:
        await upload.close()
        raise UploadValidationError("UPLOAD_MEDIA_TYPE_MISMATCH")

    descriptor, raw_path = tempfile.mkstemp(
        prefix="shiftmate-import-", suffix=original_suffix
    )
    path = Path(raw_path)
    digest = hashlib.sha256()
    size = 0
    try:
        with os.fdopen(descriptor, "wb") as destination:
            while chunk := await upload.read(64 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise UploadValidationError("UPLOAD_TOO_LARGE")
                digest.update(chunk)
                destination.write(chunk)
        with path.open("rb") as source:
            if not source.read(len(magic)).startswith(magic):
                raise UploadValidationError("UPLOAD_MAGIC_MISMATCH")
        page_count = (
            _pdf_page_count(path, pdf_max_pages)
            if expected_media_type == "application/pdf"
            else None
        )
        return ValidatedUpload(
            path=path,
            filename=f"{uuid4().hex}{original_suffix}",
            media_type=expected_media_type,
            sha256=digest.hexdigest(),
            size=size,
            page_count=page_count,
        )
    except Exception:
        path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def cleanup_temporary_upload(upload: ValidatedUpload) -> None:
    upload.path.unlink(missing_ok=True)


def _pdf_page_count(path: Path, max_pages: int) -> int:
    try:
        reader = PdfReader(path, strict=True)
        page_count = len(reader.pages)
    except (PdfReadError, ValueError, OSError) as error:
        raise UploadValidationError("UPLOAD_PDF_INVALID") from error
    if page_count == 0 or page_count > max_pages:
        raise UploadValidationError("UPLOAD_PDF_PAGE_LIMIT")
    return page_count
