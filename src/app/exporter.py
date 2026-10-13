"""Export the library as a CSV or Markdown reading report."""

from __future__ import annotations

import csv
import logging
from datetime import date
from pathlib import Path
from typing import Callable, Sequence

from src.models import Book, InvalidOperationError, StorageError

logger = logging.getLogger(__name__)

CSV_FIELDS = [
    "id", "title", "author", "genre", "status", "total_page",
    "current_page", "rating", "finish_date", "notes",
]


def export_csv(books: Sequence[Book], path: Path) -> None:
    """Write all books to a CSV file.

    Raises:
        StorageError: if the file cannot be written.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for book in books:
                data = book.to_dict()
                writer.writerow(
                    {f: "" if data[f] is None else data[f]
                     for f in CSV_FIELDS}
                )
    except OSError as exc:
        raise StorageError(f"Could not write {path}: {exc}") from exc
    logger.info("Exported %d book(s) to %s", len(books), path)


def _md_cell(text: str) -> str:
    """Make text safe to place inside a Markdown table cell."""
    return text.replace("|", "\\|").replace("\n", " ")


def export_markdown(books: Sequence[Book], path: Path) -> None:
    """Write a Markdown reading report.

    Raises:
        StorageError: if the file cannot be written.
    """
    lines = [
        "# Reading Report",
        "",
        f"Generated on {date.today().isoformat()} - {len(books)} book(s)",
        "",
        "| ID | Title | Author | Genre | Status | Progress | Rating "
        "| Finished | Notes |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for book in books:
        rating = f"{book.rating}/5" if book.rating else "-"
        finished = book.finish_date.isoformat() if book.finish_date else "-"
        cells = [
            str(book.id), _md_cell(book.title), _md_cell(book.author),
            _md_cell(book.genre), book.status.value,
            f"{book.current_page}/{book.total_page}", rating, finished,
            _md_cell(book.notes),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError as exc:
        raise StorageError(f"Could not write {path}: {exc}") from exc
    logger.info("Exported %d book(s) to %s", len(books), path)


EXPORTERS: dict[str, Callable[[Sequence[Book], Path], None]] = {
    "csv": export_csv,
    "md": export_markdown,
}


def export_books(books: Sequence[Book], path: Path, fmt: str) -> None:
    """Export books in the given format ('csv' or 'md').

    Raises:
        InvalidOperationError: if the format is not supported.
    """
    exporter = EXPORTERS.get(fmt)
    if exporter is None:
        supported = ", ".join(EXPORTERS)
        raise InvalidOperationError(
            f"Unsupported format '{fmt}'. Choose one of: {supported}."
        )
    exporter(books, path)
