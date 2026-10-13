"""Saving and Loading books json."""
from __future__ import annotations

import logging
import json
from pathlib import Path
from src.models import Book,StorageError,InvalidBookDataError

logger=logging.getLogger(__name__)

class JsonStorage:
    """Store books according to it's relevant file."""

    def __init__(self,path:Path)->None:
        self._path = Path(path)

    def load(self)->list[Book]:
        """Load books from file."""
        if not self._path.exists():
            logger.info("No data file at %s ; starting empty",self._path)
            return []
        try:
            text=self._path.read_text(encoding="utf-8")
            if not text.strip():
                return[]
            raw=json.loads(text)
        except(OSError,json.JSONDecodeError) as exc:
            logger.error("Failed to read %s: %s", self._path, exc)
            raise StorageError(
                f"Could not read {self._path}: {exc}"
            ) from exc
        if not isinstance(raw, list):
            raise StorageError(f"{self._path} must contain a JSON list.")
        try:
            books = [Book.from_dict(item) for item in raw]
        except InvalidBookDataError as exc:
            logger.error("Corrupt data in %s: %s", self._path, exc)
            raise StorageError(f"{self._path} is corrupt: {exc}") from exc
        logger.info("Loaded %d book(s) from %s", len(books), self._path)
        return books

    def save(self, books: list[Book]) -> None:
        """Write books to disk (via a temp file so a crash can't corrupt)."""
        payload = [book.to_dict() for book in books]
        tmp_path = self._path.with_suffix(".tmp")
        try:
            tmp_path.write_text(
                json.dumps(payload, indent=2), encoding="utf-8"
            )
            tmp_path.replace(self._path)
        except OSError as exc:
            logger.error("Failed to write %s: %s", self._path, exc)
            raise StorageError(
                f"Could not write {self._path}: {exc}"
            ) from exc
        logger.debug("Saved %d book(s) to %s", len(books), self._path)