from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .embeddings import embed_text
from .qdrant_store import ensure_collection, upsert_points

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = PROJECT_ROOT / "rag" / "docs"


def _chunk_text(text: str, max_chars: int = 1400, overlap: int = 180) -> list[str]:
    paragraphs = [item.strip() for item in text.split("\n\n") if item.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
            continue
        if current:
            chunks.append(current)
        current = paragraph

    if current:
        chunks.append(current)

    if overlap <= 0 or len(chunks) <= 1:
        return chunks

    overlapped: list[str] = []
    previous_tail = ""
    for chunk in chunks:
        combined = f"{previous_tail}\n\n{chunk}".strip() if previous_tail else chunk
        overlapped.append(combined)
        previous_tail = chunk[-overlap:]
    return overlapped


def _metadata_for(path: Path) -> dict[str, Any]:
    relative = path.relative_to(DOCS_ROOT).as_posix()
    parts = path.relative_to(DOCS_ROOT).parts
    stem = path.stem

    doc_type = "knowledge"
    ticker = None
    if parts and parts[0] == "companies":
        doc_type = "company_note"
        ticker = stem.upper()
    elif "product" in stem or "project" in stem:
        doc_type = "product_overview"
    elif "portfolio" in stem:
        doc_type = "portfolio_methodology"
    elif "sector" in stem:
        doc_type = "sector_note"
    elif "disclaimer" in stem:
        doc_type = "disclaimer"

    return {
        "source": relative,
        "title": stem.replace("_", " ").title(),
        "doc_type": doc_type,
        "ticker": ticker,
        "language": "en",
    }


def _point_id(source: str, chunk_index: int, text: str) -> int:
    digest = hashlib.sha256(f"{source}:{chunk_index}:{text}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def iter_points(root: Path, *, embed: bool = True) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    paths = sorted([*root.rglob("*.md"), *root.rglob("*.txt")])
    for path in paths:
        text = path.read_text(encoding="utf-8")
        metadata = _metadata_for(path)
        for index, chunk in enumerate(_chunk_text(text)):
            payload = {
                **metadata,
                "chunk_index": index,
                "text": chunk,
            }
            point = {
                "id": _point_id(metadata["source"], index, chunk),
                "payload": payload,
            }
            if embed:
                point["vector"] = embed_text(chunk)
            points.append(point)
    return points


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Ingest local RAG docs into Qdrant Cloud.")
    parser.add_argument("--docs-root", default=str(DOCS_ROOT))
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root = Path(args.docs_root)
    points = iter_points(root, embed=not args.dry_run)
    print(json.dumps({"docs_root": str(root), "points": len(points)}, indent=2))

    if args.dry_run:
        return

    ensure_collection()
    for start in range(0, len(points), args.batch_size):
        batch = points[start : start + args.batch_size]
        upsert_points(batch)
        print(f"upserted {start + len(batch)}/{len(points)}")


if __name__ == "__main__":
    main()
