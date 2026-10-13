from __future__ import annotations

import logging

from src.models import BookNotFoundError,Book,Status

from src.app.storage import JsonStorage
from typing import Optional
from datetime import date

logger=logging.getLogger(__name__)


class Statistics:
    """Summary numbers about the collection."""

    def __init__(
        self,
        total_books: int,
        finished_this_year: int,
        avg_pages_per_finished: float,
        favorite_genre: Optional[str],
    ) -> None:
        self.total_books = total_books
        self.finished_this_year = finished_this_year
        self.avg_pages_per_finished = avg_pages_per_finished
        self.favorite_genre = favorite_genre


class Library:
    """A Collection of books that saves itself after every change."""

    def __init__(self,storage:JsonStorage):
        """Create a library and load existing books from storage."""
        self._storage= storage
        self._books:list[Book]=storage.load()
    
    def __len__(self)->int:
        """Number of Books in Library."""
        return len(self._books)

    def _next_id(self)->int:
        """Return an id higher than any existing id."""
        return max((book.id for book in self._books),default=0)+1

    def _save(self)->None:
        """Write the current state to storage ."""
        self._storage.save(self._books)

    def add_book(
        self,
        title:str,
        author:str,
        genre:str,
        total_page:int,
        status:Status=Status.TO_READ,
        current_page:int =0,
    )-> Book:
        """Create a book,add it to the collection and save ."""

        book=Book(
            self._next_id(),title,author,genre,total_page,status,current_page,
        )

        self._books.append(book)
        self._save()
        logger.info("Added book id=%d title =%r",book.id,book.title)
        return book

    def get_book(self,book_id:int)->Book:
        """Return the Book with id."""

        for book in self._books:
            if book.id==book_id:
                return book
        raise BookNotFoundError(f"No book with id {book_id} found.")

    def list_books(
            self,
            status:Optional[Status]=None,
            genre: Optional[str]=None,
    )->list[Book]:
        """Return Books, Optionally filtered by status or genre."""

        result=list(self._books)
        if status is not None:
            result=[b for b in result if b.status is status]
        if genre:
            wanted=genre.strip().casefold()
            result=[b for b in result if b.genre.casefold()==wanted]
        return result

    def search(self,query:str)->list[Book]:
        """Case-insensitive partial match on title or author."""
        magnifi=query.strip().casefold()
        return[
            b for b in self._books
            if magnifi in b.title.casefold() or magnifi in b.author.casefold()
        ]

    def remove_book(self,book_id:int)->Book:
        """Remove and return a book"""
        book=self.get_book(book_id)
        self._books.remove(book)
        self._save()
        logger.info("Removed book id=%d title=%r",book.id,book.title)
        return book

    def start_reading(self,book_id:int)-> Book:
        """set the current pages of a book that is being read."""
        book=self.get_book(book_id)
        book.start_reading()
        self._save()
        logger.info("Started reading id=%d",book.id)
        return book

    def update_progress(self,book_id:int,page:int)->Book:
        """Set the current pages of a book taht is being read."""
        book=self.get_book(book_id)
        book.update_progress(page)
        self._save()
        logger.info("progress id=%d page=%d",book.id,page)
        return book

    def mark_finished(self,book_id:int)-> Book:
        """mark a book as finsihed (record today's date)."""
        book=self.get_book(book_id)
        book.mark_finished()
        self._save()
        logger.info("Finished book's id=%d on %s",book.id,book.finish_date)
        return book

    def rate_book(self,book_id:int,rating:int)-> Book:
        """mark a book as finsihed (record today's date)."""
        book=self.get_book(book_id)
        book.set_rating(rating)
        self._save()
        logger.info("Rated book's id=%d rating=%d",book.id,rating)
        return book

    def set_notes(self, book_id: int, notes: str) -> Book:
        """Replace a book's notes/review text."""
        book = self.get_book(book_id)
        book.set_notes(notes)
        self._save()
        logger.info("Updated notes id=%d", book.id)
        return book

    def statistics(self) -> Statistics:
        """Compute collection statistics."""
        finished = [b for b in self._books if b.status is Status.FINISHED]
        this_year = date.today().year
        finished_this_year = sum(
            1 for b in finished
            if b.finish_date and b.finish_date.year == this_year
        )
        average = (
            sum(b.total_page for b in finished) / len(finished)
            if finished else 0.0
        )

        genre_counts = {}
        for b in finished:
            genre_counts[b.genre] = genre_counts.get(b.genre, 0) + 1

        favorite_genre = None
        highest = 0
        for genre, count in genre_counts.items():
            if count > highest:
                favorite_genre = genre
                highest = count

        return Statistics(
            total_books=len(self._books),
            finished_this_year=finished_this_year,
            avg_pages_per_finished=average,
            favorite_genre=favorite_genre,
        )
    