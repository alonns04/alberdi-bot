from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Tuple

from config import CHUNK_SIZE

PAGE_MARKER_RE = re.compile(r"\x00PAGE:(\d+)\x00")

LEGAL_HEADING_RE = re.compile(
    r"^(?:libro|cap[íi]tulo|t[íi]tulo|secci[óo]n|art[íi]culo|art\.?|inciso|par[áa]grafo|numeral)\b",
    re.IGNORECASE,
)

LIBRO_RE = re.compile(r"^\s*libro\s+([IVXLCDM\d]+(?:\s*[-–—].*)?)", re.IGNORECASE)
TITULO_RE = re.compile(r"^\s*t[íi]tulo\s+([IVXLCDM\d]+(?:\s*[-–—].*)?)", re.IGNORECASE)
CAPITULO_RE = re.compile(
    r"^\s*cap(?:í|i)tulo\s+([IVXLCDM\d]+(?:\s*[-–—].*)?)",
    re.IGNORECASE,
)
SECCION_RE = re.compile(r"^\s*secci(?:ó|o)n\s+([0-9]+(?:\s*[-–—].*)?)", re.IGNORECASE)
ARTICULO_RE = re.compile(
    r"^\s*(?:art(?:[íi]culo)?\.?)\s*(?:n(?:º|ro|°)?\.?\s*)?(\d+[a-z]?(?:\s*bis)?)\s*[º°]?",
    re.IGNORECASE,
)
INCISO_RE = re.compile(
    r"^\s*(?:inciso\s+)?(\(?[a-z]\)?|[0-9]+(?:\.[0-9]+)?)\s*[-–—.:)]",
    re.IGNORECASE,
)

TOC_LINE_RE = re.compile(r"\.{4,}\s*\d+\s*$")
INDEX_HEADING_RE = re.compile(r"^\s*(?:índice|indice|sumario|contenido)\s*$", re.IGNORECASE)


def strip_page_markers(text: str) -> str:
    cleaned = PAGE_MARKER_RE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", cleaned).strip()


def page_from_text(text: str) -> int | None:
    match = PAGE_MARKER_RE.search(text)
    if not match:
        return None
    return int(match.group(1))


def join_pages_with_markers(pages: List[Tuple[int, str]]) -> str:
    parts: List[str] = []
    for page_number, page_text in pages:
        if not page_text.strip():
            continue
        parts.append(f"\x00PAGE:{page_number}\x00")
        parts.append(page_text.strip())
    return "\n\n".join(parts)


def _is_noise_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if re.fullmatch(r"\d{1,4}", stripped):
        return True
    if re.fullmatch(r"(?:p[aá]gina|pag\.?|pág\.?)\s*\d+", stripped, re.IGNORECASE):
        return True
    if TOC_LINE_RE.search(stripped):
        return True
    if len(stripped) <= 3 and stripped.isupper():
        return True
    return False


def remove_repeated_lines(text: str, min_repeats: int = 3) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) < min_repeats * 2:
        return text

    counts = Counter(line for line in lines if len(line) < 140 and not PAGE_MARKER_RE.match(line))
    repeated = {line for line, count in counts.items() if count >= min_repeats}
    if not repeated:
        return text

    filtered: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if filtered and filtered[-1] != "":
                filtered.append("")
            continue
        if PAGE_MARKER_RE.match(stripped):
            filtered.append(stripped)
            continue
        if stripped in repeated:
            continue
        filtered.append(stripped)
    return "\n".join(filtered)


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = remove_repeated_lines(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    lines: List[str] = []
    in_index = False
    for line in text.splitlines():
        stripped = line.strip()
        if PAGE_MARKER_RE.fullmatch(stripped):
            lines.append(stripped)
            continue
        if INDEX_HEADING_RE.match(stripped):
            in_index = True
            continue
        if in_index:
            if ARTICULO_RE.match(stripped) or CAPITULO_RE.match(stripped) or LIBRO_RE.match(stripped):
                in_index = False
            else:
                continue
        if _is_noise_line(stripped):
            continue
        lines.append(stripped)

    return re.sub(r"\n{2,}", "\n\n", "\n".join(lines)).strip()


def normalize_article(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"\s+", "", value.strip().lower())


def _empty_legal_fields() -> Dict[str, str | None]:
    return {
        "book": None,
        "title": None,
        "chapter": None,
        "section": None,
        "article": None,
        "inciso": None,
    }


def _update_structure_from_line(line: str, state: Dict[str, str | None]) -> None:
    libro_match = LIBRO_RE.match(line)
    if libro_match:
        state["book"] = libro_match.group(1).strip()
        return

    titulo_match = TITULO_RE.match(line)
    if titulo_match:
        state["title"] = titulo_match.group(1).strip()
        return

    capitulo_match = CAPITULO_RE.match(line)
    if capitulo_match:
        state["chapter"] = capitulo_match.group(1).strip()
        return

    seccion_match = SECCION_RE.match(line)
    if seccion_match:
        state["section"] = seccion_match.group(1).strip()
        return

    inciso_match = INCISO_RE.match(line)
    if inciso_match and state.get("article"):
        state["inciso"] = inciso_match.group(1).strip("(). ")


def _metadata_from_state(
    base: Dict[str, Any] | None,
    state: Dict[str, str | None],
    content: str,
) -> Dict[str, Any]:
    merged = dict(base or {})
    page = page_from_text(content) or merged.get("page")
    for key in ("book", "title", "chapter", "section", "article", "inciso"):
        value = state.get(key) or merged.get(key)
        if value:
            merged[key] = value
    if page is not None:
        merged["page"] = page
    merged.setdefault("document_type", merged.get("document_type") or merged.get("type") or "txt")
    return merged


def _split_oversized_unit(content: str, max_chars: int) -> List[str]:
    if len(content) <= max_chars:
        return [content]

    inciso_parts = re.split(r"(?=\n\s*(?:inciso\s+)?\(?[a-z]\)?\s*[-–—.:)])", content, flags=re.IGNORECASE)
    if len(inciso_parts) > 1:
        parts: List[str] = []
        current = ""
        for part in inciso_parts:
            candidate = f"{current}\n{part}".strip() if current else part.strip()
            if len(candidate) > max_chars and current:
                parts.append(current.strip())
                current = part.strip()
            else:
                current = candidate
        if current:
            parts.append(current.strip())
        if parts:
            return parts

    sentences = [sentence.strip() for sentence in re.split(r"(?<=[.;:])\s+", content) if sentence.strip()]
    parts = []
    current = ""
    for sentence in sentences:
        candidate = f"{current}\n{sentence}".strip() if current else sentence
        if len(candidate) > max_chars and current:
            parts.append(current.strip())
            current = sentence
        else:
            current = candidate
    if current:
        parts.append(current.strip())
    return parts or [content[:max_chars]]


def _chunk_by_legal_structure(
    text: str,
    max_chars: int,
    metadata: Dict[str, Any] | None,
) -> List[Dict[str, Any]]:
    state = _empty_legal_fields()
    if metadata:
        for key in state:
            if metadata.get(key):
                state[key] = str(metadata[key])

    units: List[str] = []
    current_lines: List[str] = []

    def flush_unit() -> None:
        if not current_lines:
            return
        units.append("\n".join(current_lines).strip())
        current_lines.clear()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if PAGE_MARKER_RE.fullmatch(line):
            if current_lines and current_lines[-1] != line:
                current_lines.append(line)
            elif not current_lines:
                current_lines.append(line)
            continue

        if ARTICULO_RE.match(line):
            flush_unit()
            article_match = ARTICULO_RE.match(line)
            if article_match:
                state["article"] = normalize_article(article_match.group(1))
            state["inciso"] = None
            current_lines.append(line)
            continue

        if current_lines:
            _update_structure_from_line(line, state)
            current_lines.append(line)
        else:
            _update_structure_from_line(line, state)
            if LEGAL_HEADING_RE.match(line):
                flush_unit()
                current_lines.append(line)
                flush_unit()
            else:
                current_lines.append(line)

    flush_unit()

    if not units:
        return []

    chunks: List[Dict[str, Any]] = []
    rolling_state = _empty_legal_fields()
    if metadata:
        for key in rolling_state:
            if metadata.get(key):
                rolling_state[key] = str(metadata[key])

    for unit in units:
        unit_state = dict(rolling_state)
        for line in unit.splitlines():
            if ARTICULO_RE.match(line.strip()):
                article_match = ARTICULO_RE.match(line.strip())
                if article_match:
                    unit_state["article"] = normalize_article(article_match.group(1))
                    unit_state["inciso"] = None
            _update_structure_from_line(line.strip(), unit_state)

        for key, value in unit_state.items():
            if value:
                rolling_state[key] = value

        for part in _split_oversized_unit(unit, max_chars):
            clean_content = strip_page_markers(part)
            if not clean_content:
                continue
            chunks.append(
                {
                    "content": clean_content,
                    **_metadata_from_state(metadata, unit_state, part),
                }
            )

    return chunks


def chunk_text(text: str, max_chars: int = CHUNK_SIZE, metadata: Dict[str, Any] | None = None) -> List[Dict[str, Any]]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    chunks = _chunk_by_legal_structure(normalized, max_chars=max_chars, metadata=metadata)
    if chunks:
        return chunks

    fallback = strip_page_markers(normalized)
    if not fallback:
        return []
    return [{"content": fallback, **_metadata_from_state(metadata, _empty_legal_fields(), normalized)}]
