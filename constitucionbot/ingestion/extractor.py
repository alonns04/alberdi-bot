from __future__ import annotations

import io
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import fitz
except ImportError:  # pragma: no cover - depends on environment
    fitz = None

try:
    import pytesseract
except ImportError:  # pragma: no cover - depends on environment
    pytesseract = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover - depends on environment
    Image = None

from config import OCR_TESSERACT_CMD, ROOT_DIR
from ingestion.chunker import chunk_text, join_pages_with_markers, normalize_text


def _normalize_catalog_text(text: str) -> str:
    normalized = text.lower()
    for src, dst in (("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u")):
        normalized = normalized.replace(src, dst)
    return normalized


def infer_norm_category(path: Path) -> str:
    blob = _normalize_catalog_text(f"{path.stem} {path.name}")
    compact = re.sub(r"[^a-z0-9]+", "", blob)

    if "constituc" in blob:
        if any(token in blob for token in ("manual", "bidart", "doctrina", "campos", "comentad")):
            return "manual_constitucion"
        if "lectura facil" in blob or "lecturafacil" in compact:
            return "constitucion_didactica"
        if "linea tiempo" in blob or "lineatiempo" in compact or "como es nuestra" in blob:
            return "constitucion_auxiliar"
        if "constitucionnacional" in compact or "constitucion nacional" in blob:
            return "constitucion_nacional"
        return "constitucion_relacionada"

    if "codigo" in blob and "penal" in blob:
        return "codigo_penal"
    if "procesal penal" in blob:
        return "codigo_procesal_penal"
    if "derecho penal" in blob:
        return "manual_penal"
    return "general"


def _base_document_metadata(path: Path, document_type: str) -> Dict[str, Any]:
    return {
        "source": str(path.relative_to(ROOT_DIR)).replace("\\", "/"),
        "document_name": path.name,
        "document_type": document_type,
        "norm_category": infer_norm_category(path),
        "book": path.stem,
        "title": path.stem,
        "chapter": None,
        "section": None,
        "article": None,
        "inciso": None,
        "page": None,
    }


def extract_text_from_txt(path: Path) -> List[Dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    document_metadata = _base_document_metadata(path, "txt")
    chunks = chunk_text(text, metadata=document_metadata)
    return [{**chunk, "type": "txt"} for chunk in chunks]


def _extract_pdf_pages(path: Path) -> Tuple[List[Tuple[int, str]], str | None]:
    if fitz is None:
        return [], "No se pudo leer el PDF porque no está instalada la dependencia pymupdf."

    if pytesseract is not None:
        pytesseract.pytesseract.tesseract_cmd = OCR_TESSERACT_CMD

    pages: List[Tuple[int, str]] = []
    doc = fitz.open(path)
    for page_number, page in enumerate(doc, start=1):
        text = page.get_text().strip()
        if not text and pytesseract is not None and Image is not None:
            pix = page.get_pixmap(dpi=300)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(image, lang="spa").strip()
        pages.append((page_number, text))
    return pages, None


def extract_text_from_pdf(path: Path) -> List[Dict[str, Any]]:
    document_metadata = _base_document_metadata(path, "pdf")

    try:
        pages, error = _extract_pdf_pages(path)
        if error:
            return [
                {
                    "source": document_metadata["source"],
                    "content": error,
                    "type": "pdf_error",
                }
            ]

        if not any(page_text.strip() for _, page_text in pages):
            return []

        marked_text = join_pages_with_markers(pages)
        marked_text = normalize_text(marked_text)
        chunks = chunk_text(marked_text, metadata=document_metadata)
        return [{**chunk, "type": "pdf_text"} for chunk in chunks]
    except Exception as exc:
        return [
            {
                "source": document_metadata["source"],
                "content": f"Error al leer PDF con fitz/pytesseract: {exc}",
                "type": "pdf_error",
            }
        ]


def extract_documents(path: Path) -> List[Dict[str, Any]]:
    if path.suffix.lower() == ".txt":
        return extract_text_from_txt(path)
    if path.suffix.lower() == ".pdf":
        return extract_text_from_pdf(path)
    return []
