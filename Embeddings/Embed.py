#!/usr/bin/env python3
"""
embed_3gpp.py — Local embedding + search pipeline for 3GPP / ETSI specification PDFs.

What it does
------------
1. Extracts text from 3GPP TS/TR PDFs (3gpp.org or ETSI-published) with PyMuPDF
   (pymupdf4llm by default, so tables come out as Markdown).
2. Strips boilerplate: page headers/footers, cover page, table of contents, Foreword,
   IPR / modal-verb sections, and the "Change history" annex (configurable).
3. Rebuilds the clause hierarchy (5 > 5.5 > 5.5.1 > 5.5.1.3, Annex B > B.1, ...)
   and chunks *within* clauses, paragraph-aware, measured in the model's tokens.
4. Prepends a context header to every chunk before embedding, e.g.
       3GPP TS 24.501 V18.5.0 (Rel-18) | 5.5 5GMM specific procedures >
       5.5.1 Registration procedure > 5.5.1.3 Mobility and periodic registration update
   which improves retrieval a lot for short / generic clause bodies.
5. Embeds with a local model (default: Qwen3-Embedding-0.6B) and stores vectors +
   rich metadata (spec, version, release, clause, pages) in an embedded LanceDB
   database, plus a full-text (BM25) index for hybrid search. Exact identifiers
   such as "T3512", "5G-GUTI", "SUCI" or IE names benefit a lot from the keyword side.
6. Incremental: unchanged files (by SHA-256) are skipped on re-runs; changed files
   are replaced.

Install (do this once)
----------------------
    # 1. PyTorch for your platform: https://pytorch.org/get-started/locally/
    #    (CUDA build on NVIDIA; the default wheel already supports Apple-silicon MPS)
    pip install torch
    # 2. Everything else
    pip install "sentence-transformers>=3.3" pymupdf pymupdf4llm lancedb pyarrow tqdm
    # 3. Optional, NVIDIA only: faster attention for the Qwen3 models
    pip install flash-attn --no-build-isolation

Usage
-----
    # Index a folder of PDFs (recursive) into ./3gpp_index
    python embed_3gpp.py index ./specs --db ./3gpp_index

    # Bigger / better model (needs a GPU with ~10 GB+ VRAM for 4B in fp16)
    python embed_3gpp.py index ./specs --db ./3gpp_index_4b --model qwen3-4b

    # Inspect parsing/chunking without embedding anything
    python embed_3gpp.py index ./specs --dry-run --dump-chunks chunks.jsonl

    # Search (hybrid vector + BM25 by default), optional filters and reranking
    python embed_3gpp.py search "when does the UE start timer T3512" --db ./3gpp_index
    python embed_3gpp.py search "SUCI concealment" --spec 33.501 --release 18 --rerank -k 5

    # List the available model presets
    python embed_3gpp.py models

Model choice
------------
Qwen3-Embedding is the strongest open-weight family for text retrieval right now, with
a 32K context, instruction-aware queries, and Matryoshka (truncatable) outputs.
  qwen3-0.6b      default: best quality/speed trade-off; runs fine on CPU, fast on GPU/MPS
  qwen3-4b        noticeably better retrieval; wants a GPU
  qwen3-8b        top of the open leaderboards; wants a 24 GB+ GPU
  embeddinggemma  300M, very light (good for laptops / CPU-only); gated on Hugging Face
  bge-m3          solid multilingual baseline, 8K context
Pick one model per database. The model is recorded in the DB and reused by `search`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Iterable

log = logging.getLogger("embed_3gpp")

TABLE_NAME = "chunks"
META_FILE = "index_meta.json"

# ---------------------------------------------------------------------------
# Model presets
# ---------------------------------------------------------------------------

QWEN_QUERY_PROMPT = (
    "Instruct: Given a question about 3GPP mobile network specifications, "
    "retrieve specification passages that answer the question\nQuery: "
)


@dataclass(frozen=True)
class ModelPreset:
    hf_id: str
    dim: int
    query_prompt: str = ""
    doc_style: str = "header"   # "header" -> header + body; "gemma" -> "title: ... | text: ..."
    max_seq_len: int = 8192
    fp16_ok: bool = True
    left_padding: bool = False  # Qwen3 embedding uses last-token pooling -> left padding
    note: str = ""


PRESETS: dict[str, ModelPreset] = {
    "qwen3-0.6b": ModelPreset("Qwen/Qwen3-Embedding-0.6B", 1024, QWEN_QUERY_PROMPT,
                              left_padding=True, note="default; ~1.2 GB fp16"),
    "qwen3-4b": ModelPreset("Qwen/Qwen3-Embedding-4B", 2560, QWEN_QUERY_PROMPT,
                            left_padding=True, note="~8 GB fp16; GPU recommended"),
    "qwen3-8b": ModelPreset("Qwen/Qwen3-Embedding-8B", 4096, QWEN_QUERY_PROMPT,
                            left_padding=True, note="~16 GB fp16; large GPU"),
    "embeddinggemma": ModelPreset("google/embeddinggemma-300m", 768,
                                  "task: search result | query: ", doc_style="gemma",
                                  max_seq_len=2048, fp16_ok=False,
                                  note="300M, CPU-friendly; accept licence on HF first"),
    "bge-m3": ModelPreset("BAAI/bge-m3", 1024, "", max_seq_len=8192,
                          note="multilingual baseline"),
}

DEFAULT_RERANKER = "BAAI/bge-reranker-v2-m3"

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Unit:
    """A paragraph-level piece of text from one page."""
    page: int
    text: str
    md_heading: bool = False
    is_table: bool = False


@dataclass
class Section:
    clause: str
    title: str
    path: list[tuple[str, str]]          # [(clause, title), ...] root -> self
    paras: list[tuple[int, str]] = field(default_factory=list)  # (page, text)


@dataclass
class DocMeta:
    doc_type: str = ""      # TS / TR
    spec: str = ""          # e.g. 24.501
    version: str = ""       # e.g. 18.5.0
    release: int | None = None
    date: str = ""          # e.g. 2024-03
    spec_title: str = ""

    @property
    def label(self) -> str:
        parts = ["3GPP", self.doc_type or "", self.spec or "?"]
        s = " ".join(p for p in parts if p)
        if self.version:
            s += f" V{self.version}"
        if self.release:
            s += f" (Rel-{self.release})"
        return s


# ---------------------------------------------------------------------------
# Regexes for 3GPP document structure
# ---------------------------------------------------------------------------

# Running headers, e.g. "3GPP TS 23.501 V18.5.0 (2024-03)", possibly with page/Release glued on
HEADER_RES = [
    re.compile(r"3GPP\s+T[SR]\s+\d{2}\.\d{3}(?:-\d+)?\s+V\d+\.\d+\.\d+\s*\(\d{4}-\d{2}\)"),
    re.compile(r"3GPP\s+T[SR]\s+\d{2}\.\d{3}(?:-\d+)?\s+version\s+\d+\.\d+\.\d+\s+Release\s+\d+"),
    re.compile(r"ETSI\s+T[SR]\s+1\d{2}\s?\d{3}(?:-\d+)?\s+V\d+\.\d+\.\d+\s*\(\d{4}-\d{2}\)"),
]
FOOTER_RE = re.compile(r"^(?:(?:Release\s+\d+|3GPP|ETSI)\s*)+(?:\d{1,4})?$|^\d{1,4}$")

CLAUSE_RE = re.compile(
    r"^(?P<num>(?:\d{1,2}|[A-Z]{1,2})(?:\.\d{1,3}){0,8})\.?\s+(?P<title>\S.{0,200})$"
)
ANNEX_RE = re.compile(
    r"^Annex\s+(?P<letter>[A-Z]{1,2})\s*\((?P<kind>normative|informative)\)\s*:?\s*(?P<title>.*)$",
    re.I,
)
TOC_LINE_RE = re.compile(
    r"^(?:(?:\d{1,2}|[A-Z]{1,2})(?:\.\d{1,3})*|Annex\s+[A-Z]{1,2}\b.*|Foreword|Introduction)"
    r"\s+.{1,220}?[\s.…]+\d{1,4}$"
)
SKIP_TITLE_RE = re.compile(
    r"^(?:Foreword|Intellectual Property Rights|Modal verbs terminology|Legal Notice|"
    r"Contents|Change history|Change History|Document history)\b",
    re.I,
)
# First token of a "title" that suggests a false-positive heading ("5 ms", "3.5 Mbit/s")
UNIT_WORDS = {
    "ms", "s", "sec", "seconds", "minutes", "min", "hours", "h", "db", "dbm", "hz", "khz",
    "mhz", "ghz", "bit", "bits", "bit/s", "kbit/s", "mbit/s", "gbit/s", "kbps", "mbps",
    "gbps", "byte", "bytes", "octet", "octets", "%", "km", "m", "x", "times", "and", "or",
    "to", "of", "the", "in", "is", "are", "if", "when",
}

# Metadata from title pages and filenames
META_3GPP_RE = re.compile(
    r"3GPP\s+(TS|TR)\s+(\d{2}\.\d{3}(?:-\d{1,2})?)\s+V(\d+\.\d+\.\d+)\s*\((\d{4}-\d{2})\)"
)
META_ETSI_RE = re.compile(
    r"ETSI\s+(TS|TR)\s+1(\d{2})\s?(\d{3})(?:-(\d{1,2}))?\s+V(\d+\.\d+\.\d+)\s*\((\d{4}-\d{2})\)"
)
META_ETSI_VER_RE = re.compile(
    r"3GPP\s+(TS|TR)\s+(\d{2}\.\d{3}(?:-\d{1,2})?)\s+version\s+(\d+\.\d+\.\d+)\s+Release\s+(\d+)"
)
RELEASE_RE = re.compile(r"\(\s*Release\s+(\d{1,2})\s*\)")
FNAME_3GPP_RE = re.compile(r"(?<![0-9a-z])(\d{5})(?:-(\d{1,2}))?-([0-9a-z])([0-9a-z])([0-9a-z])(?![0-9a-z])", re.I)
FNAME_ETSI_RE = re.compile(r"t([sr])_1(\d{2})(\d{3})(\d{2})?v(\d{2})(\d{2})(\d{2})p", re.I)
SERIES_LABELS_RE = re.compile(
    r"^(?:Digital cellular telecommunications system.*|Universal Mobile Telecommunications System.*|"
    r"LTE|5G|6G|GSM|UMTS)$",
    re.I,
)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------

_MD_EMPH_RE = re.compile(r"(\*\*|__|(?<!\w)_(?=\S)|(?<=\S)_(?!\w)|`)")
_WS_RE = re.compile(r"[ \t  ​]+")


def clean_inline(text: str) -> str:
    text = _MD_EMPH_RE.sub("", text)
    text = text.replace("­", "")   # soft hyphen
    return _WS_RE.sub(" ", text).strip()


def is_header_footer(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if FOOTER_RE.match(s):
        return True
    if len(s) < 160 and any(r.search(s) for r in HEADER_RES):
        return True
    return False


def join_wrapped(lines: Iterable[str]) -> str:
    """Join visually wrapped lines into one paragraph, keeping hyphenated terms intact."""
    out = ""
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if not out:
            out = ln
        elif out.endswith("-") and not out.endswith(" -"):
            out += ln               # "5G-" + "GUTI" -> "5G-GUTI"
        else:
            out += " " + ln
    return out


def file_sha256(path: Path, bufsize: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(bufsize):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# PDF extraction (runs in worker processes)
# ---------------------------------------------------------------------------

def _import_pymupdf():
    try:
        import pymupdf  # PyMuPDF >= 1.24
        return pymupdf
    except ImportError:
        import fitz  # older PyMuPDF
        return fitz


def extract_units_pymupdf4llm(path: str, margin: float) -> tuple[list[list[Unit]], list[list[str]]]:
    import pymupdf4llm

    kwargs = dict(page_chunks=True, margins=(0, margin, 0, margin),
                  show_progress=False, ignore_images=True)
    try:
        chunks = pymupdf4llm.to_markdown(path, **kwargs)
    except TypeError:   # older/newer signature differences
        chunks = pymupdf4llm.to_markdown(path, page_chunks=True)

    pages_units: list[list[Unit]] = []
    pages_raw: list[list[str]] = []
    for idx, ch in enumerate(chunks):
        pno = idx + 1
        md = ch["text"] if isinstance(ch, dict) else str(ch)
        raw_lines = [clean_inline(l.lstrip("#").strip()) for l in md.splitlines()]
        pages_raw.append([l for l in raw_lines if l])

        units: list[Unit] = []
        para: list[str] = []
        table: list[str] = []

        def flush_para():
            if para:
                t = clean_inline(join_wrapped(para))
                if t and not is_header_footer(t):
                    units.append(Unit(pno, t))
                para.clear()

        def flush_table():
            if table:
                rows = [r for r in table if not re.fullmatch(r"\|?\s*:?-{2,}.*", r)]
                rows = [clean_inline(r) for r in rows]
                if rows:
                    units.append(Unit(pno, "\n".join(rows), is_table=True))
                table.clear()

        for line in md.splitlines():
            s = line.strip()
            if s.startswith("|"):
                flush_para()
                table.append(s)
                continue
            flush_table()
            if not s or re.fullmatch(r"-{3,}|\*{3,}", s):
                flush_para()
                continue
            if s.startswith("#"):
                flush_para()
                t = clean_inline(s.lstrip("#"))
                if t and not is_header_footer(t):
                    units.append(Unit(pno, t, md_heading=True))
                continue
            if is_header_footer(clean_inline(s)):
                continue
            # A line that on its own looks like a clause heading starts a new unit
            cs = clean_inline(s)
            if (CLAUSE_RE.match(cs) or ANNEX_RE.match(cs)) and len(cs) < 160:
                flush_para()
                units.append(Unit(pno, cs))
                continue
            para.append(s)
        flush_para()
        flush_table()
        pages_units.append(units)
    return pages_units, pages_raw


def extract_units_pymupdf(path: str, margin: float) -> tuple[list[list[Unit]], list[list[str]]]:
    pymupdf = _import_pymupdf()
    pages_units: list[list[Unit]] = []
    pages_raw: list[list[str]] = []
    with pymupdf.open(path) as doc:
        for pno, page in enumerate(doc, 1):
            r = page.rect
            clip = pymupdf.Rect(r.x0, r.y0 + margin, r.x1, r.y1 - margin)
            raw = page.get_text("text", clip=clip)
            pages_raw.append([clean_inline(l) for l in raw.splitlines() if l.strip()])
            units: list[Unit] = []
            for b in page.get_text("blocks", clip=clip, sort=True):
                if b[6] != 0:      # 0 = text block, 1 = image
                    continue
                lines = [l for l in b[4].splitlines() if l.strip()]
                lines = [l for l in lines if not is_header_footer(clean_inline(l))]
                if not lines:
                    continue
                t = clean_inline(join_wrapped(lines))
                if t:
                    units.append(Unit(pno, t))
            pages_units.append(units)
    return pages_units, pages_raw


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

def _version_from_chars(chars: str) -> str:
    return ".".join(str(int(c, 36)) for c in chars)


def extract_meta(first_pages_text: str, filename: str) -> DocMeta:
    m = DocMeta()
    text = first_pages_text

    if g := META_3GPP_RE.search(text):
        m.doc_type, m.spec, m.version, m.date = g.group(1), g.group(2), g.group(3), g.group(4)
    elif g := META_ETSI_RE.search(text):
        m.doc_type = g.group(1)
        m.spec = f"{g.group(2)}.{g.group(3)}" + (f"-{g.group(4)}" if g.group(4) else "")
        m.version, m.date = g.group(5), g.group(6)
    if g := META_ETSI_VER_RE.search(text):
        m.doc_type = m.doc_type or g.group(1)
        m.spec = m.spec or g.group(2)
        m.version = m.version or g.group(3)
        m.release = int(g.group(4))
    if m.release is None and (g := RELEASE_RE.search(text)):
        m.release = int(g.group(1))

    # Filename fallbacks: "23501-i50.pdf" (3GPP) or "ts_123501v180500p.pdf" (ETSI)
    if not m.spec or not m.version:
        if g := FNAME_ETSI_RE.search(filename):
            m.doc_type = m.doc_type or f"T{g.group(1).upper()}"
            m.spec = m.spec or f"{g.group(2)}.{g.group(3)}" + (f"-{int(g.group(4))}" if g.group(4) else "")
            m.version = m.version or f"{int(g.group(5))}.{int(g.group(6))}.{int(g.group(7))}"
        elif g := FNAME_3GPP_RE.search(filename):
            num = g.group(1)
            m.spec = m.spec or f"{num[:2]}.{num[2:]}" + (f"-{g.group(2)}" if g.group(2) else "")
            m.version = m.version or _version_from_chars(g.group(3) + g.group(4) + g.group(5))
    if m.release is None and m.version:
        major = int(m.version.split(".")[0])
        if 8 <= major <= 30:            # V18.x.y == Rel-18 for modern specs
            m.release = major
    if not m.doc_type and m.spec:
        # Rough heuristic: xx.8xx / xx.9xx are TRs
        m.doc_type = "TR" if re.match(r"\d{2}\.[89]", m.spec) else "TS"

    m.spec_title = _extract_spec_title(text)
    return m


def _extract_spec_title(text: str) -> str:
    flat = re.sub(r"\s+", " ", text)
    for r in HEADER_RES[::-1]:          # drop running headers so they don't leak into the title
        flat = r.sub(" ", flat) if r is not HEADER_RES[1] else flat
    # 3GPP cover: "Technical Specification Group X; <title>; Stage 3 (Release 18)"
    if g := re.search(r"Technical Specification Group [^;]{3,120};\s*(.{5,300}?)\s*\(Release\s+\d+\)", flat):
        return g.group(1).strip(" ;")
    # ETSI cover: "...; LTE; 5G; <title> (3GPP TS 24.501 version 18.5.0 Release 18)"
    if g := re.search(r"([^()]{5,400}?(?:\([^()]{1,40}\)[^()]{0,200}?)*)\(3GPP\s+T[SR]\s+\d", flat):
        parts = [p.strip() for p in g.group(1).split(";")]
        parts = [p for p in parts if p and not SERIES_LABELS_RE.match(p)]
        if parts:
            return "; ".join(parts[-2:])[-250:].strip()
    return ""


# ---------------------------------------------------------------------------
# Clause structure
# ---------------------------------------------------------------------------

def is_toc_page(raw_lines: list[str]) -> bool:
    if not raw_lines:
        return False
    if any(l.strip().lower() in ("contents", "table of contents") for l in raw_lines[:8]):
        return True
    hits = sum(1 for l in raw_lines if TOC_LINE_RE.match(l))
    return hits >= 5 and hits / len(raw_lines) >= 0.4


def _clause_key(num: str) -> tuple[int, ...]:
    key = []
    for p in num.split("."):
        if p.isdigit():
            key.append(int(p))
        else:  # Annex letters sort after all numeric clauses: A < B < ... < Z < AA
            key.append(1000 + sum((ord(c) - 64) * 27 ** i for i, c in enumerate(reversed(p.upper()))))
    return tuple(key)


def _parse_heading(text: str) -> tuple[str, str] | None:
    """Return (clause, title) if `text` looks like a clause or annex heading."""
    if "\n" in text or len(text) > 220:
        return None
    if a := ANNEX_RE.match(text):
        letter = a.group("letter").upper()
        title = a.group("title").strip()
        return letter, (f"Annex {letter} ({a.group('kind').lower()})" + (f": {title}" if title else ""))
    m = CLAUSE_RE.match(text)
    if not m:
        return None
    num, title = m.group("num"), m.group("title").strip()
    parts = num.split(".")
    if parts[0].isalpha() and len(parts) < 2:          # "A Something" is not a heading
        return None
    if not re.search(r"[A-Za-z]", title):
        return None
    if title[-1] in ".,;" and not title.endswith("..."):
        return None
    words = title.split()
    if len(words) > 25 or words[0].lower().strip(",.:()") in UNIT_WORDS:
        return None
    if re.search(r"\s\d{1,4}$", title) and len(words) > 1 and TOC_LINE_RE.match(text):
        return None                                     # looks like a TOC entry
    return num, title


def sectionize(pages_units: list[list[Unit]], pages_raw: list[list[str]],
               keep_boilerplate: bool = False) -> list[Section]:
    """Rebuild the clause tree and return body sections in document order."""

    def run(require_scope: bool) -> list[Section]:
        sections: list[Section] = []
        stack: list[tuple[str, str, bool]] = []     # (clause, title, skip)
        current: Section | None = None
        current_skip = False
        last_key: tuple[int, ...] = ()
        started = not require_scope
        pending_annex: tuple[str, str] | None = None

        def open_section(num: str, title: str):
            nonlocal current, current_skip, stack, last_key
            stack = [s for s in stack if num.startswith(s[0] + ".")]
            parent_skip = any(s[2] for s in stack)
            bare = re.sub(r"^Annex [A-Z]+ \(\w+\):?\s*", "", title)
            skip = (not keep_boilerplate) and (parent_skip or bool(SKIP_TITLE_RE.match(bare)))
            stack.append((num, title, skip))
            current = Section(num, title, [(c, t) for c, t, _ in stack])
            current_skip = skip
            sections.append(current) if not skip else None
            last_key = _clause_key(num)

        for page_idx, units in enumerate(pages_units):
            raw = pages_raw[page_idx] if page_idx < len(pages_raw) else []
            if is_toc_page(raw):
                continue
            for u in units:
                text = u.text.strip()
                if not text:
                    continue

                # Annex heading split over two lines: "Annex B (informative):" / "Change history"
                if pending_annex and not u.is_table and len(text) < 160 and not _parse_heading(text):
                    letter, label = pending_annex
                    pending_annex = None
                    open_section(letter, f"{label}: {text}")
                    continue
                pending_annex = None

                h = None if u.is_table else _parse_heading(text)

                # Body "1 Scope" (re)starts the document; this also recovers from TOC false starts.
                if h and h[0] == "1" and h[1].strip().lower() == "scope":
                    sections.clear()
                    stack.clear()
                    last_key = ()
                    started = True
                    open_section("1", "Scope")
                    continue
                if not started:
                    continue

                if h:
                    num, title = h
                    key = _clause_key(num)
                    parts = num.split(".")
                    stack_nums = [s[0] for s in stack]
                    is_annex = ANNEX_RE.match(text) is not None
                    accept = key > last_key
                    if accept and not (u.md_heading or is_annex):
                        if len(parts) == 1:
                            top = stack_nums[0] if stack_nums else None
                            if top is None:
                                accept = not require_scope
                            elif top.isdigit() and num.isdigit():
                                accept = 0 < int(num) - int(top) <= 3   # tolerate one missed heading
                            else:
                                accept = False
                        else:
                            parent = ".".join(parts[:-1])
                            same_top = bool(stack_nums) and parts[0] == stack_nums[0]
                            depth_ok = bool(stack_nums) and len(parts) <= len(stack_nums[-1].split(".")) + 1
                            accept = parent in stack_nums or (same_top and depth_ok)
                    if accept:
                        if is_annex and not ANNEX_RE.match(text).group("title").strip():
                            pending_annex = (num, title)
                            continue
                        open_section(num, title)
                        continue

                if current is not None and not current_skip:
                    current.paras.append((u.page, text))
        return [s for s in sections if s.paras]

    secs = run(require_scope=True)
    if not secs:
        log.debug("No '1 Scope' clause found; falling back to unanchored parsing")
        secs = run(require_scope=False)
    if not secs:
        # Last resort: one pseudo-section per page so the content is still searchable
        secs = [Section("", f"page {i + 1}", [("", f"page {i + 1}")], [(u.page, u.text) for u in units])
                for i, units in enumerate(pages_units) if units]
    return secs


# ---------------------------------------------------------------------------
# Worker entry point: parse one PDF
# ---------------------------------------------------------------------------

def parse_document(path: str, parser: str, margin: float, keep_boilerplate: bool) -> dict:
    t0 = time.time()
    try:
        if parser == "pymupdf4llm":
            try:
                pages_units, pages_raw = extract_units_pymupdf4llm(path, margin)
            except ImportError:
                pages_units, pages_raw = extract_units_pymupdf(path, margin)
        else:
            pages_units, pages_raw = extract_units_pymupdf(path, margin)

        # Title-page metadata from the unclipped first pages (headers carry spec + version)
        try:
            pymupdf = _import_pymupdf()
            with pymupdf.open(path) as doc:
                head = "\n".join(doc[i].get_text() for i in range(min(3, len(doc))))
        except Exception:
            head = "\n".join("\n".join(r) for r in pages_raw[:3])
        meta = extract_meta(head, os.path.basename(path))
        sections = sectionize(pages_units, pages_raw, keep_boilerplate)
        return {"path": path, "meta": asdict(meta), "sections": [asdict(s) for s in sections],
                "n_pages": len(pages_units), "seconds": time.time() - t0, "error": None}
    except Exception as e:  # keep the batch going
        return {"path": path, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

_SENT_SPLIT_RE = re.compile(r"(?<=[.;:])\s+(?=[A-Z0-9(\-])")


def _split_long(text: str, count: Callable[[str], int], max_tokens: int) -> list[str]:
    """Split one oversized paragraph by sentences, then by words as a last resort."""
    if count(text) <= max_tokens:
        return [text]
    seps = text.split("\n") if "\n" in text else _SENT_SPLIT_RE.split(text)
    joiner = "\n" if "\n" in text else " "
    if len(seps) == 1:
        words = text.split(" ")
        if len(words) == 1:
            return [text]               # let the model truncate pathological tokens
        mid = len(words) // 2
        return (_split_long(" ".join(words[:mid]), count, max_tokens)
                + _split_long(" ".join(words[mid:]), count, max_tokens))
    out, buf = [], ""
    for s in seps:
        cand = f"{buf}{joiner}{s}" if buf else s
        if count(cand) <= max_tokens:
            buf = cand
        else:
            if buf:
                out.append(buf)
            if count(s) > max_tokens:
                out.extend(_split_long(s, count, max_tokens))
                buf = ""
            else:
                buf = s
    if buf:
        out.append(buf)
    return out


def section_header(meta: DocMeta, sec: dict, max_levels: int = 3) -> str:
    path = sec["path"][-max_levels:]
    crumbs = " > ".join(f"{c} {t}".strip() if not t.startswith("Annex") else t for c, t in path)
    return f"{meta.label} | {crumbs}" if crumbs else meta.label


def chunk_section(sec: dict, header: str, count: Callable[[str], int],
                  max_tokens: int, overlap: int) -> list[dict]:
    budget = max(64, max_tokens - count(header) - 4)
    pieces: list[tuple[int, str, int]] = []      # (page, text, tokens)
    for page, text in sec["paras"]:
        for p in _split_long(text, count, budget):
            pieces.append((page, p, count(p)))

    chunks: list[dict] = []
    buf: list[tuple[int, str, int]] = []
    buf_tok = 0

    def emit():
        if buf:
            chunks.append({"text": "\n\n".join(p[1] for p in buf),
                           "page_start": min(p[0] for p in buf),
                           "page_end": max(p[0] for p in buf),
                           "n_tokens": buf_tok})

    for piece in pieces:
        if buf and buf_tok + piece[2] > budget:
            emit()
            # paragraph-level overlap: carry trailing paragraphs up to `overlap` tokens
            carry, carry_tok = [], 0
            for prev in reversed(buf):
                if carry_tok + prev[2] > overlap:
                    break
                carry.insert(0, prev)
                carry_tok += prev[2]
            if carry and carry_tok + piece[2] > budget:
                carry, carry_tok = [], 0
            buf, buf_tok = carry, carry_tok
        buf.append(piece)
        buf_tok += piece[2]
    emit()
    return chunks


def build_records(parsed: dict, count: Callable[[str], int], preset: ModelPreset,
                  max_tokens: int, overlap: int, file_sha: str) -> list[dict]:
    meta = DocMeta(**parsed["meta"])
    src = parsed["path"]
    records = []
    idx = 0
    for sec in parsed["sections"]:
        header = section_header(meta, sec)
        for ch in chunk_section(sec, header, count, max_tokens, overlap):
            if preset.doc_style == "gemma":
                embed_text = f"title: {header} | text: {ch['text']}"
            else:
                embed_text = f"{header}\n\n{ch['text']}"
            records.append({
                "id": hashlib.sha1(f"{file_sha}:{idx}".encode()).hexdigest(),
                "doc_type": meta.doc_type, "spec": meta.spec, "version": meta.version,
                "release": meta.release if meta.release is not None else -1,
                "date": meta.date, "spec_title": meta.spec_title,
                "clause": sec["clause"], "clause_title": sec["title"],
                "section_path": " > ".join(f"{c} {t}".strip() for c, t in sec["path"]),
                "page_start": ch["page_start"], "page_end": ch["page_end"],
                "chunk_index": idx, "n_tokens": ch["n_tokens"],
                "context": header, "text": ch["text"], "embed_text": embed_text,
                "source_file": os.path.basename(src), "source_path": src,
                "file_sha256": file_sha,
            })
            idx += 1
    return records


# ---------------------------------------------------------------------------
# Embedding model
# ---------------------------------------------------------------------------

def pick_device(requested: str) -> str:
    if requested != "auto":
        return requested
    import torch
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_embedder(preset: ModelPreset, device: str, dim: int | None, max_seq: int):
    import torch
    from sentence_transformers import SentenceTransformer

    if device == "cuda":
        dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else (
            torch.float16 if preset.fp16_ok else torch.float32)
    elif device == "mps":
        dtype = torch.float16 if preset.fp16_ok else torch.float32
    else:
        dtype = torch.float32

    model_kwargs: dict = {"torch_dtype": dtype}
    if device == "cuda" and dtype in (torch.float16, torch.bfloat16):
        try:
            import flash_attn  # noqa: F401
            model_kwargs["attn_implementation"] = "flash_attention_2"
        except ImportError:
            model_kwargs["attn_implementation"] = "sdpa"
    tokenizer_kwargs = {"padding_side": "left"} if preset.left_padding else {}

    log.info("Loading %s on %s (%s)%s", preset.hf_id, device, str(dtype).replace("torch.", ""),
             f", truncate_dim={dim}" if dim else "")
    try:
        model = SentenceTransformer(preset.hf_id, device=device, model_kwargs=model_kwargs,
                                    tokenizer_kwargs=tokenizer_kwargs, truncate_dim=dim)
    except (ValueError, ImportError) as e:   # e.g. attention impl unsupported
        log.warning("Retrying model load without custom attention (%s)", e)
        model_kwargs.pop("attn_implementation", None)
        model = SentenceTransformer(preset.hf_id, device=device, model_kwargs=model_kwargs,
                                    tokenizer_kwargs=tokenizer_kwargs, truncate_dim=dim)
    model.max_seq_length = min(max_seq, preset.max_seq_len)
    return model


def make_token_counter(tokenizer) -> Callable[[str], int]:
    if tokenizer is None:
        return lambda s: max(1, len(s) // 4)          # rough fallback (dry runs only)
    return lambda s: len(tokenizer(s, add_special_tokens=False)["input_ids"])


def encode(model, texts: list[str], batch_size: int):
    import numpy as np
    vecs = model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                        convert_to_numpy=True, show_progress_bar=False)
    return np.asarray(vecs, dtype="float32")


# ---------------------------------------------------------------------------
# Storage (LanceDB)
# ---------------------------------------------------------------------------

def _sql_str(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def arrow_schema(dim: int):
    import pyarrow as pa
    return pa.schema([
        ("id", pa.string()), ("vector", pa.list_(pa.float32(), dim)),
        ("doc_type", pa.string()), ("spec", pa.string()), ("version", pa.string()),
        ("release", pa.int32()), ("date", pa.string()), ("spec_title", pa.string()),
        ("clause", pa.string()), ("clause_title", pa.string()), ("section_path", pa.string()),
        ("page_start", pa.int32()), ("page_end", pa.int32()), ("chunk_index", pa.int32()),
        ("n_tokens", pa.int32()), ("context", pa.string()), ("text", pa.string()),
        ("source_file", pa.string()), ("source_path", pa.string()), ("file_sha256", pa.string()),
    ])


def to_arrow(records: list[dict], vectors, dim: int):
    import pyarrow as pa
    schema = arrow_schema(dim)
    cols = {}
    for f in schema:
        if f.name == "vector":
            flat = pa.array(vectors.reshape(-1), type=pa.float32())
            cols["vector"] = pa.FixedSizeListArray.from_arrays(flat, dim)
        else:
            cols[f.name] = pa.array([r[f.name] for r in records], type=f.type)
    return pa.Table.from_pydict(cols, schema=schema)


def open_table(db_path: Path, dim: int, create: bool):
    import lancedb
    db = lancedb.connect(str(db_path))
    names = db.table_names() if hasattr(db, "table_names") else list(db.list_tables())
    if TABLE_NAME in names:
        return db, db.open_table(TABLE_NAME)
    if not create:
        raise SystemExit(f"No '{TABLE_NAME}' table in {db_path}. Run `index` first.")
    return db, db.create_table(TABLE_NAME, schema=arrow_schema(dim))


def load_index_meta(db_path: Path) -> dict:
    p = db_path / META_FILE
    if p.exists():
        return json.loads(p.read_text())
    return {}


def save_index_meta(db_path: Path, meta: dict) -> None:
    db_path.mkdir(parents=True, exist_ok=True)
    tmp = db_path / (META_FILE + ".tmp")
    tmp.write_text(json.dumps(meta, indent=2))
    tmp.replace(db_path / META_FILE)


def build_fts_index(tbl) -> None:
    try:
        tbl.create_fts_index("text", replace=True)
        log.info("Full-text index built")
    except Exception as e:
        log.warning("Could not build full-text index (hybrid search disabled): %s", e)


# ---------------------------------------------------------------------------
# `index` command
# ---------------------------------------------------------------------------

def discover_pdfs(inputs: list[str]) -> list[Path]:
    files: list[Path] = []
    for inp in inputs:
        p = Path(inp).expanduser()
        if p.is_dir():
            files.extend(sorted(q for q in p.rglob("*") if q.suffix.lower() == ".pdf"))
        elif p.suffix.lower() == ".pdf" and p.exists():
            files.append(p)
        else:
            log.warning("Skipping %s (not a PDF or directory)", p)
    seen, out = set(), []
    for f in files:
        rp = f.resolve()
        if rp not in seen:
            seen.add(rp)
            out.append(rp)
    return out


def _progress(iterable, total: int, desc: str):
    try:
        from tqdm import tqdm
        return tqdm(iterable, total=total, desc=desc, unit="file")
    except ImportError:
        return iterable


def cmd_index(args) -> None:
    preset = PRESETS[args.model] if args.model in PRESETS else ModelPreset(args.model, 0)
    files = discover_pdfs(args.inputs)
    if not files:
        raise SystemExit("No PDFs found.")
    db_path = Path(args.db).expanduser().resolve()

    # --- model / tokenizer
    model = None
    tokenizer = None
    if args.dry_run:
        try:
            from transformers import AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(preset.hf_id)
        except Exception as e:
            log.warning("Tokenizer unavailable (%s); using a ~4 chars/token estimate", e)
        dim = args.dim or preset.dim
    else:
        device = pick_device(args.device)
        model = load_embedder(preset, device, args.dim, max_seq=args.max_tokens + 64)
        tokenizer = model.tokenizer
        dim = model.get_sentence_embedding_dimension()
        batch_size = args.batch_size or (32 if device == "cuda" else 8)
    count = make_token_counter(tokenizer)

    # --- incremental bookkeeping
    meta = {} if args.dry_run else load_index_meta(db_path)
    if meta and not args.dry_run:
        if meta.get("model") != preset.hf_id or meta.get("dim") != dim:
            raise SystemExit(
                f"{db_path} was built with {meta.get('model')} (dim={meta.get('dim')}); "
                f"you asked for {preset.hf_id} (dim={dim}). Use a different --db, or --rebuild.")
    if args.rebuild and not args.dry_run and db_path.exists():
        import shutil
        shutil.rmtree(db_path)
        meta = {}
    meta.setdefault("model", preset.hf_id)
    meta.setdefault("preset", args.model)
    meta.setdefault("dim", dim)
    meta.setdefault("query_prompt", preset.query_prompt)
    meta.setdefault("files", {})

    todo: list[tuple[Path, str]] = []
    for f in files:
        sha = file_sha256(f)
        if not args.dry_run and meta["files"].get(str(f), {}).get("sha256") == sha:
            continue
        todo.append((f, sha))
    log.info("%d PDF(s) found, %d to process, %d unchanged", len(files), len(todo), len(files) - len(todo))
    if not todo:
        return

    tbl = None
    if not args.dry_run:
        _, tbl = open_table(db_path, dim, create=True)
        save_index_meta(db_path, meta)

    dump = open(args.dump_chunks, "w", encoding="utf-8") if args.dump_chunks else None
    total_chunks, failures, t_start = 0, [], time.time()
    sha_by_path = {str(f): sha for f, sha in todo}
    parse_args = (args.parser, args.margin, args.keep_boilerplate)

    def handle(parsed: dict):
        nonlocal total_chunks
        path = parsed["path"]
        if parsed.get("error"):
            failures.append((path, parsed["error"]))
            log.error("Failed: %s — %s", path, parsed["error"])
            return
        sha = sha_by_path[path]
        records = build_records(parsed, count, preset, args.max_tokens, args.overlap, sha)
        if not records:
            failures.append((path, "no text extracted (scanned PDF? try OCR first)"))
            log.warning("No chunks from %s", path)
            return
        if dump:
            for r in records:
                dump.write(json.dumps({k: v for k, v in r.items() if k != "embed_text"},
                                      ensure_ascii=False) + "\n")
        if not args.dry_run:
            vecs = encode(model, [r["embed_text"] for r in records], batch_size)
            tbl.delete(f"source_path = {_sql_str(path)}")     # replace older version of this file
            tbl.add(to_arrow(records, vecs, dim))
            meta["files"][path] = {"sha256": sha, "n_chunks": len(records),
                                   "spec": parsed["meta"]["spec"], "version": parsed["meta"]["version"],
                                   "indexed_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
            save_index_meta(db_path, meta)
        total_chunks += len(records)
        m = DocMeta(**parsed["meta"])
        log.info("%s: %s — %d pages, %d sections, %d chunks", os.path.basename(path), m.label,
                 parsed["n_pages"], len(parsed["sections"]), len(records))

    try:
        if args.workers <= 0:
            for f, _ in _progress(todo, len(todo), "PDFs"):
                handle(parse_document(str(f), *parse_args))
        else:
            # Parse PDFs in parallel processes while the main process embeds on the GPU/CPU
            with ProcessPoolExecutor(max_workers=args.workers) as ex:
                futs = [ex.submit(parse_document, str(f), *parse_args) for f, _ in todo]
                for fut in _progress(as_completed(futs), len(futs), "PDFs"):
                    handle(fut.result())
    finally:
        if dump:
            dump.close()

    if tbl is not None and total_chunks:
        build_fts_index(tbl)
        n_rows = tbl.count_rows()
        if args.ann_index and n_rows >= 10_000:
            try:
                tbl.create_index(metric="cosine", vector_column_name="vector", replace=True)
                log.info("ANN index built over %d rows", n_rows)
            except Exception as e:
                log.warning("ANN index build failed (brute-force search still works): %s", e)

    dt = time.time() - t_start
    log.info("Done: %d chunks from %d file(s) in %.1fs%s", total_chunks, len(todo) - len(failures), dt,
             f"; {len(failures)} failed" if failures else "")
    for p, err in failures:
        log.info("  failed: %s (%s)", p, err)


# ---------------------------------------------------------------------------
# `search` command
# ---------------------------------------------------------------------------

def _apply_metric(q, metric: str):
    for name in ("distance_type", "metric"):
        if hasattr(q, name):
            return getattr(q, name)(metric)
    return q


def _fts_query_text(q: str) -> str:
    # Keep tokens like 5G-GUTI / T3512 / N1 intact; drop query-syntax characters
    return re.sub(r"[\"'():^~*\[\]{}!\\/]+", " ", q).strip()


def build_where(args) -> str | None:
    conds = []
    if args.spec:
        conds.append("(" + " OR ".join(f"spec = {_sql_str(s)}" for s in args.spec) + ")")
    if args.release:
        conds.append("(" + " OR ".join(f"release = {int(r)}" for r in args.release) + ")")
    if args.clause:
        conds.append(f"clause LIKE {_sql_str(args.clause + '%')}")
    return " AND ".join(conds) if conds else None


def cmd_search(args) -> None:
    db_path = Path(args.db).expanduser().resolve()
    meta = load_index_meta(db_path)
    if not meta:
        raise SystemExit(f"No index metadata in {db_path}. Run `index` first.")
    preset_name = meta.get("preset", "")
    preset = PRESETS.get(preset_name) or ModelPreset(meta["model"], meta["dim"], meta.get("query_prompt", ""))
    device = pick_device(args.device)
    dim = meta["dim"] if meta["dim"] != preset.dim else None
    model = load_embedder(preset, device, dim, max_seq=512)
    _, tbl = open_table(db_path, meta["dim"], create=False)

    where = build_where(args)
    pool = max(args.k * 4, 20)

    qvec = encode(model, [meta.get("query_prompt", preset.query_prompt) + args.query], 1)[0]
    vq = _apply_metric(tbl.search(qvec, vector_column_name="vector"), "cosine").limit(pool)
    if where:
        try:
            vq = vq.where(where, prefilter=True)
        except TypeError:
            vq = vq.where(where)
    vec_hits = vq.to_list()

    fts_hits = []
    if not args.no_hybrid:
        try:
            fq = tbl.search(_fts_query_text(args.query), query_type="fts").limit(pool)
            if where:
                fq = fq.where(where)
            fts_hits = fq.to_list()
        except Exception as e:
            log.debug("FTS unavailable: %s", e)

    # Reciprocal-rank fusion
    fused: dict[str, dict] = {}
    for hits, label in ((vec_hits, "vec"), (fts_hits, "fts")):
        for rank, h in enumerate(hits):
            e = fused.setdefault(h["id"], {"hit": h, "score": 0.0, "via": []})
            e["score"] += 1.0 / (60 + rank)
            e["via"].append(label)
    ranked = sorted(fused.values(), key=lambda e: e["score"], reverse=True)

    if args.rerank and ranked:
        from sentence_transformers import CrossEncoder
        cand = ranked[:pool]
        ce = CrossEncoder(args.reranker, device=device, max_length=1024)
        scores = ce.predict([(args.query, f"{e['hit']['context']}\n\n{e['hit']['text']}") for e in cand],
                            batch_size=16, show_progress_bar=False)
        for e, s in zip(cand, scores):
            e["score"] = float(s)
        ranked = sorted(cand, key=lambda e: e["score"], reverse=True)

    results = ranked[:args.k]
    if args.json:
        out = [{k: v for k, v in e["hit"].items() if k not in ("vector",) and not k.startswith("_")}
               | {"score": e["score"], "matched_by": e["via"]} for e in results]
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return
    if not results:
        print("No results.")
        return
    for i, e in enumerate(results, 1):
        h = e["hit"]
        pages = f"p.{h['page_start']}" + (f"-{h['page_end']}" if h["page_end"] != h["page_start"] else "")
        print(f"\n[{i}] {h['context']}")
        print(f"    {h['source_file']}  {pages}  score={e['score']:.4f}  via={'+'.join(e['via'])}")
        snippet = re.sub(r"\s+", " ", h["text"])
        print("    " + (snippet[:args.snippet] + ("…" if len(snippet) > args.snippet else "")))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_models(_args) -> None:
    for name, p in PRESETS.items():
        print(f"{name:15s} {p.hf_id:32s} dim={p.dim:<5d} {p.note}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Embed and search 3GPP specification PDFs locally.")
    ap.add_argument("-v", "--verbose", action="store_true")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("index", help="Parse, chunk and embed PDFs into a LanceDB index")
    pi.add_argument("inputs", nargs="+", help="PDF files and/or directories (searched recursively)")
    pi.add_argument("--db", default="./Data/3gpp_index", help="Index directory (default: ./Data/3gpp_index)")
    pi.add_argument("--model", default="qwen3-0.6b",
                    help=f"Preset ({', '.join(PRESETS)}) or any sentence-transformers model id")
    pi.add_argument("--dim", type=int, default=None,
                    help="Truncate embeddings (Matryoshka), e.g. 512 or 256, to save space")
    pi.add_argument("--device", default="auto", help="auto | cuda | mps | cpu")
    pi.add_argument("--batch-size", type=int, default=None)
    pi.add_argument("--max-tokens", type=int, default=512, help="Max tokens per chunk incl. header")
    pi.add_argument("--overlap", type=int, default=64, help="Paragraph overlap budget in tokens")
    pi.add_argument("--parser", choices=["pymupdf4llm", "pymupdf"], default="pymupdf4llm",
                    help="pymupdf4llm keeps tables as Markdown; pymupdf is faster")
    pi.add_argument("--margin", type=float, default=36.0,
                    help="Points to crop from top and bottom of each page (headers/footers)")
    pi.add_argument("--workers", type=int, default=max(1, min(4, (os.cpu_count() or 2) - 1)),
                    help="Parallel PDF parser processes (0 = parse in main process)")
    pi.add_argument("--keep-boilerplate", action="store_true",
                    help="Keep Foreword / IPR / Change history sections")
    pi.add_argument("--ann-index", action="store_true",
                    help="Build an ANN vector index (only useful for very large corpora)")
    pi.add_argument("--rebuild", action="store_true", help="Delete and rebuild the index")
    pi.add_argument("--dry-run", action="store_true", help="Parse and chunk only; no embedding")
    pi.add_argument("--dump-chunks", default=None, help="Write chunks to this JSONL file")
    pi.set_defaults(func=cmd_index)

    ps = sub.add_parser("search", help="Query an existing index")
    ps.add_argument("query")
    ps.add_argument("--db", default="./3gpp_index")
    ps.add_argument("-k", type=int, default=8)
    ps.add_argument("--spec", action="append", help="Filter by spec number, e.g. 24.501 (repeatable)")
    ps.add_argument("--release", action="append", type=int, help="Filter by release (repeatable)")
    ps.add_argument("--clause", default=None, help="Filter by clause prefix, e.g. 5.5.1")
    ps.add_argument("--no-hybrid", action="store_true", help="Vector search only")
    ps.add_argument("--rerank", action="store_true", help="Rerank with a local cross-encoder")
    ps.add_argument("--reranker", default=DEFAULT_RERANKER)
    ps.add_argument("--device", default="auto")
    ps.add_argument("--snippet", type=int, default=400)
    ps.add_argument("--json", action="store_true")
    ps.set_defaults(func=cmd_search)

    pm = sub.add_parser("models", help="List model presets")
    pm.set_defaults(func=cmd_models)

    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    args.func(args)


if __name__ == "__main__":
    main()
