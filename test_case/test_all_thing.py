"""All tests for the Personal Library app.

Run from the project root:  pytest
"""

import csv
import logging
import sys
from datetime import date

import pytest

from src.app import cli
from src.app.exporter import export_books
from src.app.library import Library
from src.app.storage import JsonStorage
from src.logger import setup_logging
from src.models import (
    Book, BookNotFoundError, InvalidBookDataError,
    InvalidOperationError, Status, StorageError,
)


# ===== shared helpers and fixtures =====================================
def make_book(**overrides):
    """Build a valid Book, allowing field overrides."""
    data = dict(book_id=1, title="Dune", author="Frank Herbert",genre="sci-fi", total_page=500)
    data.update(overrides)
    return Book(**data)


def feed(monkeypatch, answers):
    """Make input() return the given answers one by one."""
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(it))


def write(tmp_path, text):
    """Create data.json with the given text and return its path."""
    path = tmp_path / "data.json"
    path.write_text(text)
    return path


@pytest.fixture
def library(tmp_path):
    """An empty library backed by a temporary file."""
    return Library(JsonStorage(tmp_path / "data.json"))


@pytest.fixture
def books():
    """Two sample books: one finished and rated, one to-read."""
    return [Book(1, "Dune", "Frank Herbert", "Sci-Fi", 500,
                 Status.FINISHED, rating=5, notes="Great | epic"),
            Book(2, "Emma", "Jane Austen", "Romance", 300)]


@pytest.fixture(autouse=True)
def clean_logger():
    """Remove log handlers added during a test."""
    yield
    logger = logging.getLogger("src")
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


# ===== models: Book and Status =========================================
def test_new_book_defaults():
    book = make_book()
    assert (book.status, book.current_page, book.finish_date) == (Status.TO_READ, 0, None)
    assert book.genre == "Sci-Fi"


@pytest.mark.parametrize("field", ["title", "author", "genre"])
def test_blank_text_fields_rejected(field):
    with pytest.raises(InvalidBookDataError):
        make_book(**{field: "   "})


@pytest.mark.parametrize("pages", [0, -5, "100", None, True])
def test_invalid_total_page(pages):
    with pytest.raises(InvalidBookDataError):
        make_book(total_page=pages)


def test_status_parse():
    assert Status.parse("  READING ") is Status.READING
    with pytest.raises(InvalidBookDataError):
        Status.parse("abandoned")


def test_update_progress_requires_reading_status():
    with pytest.raises(InvalidOperationError):
        make_book().update_progress(10)


def test_update_progress_bounds():
    book = make_book(status=Status.READING)
    book.update_progress(250)
    assert book.progress_percent == 50
    for bad in (501, -1):
        with pytest.raises(InvalidBookDataError):
            book.update_progress(bad)


def test_mark_finished_records_date():
    book = make_book(status=Status.READING, current_page=10)
    book.mark_finished()
    assert (book.status, book.current_page, book.finish_date) == (
        Status.FINISHED, 500, date.today())


@pytest.mark.parametrize("action", ["mark_finished", "start_reading"])
def test_finished_book_rejects_further_changes(action):
    book = make_book()
    book.mark_finished()
    with pytest.raises(InvalidOperationError):
        getattr(book, action)()


def test_dict_round_trip_keeps_rating_and_notes():
    book = make_book(status=Status.FINISHED, finish_date=date(2026, 1, 5),
                     rating=5, notes="Loved it")
    clone = Book.from_dict(book.to_dict())
    assert clone.to_dict() == book.to_dict()
    assert (clone.rating, clone.notes) == (5, "Loved it")


def test_from_dict_missing_key():
    with pytest.raises(InvalidBookDataError):
        Book.from_dict({"id": 1, "title": "x"})


def test_old_records_without_rating_still_load():
    data = make_book().to_dict()
    del data["rating"], data["notes"]
    book = Book.from_dict(data)
    assert (book.rating, book.notes) == (None, "")


def test_rating_only_for_finished_books():
    book = make_book()
    with pytest.raises(InvalidOperationError):
        book.set_rating(4)
    book.mark_finished()
    book.set_rating(4)
    assert book.rating == 4


@pytest.mark.parametrize("value", [0, 6, -1, "5", 4.5, True, None])
def test_invalid_rating_values(value):
    book = make_book()
    book.mark_finished()
    with pytest.raises(InvalidBookDataError):
        book.set_rating(value)


def test_constructor_rejects_rating_on_unfinished_book():
    with pytest.raises(InvalidBookDataError):
        make_book(rating=5)


def test_notes_trimmed_cleared_and_validated():
    book = make_book()
    book.set_notes("  great read  ")
    assert book.notes == "great read"
    book.set_notes("")
    assert book.notes == ""
    for bad in (123, "x" * 1001):
        with pytest.raises(InvalidBookDataError):
            book.set_notes(bad)


# ===== storage: JsonStorage ============================================
@pytest.mark.parametrize("content", [None, ""])  # None = file does not exist
def test_missing_or_empty_file_gives_empty_list(tmp_path, content):
    path = tmp_path / "nope.json" if content is None else write(tmp_path, content)
    assert JsonStorage(path).load() == []


def test_save_then_load(tmp_path):
    storage = JsonStorage(tmp_path / "data.json")
    book = Book(1, "Dune", "Frank Herbert", "Sci-Fi", 500, Status.READING, 40)
    storage.save([book])
    loaded = storage.load()
    assert len(loaded) == 1 and loaded[0].to_dict() == book.to_dict()


@pytest.mark.parametrize("content", ["{not valid json", '{"a": 1}', '[{"id": 1}]'])
def test_corrupt_wrong_or_bad_data_raises(tmp_path, content):
    with pytest.raises(StorageError):
        JsonStorage(write(tmp_path, content)).load()


# ===== library: business logic =========================================
def test_add_and_get(library):
    book = library.add_book("Dune", "Frank Herbert", "Sci-Fi", 500)
    assert library.get_book(book.id) is book
    assert len(library) == 1


def test_ids_are_unique_after_removal(library):
    first = library.add_book("A", "X", "G", 10)
    second = library.add_book("B", "X", "G", 10)
    library.remove_book(first.id)
    assert library.add_book("C", "X", "G", 10).id not in (second.id,)


@pytest.mark.parametrize("method", ["get_book", "remove_book"])
def test_missing_book(library, method):
    with pytest.raises(BookNotFoundError):
        getattr(library, method)(99)


def test_filter_by_status_and_genre(library):
    library.add_book("A", "X", "Fantasy", 10)
    library.add_book("B", "X", "Fantasy", 10, Status.FINISHED)
    library.add_book("C", "X", "Horror", 10, Status.FINISHED)
    assert len(library.list_books(status=Status.FINISHED)) == 2
    assert len(library.list_books(genre="fantasy")) == 2
    both = library.list_books(status=Status.FINISHED, genre="FANTASY")
    assert [b.title for b in both] == ["B"]


def test_search_is_case_insensitive_and_partial(library):
    library.add_book("The Hobbit", "J.R.R. Tolkien", "Fantasy", 300)
    library.add_book("Emma", "Jane Austen", "Romance", 400)
    assert [b.title for b in library.search("hob")] == ["The Hobbit"]
    assert [b.title for b in library.search("AUSTEN")] == ["Emma"]
    assert library.search("zzz") == []


def test_reading_workflow(library):
    book = library.add_book("Dune", "Frank Herbert", "Sci-Fi", 500)
    with pytest.raises(InvalidOperationError):
        library.update_progress(book.id, 10)
    library.start_reading(book.id)
    library.update_progress(book.id, 100)
    assert book.current_page == 100
    library.mark_finished(book.id)
    assert book.status is Status.FINISHED and book.finish_date is not None


def test_statistics_empty(library):
    stats = library.statistics()
    assert (stats.total_books, stats.avg_pages_per_finished,
            stats.favorite_genre) == (0, 0.0, None)


def test_statistics_values(library):
    for title, genre, pages, status in [
            ("A", "Fantasy", 100, Status.FINISHED), ("B", "Fantasy", 300, Status.FINISHED),
            ("C", "Horror", 200, Status.FINISHED), ("D", "Horror", 200, Status.TO_READ)]:
        library.add_book(title, "X", genre, pages, status)
    stats = library.statistics()
    assert stats.total_books == 4 and stats.finished_this_year == 3
    assert stats.avg_pages_per_finished == pytest.approx(200.0)
    assert stats.favorite_genre == "Fantasy"


def test_data_rating_and_notes_persist(tmp_path):
    path = tmp_path / "data.json"
    first = Library(JsonStorage(path))
    book = first.add_book("Dune", "Frank Herbert", "Sci-Fi", 500)
    first.mark_finished(book.id)
    first.rate_book(book.id, 5)
    first.set_notes(book.id, "Masterpiece")
    again = Library(JsonStorage(path))
    assert [b.title for b in again.list_books()] == ["Dune"]
    saved = again.get_book(book.id)
    assert (saved.rating, saved.notes) == (5, "Masterpiece")


def test_rate_unfinished_book_fails(library):
    book = library.add_book("Dune", "Frank Herbert", "Sci-Fi", 500)
    with pytest.raises(InvalidOperationError):
        library.rate_book(book.id, 3)


def test_events_are_logged(library, caplog):
    with caplog.at_level("INFO", logger="src"):
        book = library.add_book("Dune", "Frank Herbert", "Sci-Fi", 500)
        library.remove_book(book.id)
    messages = " ".join(r.getMessage() for r in caplog.records)
    assert "Added book" in messages and "Removed book" in messages


# ===== logging setup ===================================================
def test_setup_writes_to_file(tmp_path):
    log_file = tmp_path / "app.log"
    setup_logging(log_file)
    logging.getLogger("src.test").info("hello log")
    assert "hello log" in log_file.read_text(encoding="utf-8")


def test_setup_twice_adds_one_handler(tmp_path):
    setup_logging(tmp_path / "a.log")
    setup_logging(tmp_path / "b.log")
    assert len(logging.getLogger("src").handlers) == 1


def test_unwritable_log_file_does_not_crash(tmp_path):
    setup_logging(tmp_path / "missing_dir" / "app.log")
    logging.getLogger("src.test").info("still fine")


# ===== exporter: CSV / Markdown ========================================
def test_csv_export(tmp_path, books):
    path = tmp_path / "out" / "report.csv"
    export_books(books, path, "csv")
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [r["title"] for r in rows] == ["Dune", "Emma"]
    assert (rows[0]["rating"], rows[1]["rating"]) == ("5", "")


def test_markdown_export_escapes_pipes(tmp_path, books):
    path = tmp_path / "report.md"
    export_books(books, path, "md")
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# Reading Report")
    for expected in ("| Dune |", "Great \\| epic", "5/5"):
        assert expected in text


def test_unsupported_format(tmp_path, books):
    with pytest.raises(InvalidOperationError):
        export_books(books, tmp_path / "x.pdf", "pdf")


def test_unwritable_path_raises_storage_error(tmp_path, books):
    blocker = tmp_path / "file"
    blocker.write_text("i am a file, not a folder")
    with pytest.raises(StorageError):
        export_books(books, blocker / "report.csv", "csv")


# ===== CLI (driven by scripted keyboard input) =========================
def test_prompt_helpers_retry_on_bad_input(monkeypatch, capsys):
    feed(monkeypatch, ["abc", "0", "7"])
    assert cli.prompt_int("n", minimum=1) == 7
    assert "whole number" in capsys.readouterr().out
    feed(monkeypatch, ["  ", "hello"])
    assert cli.prompt_text("x") == "hello"
    feed(monkeypatch, ["nope", "Reading"])
    assert cli.prompt_status("s").value == "reading"


def test_full_session(monkeypatch, library, capsys):
    feed(monkeypatch, [
        "1", "Dune", "Frank Herbert", "sci-fi", "500", "reading", "50",
        "3", "1", "120", "7", "dune", "5", "1", "8",
        "6", "1", "y", "0"])
    cli.run(library)
    out = capsys.readouterr().out
    for text in ("Added 'Dune'", "Progress updated", "Finished 'Dune'", "Book removed"):
        assert text in out
    assert len(library) == 0


def test_errors_do_not_crash_menu(monkeypatch, library, capsys):
    feed(monkeypatch, ["5", "42", "99", "0"])
    cli.run(library)
    out = capsys.readouterr().out
    assert "Error: No book with id 42" in out and "Invalid option" in out


def test_view_with_filters(monkeypatch, library, capsys):
    library.add_book("Emma", "Jane Austen", "Romance", 300)
    feed(monkeypatch, ["2", "to-read", "romance", "0"])
    cli.run(library)
    assert "Emma" in capsys.readouterr().out


def test_rate_notes_details_flow(monkeypatch, library, capsys):
    library.add_book("Dune", "Frank Herbert", "Sci-Fi", 500)
    feed(monkeypatch, ["5", "1", "9", "1", "4",
                       "10", "1", "Slow start, great end", "11", "1", "0"])
    cli.run(library)
    out = capsys.readouterr().out
    for text in ("Rated 'Dune' 4/5", "Notes saved", "Slow start, great end"):
        assert text in out


def test_export_menu(monkeypatch, library, tmp_path, capsys):
    library.add_book("Dune", "Frank Herbert", "Sci-Fi", 500)
    monkeypatch.setattr(cli, "EXPORT_DIR", tmp_path)
    feed(monkeypatch, ["12", "csv", "12", "", "12", "pdf", "0"])
    cli.run(library)
    assert (tmp_path / "reading_report.csv").exists()
    assert (tmp_path / "reading_report.md").exists()
    assert "Unsupported format" in capsys.readouterr().out


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
