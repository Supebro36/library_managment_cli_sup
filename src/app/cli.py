"""Command-line menu interface for the Personal Library app."""

from __future__ import annotations

import logging
from typing import Callable, Optional, Sequence

from src.app.exporter import export_books
from src.app.library import Library
from src.config import APP_TITLE, EXPORT_DIR
from src.models import Book, InvalidBookDataError, LibraryError, Status

logger = logging.getLogger(__name__)

Handler = Callable[[Library], None]


# ----- input helpers ---------------------------------------------------
def prompt_text(label: str) -> str:
    """Ask until the user types a non-empty string."""
    while True:
        value = input(f"{label}: ").strip()
        if value:
            return value
        print("  This field cannot be empty.")


def prompt_int(
    label: str,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> int:
    """Ask until the user types a whole number within the given bounds."""
    while True:
        raw = input(f"{label}: ").strip()
        try:
            number = int(raw)
        except ValueError:
            print("  Please enter a whole number.")
            continue
        too_small = minimum is not None and number < minimum
        too_big = maximum is not None and number > maximum
        if too_small or too_big:
            print(f"  Value must be between {minimum} and {maximum}.")
            continue
        return number


def prompt_status(label: str) -> Status:
    """Ask until the user types a valid status."""
    options = "/".join(s.value for s in Status)
    while True:
        try:
            return Status.parse(input(f"{label} ({options}): "))
        except InvalidBookDataError as exc:
            print(f"  {exc}")


# ----- output helpers --------------------------------------------------
def _progress_text(book: Book) -> str:
    """Short description of progress for the table."""
    if book.status is Status.READING:
        return (
            f"{book.current_page}/{book.total_page} "
            f"({book.progress_percent}%)"
        )
    if book.status is Status.FINISHED and book.finish_date:
        return f"done {book.finish_date.isoformat()}"
    return "-"


def print_books(books: Sequence[Book]) -> None:
    """Print books as an aligned table."""
    if not books:
        print("No books found.")
        return
    header = (
        f"{'ID':<4}{'Title':<26}{'Author':<18}{'Genre':<12}"
        f"{'Status':<10}{'Rating':<8}{'Progress':<22}Notes"
    )
    print(header)
    print("-" * len(header))
    for b in books:
        rating = f"{b.rating}/5" if b.rating else "-"
        notes = (b.notes[:22] + "...") if len(b.notes) > 22 else b.notes
        print(
            f"{b.id:<4}{b.title[:24]:<26}{b.author[:16]:<18}"
            f"{b.genre[:10]:<12}{b.status.value:<10}{rating:<8}"
            f"{_progress_text(b):<22}{notes or '-'}"
        )


# ----- menu actions ----------------------------------------------------
def add_book(library: Library) -> None:
    """Menu action: add a new book."""
    title = prompt_text("Title")
    author = prompt_text("Author")
    genre = prompt_text("Genre")
    pages = prompt_int("Total pages", minimum=1)
    status = prompt_status("Status")
    current = 0
    if status is Status.READING:
        current = prompt_int("Current page", 0, pages)
    book = library.add_book(title, author, genre, pages, status, current)
    print(f"Added '{book.title}' with id {book.id}.")


def view_books(library: Library) -> None:
    """Menu action: list books with optional filters."""
    raw_status = input("Filter by status (blank = any): ").strip()
    genre = input("Filter by genre (blank = any): ").strip()
    status = Status.parse(raw_status) if raw_status else None
    print_books(library.list_books(status=status, genre=genre or None))


def update_progress(library: Library) -> None:
    """Menu action: update the current page."""
    book_id = prompt_int("Book id")
    book = library.get_book(book_id)
    page = prompt_int(f"Current page (0-{book.total_page})", 0,book.total_page)
    library.update_progress(book_id, page)
    print("Progress updated.")
    if book.status is Status.FINISHED:
        print(f"You reached the last page of this book '{book.title}'.... now it marked as finished !")


def start_reading(library: Library) -> None:
    """Menu action: begin reading a to-read book."""
    book = library.start_reading(prompt_int("Book id"))
    print(f"'{book.title}' is now marked as reading.")


def finish_book(library: Library) -> None:
    """Menu action: mark a book as finished."""
    book = library.mark_finished(prompt_int("Book id"))
    print(f"Finished '{book.title}' on {book.finish_date}. Well done!")


def remove_book(library: Library) -> None:
    """Menu action: delete a book after confirmation."""
    book = library.get_book(prompt_int("Book id"))
    answer = input(f"Remove '{book.title}'? (y/N): ").strip().lower()
    if answer == "y":
        library.remove_book(book.id)
        print("Book removed.")
    else:
        print("Cancelled.")


def search_books(library: Library) -> None:
    """Menu action: search by title or author."""
    print_books(library.search(prompt_text("Search text")))


def rate_book(library: Library) -> None:
    """Menu action: rate a finished book from 1 to 5."""
    book_id = prompt_int("Book id")
    rating = prompt_int("Rating (1-5)", 1, 5)
    book = library.rate_book(book_id, rating)
    print(f"Rated '{book.title}' {book.rating}/5.")


def edit_notes(library: Library) -> None:
    """Menu action: add, replace or clear a book's notes."""
    book = library.get_book(prompt_int("Book id"))
    if book.notes:
        print(f"Current notes: {book.notes}")
    text = input("New notes (blank to clear): ")
    library.set_notes(book.id, text)
    print("Notes saved.")


def show_details(library: Library) -> None:
    """Menu action: show every field of one book."""
    book = library.get_book(prompt_int("Book id"))
    rating = f"{book.rating}/5" if book.rating else "not rated"
    print(f"Title:     {book.title}")
    print(f"Author:    {book.author}")
    print(f"Genre:     {book.genre}")
    print(f"Status:    {book.status.value}")
    print(f"Progress:  {_progress_text(book)}")
    print(f"Rating:    {rating}")
    print(f"Notes:     {book.notes or '-'}")


def export_report(library: Library) -> None:
    """Menu action: export the collection as CSV or Markdown."""
    fmt = input("Format - csv or md (blank = md): ").strip().lower() or "md"
    path = EXPORT_DIR / f"reading_report.{fmt}"
    export_books(library.list_books(), path, fmt)
    print(f"Report saved to {path}")


def show_statistics(library: Library) -> None:
    """Menu action: print collection statistics."""
    stats = library.statistics()
    print(f"Total books:              {stats.total_books}")
    print(f"Finished this year:       {stats.finished_this_year}")
    print(f"Avg pages per finished:   {stats.avg_pages_per_finished:.1f}")
    print(f"Favorite genre:           {stats.favorite_genre or 'n/a'}")


MENU: dict[str, tuple[str, Handler]] = {
    "1": ("Add a book", add_book),
    "2": ("View books", view_books),
    "3": ("Update reading progress", update_progress),
    "4": ("Start reading a book", start_reading),
    "5": ("Mark a book as finished", finish_book),
    "6": ("Remove a book", remove_book),
    "7": ("Search by title/author", search_books),
    "8": ("View statistics", show_statistics),
    "9": ("Rate a finished book", rate_book),
    "10": ("Add/edit notes", edit_notes),
    "11": ("View book details", show_details),
    "12": ("Export report (CSV/Markdown)", export_report),
}


def run(library: Library) -> None:
    """Run the interactive menu loop until the user exits."""
    print(f"\n=== {APP_TITLE} ===")
    while True:
        print()
        for key, (label, _) in MENU.items():
            print(f"  {key}. {label}")
        print("  0. Exit")
        choice = input("Choose an option: ").strip()
        if choice == "0":
            print("Goodbye!")
            return
        entry = MENU.get(choice)
        if entry is None:
            print("Invalid option, please try again.")
            continue
        try:
            entry[1](library)
        except LibraryError as exc:
            logger.warning("Action %s failed: %s", choice, exc)
            print(f"Error: {exc}")
