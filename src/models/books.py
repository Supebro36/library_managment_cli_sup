from __future__ import annotations

from enum import Enum

from datetime import date
from typing import Any,Optional

from src.models.exceptions import InvalidBookDataError,InvalidOperationError,InvalidRatingError



class Status(str,Enum):
    """Reading status of a book."""

    TO_READ="to-read"
    READING="reading"
    FINISHED="finished"

    @classmethod
    def parse(cls,value:str)->"Status":
        """Convert user text such as 'Reading' into Status. """
        try:
            return cls(str(value).strip().lower())
        except ValueError as exc:
            valid=",".join(s.value for s in cls)
            raise InvalidBookDataError(
                f"Invalid Status'{value}'. Choose one of :{valid}"
            )from exc

MIN_RATING=1
MAX_RATING=5
MAX_NOTES_LENGTH=1000

def _validate_rating(rating:Any)->int:
    """Ensure the rating """
    if type(rating) is not int :
        raise InvalidRatingError("Rating must be a whole number")
    if not MIN_RATING <= rating<=MAX_RATING:
        raise InvalidRatingError(
            f"Rating must be between {MIN_RATING}and{MAX_RATING}"
        )
    return rating


def _clean_notes(notes:Any)->str:
    """Return Stripped note text. Blank also allowed."""
    if not isinstance(notes,str):
        raise InvalidBookDataError("Notes must be text.")
    notes=notes.strip()
    if len(notes)>MAX_NOTES_LENGTH:
        raise InvalidBookDataError(
            f"Notes cannot exceed {MAX_NOTES_LENGTH} characters."
        )
    return notes


def _clean_text(value:Any , field:str)->str:
    """Return a Stripped , Non-empty String or raise an error ."""
    if not isinstance(value,str) or not value.strip():
        raise InvalidBookDataError(f"{field} cannot be empty.")
    return value.strip()


class Book:
    """ A class to represent a book in the library.

    Status, current page, finish date, rating and notes are kept private
    and can only be changed through methods, so a Book can never be in an
    invalid state.
    """
    def __init__(
            self,
            book_id:int,
            title:str,
            author:str,
            genre:str,
            total_page:int,
            status: Status=Status.TO_READ,
            current_page:int=0,
            finish_date:Optional[date]=None,
            rating:Optional[int]=None,
            notes:str="",
    )->None:
        """Create a Valid Book"""
        if type(total_page) is not int or total_page<=0:
                raise InvalidBookDataError(
                    "Total pages must be a whole number greater than 0."
            )
        self.id=book_id
        self.title=_clean_text(title, "Title")
        self.author=_clean_text(author, "Author")
        self.genre=_clean_text(genre, "Genre").title()
        self.total_page=total_page
        self._status=status
        self._current_page=0
        self._finish_date:Optional[date]=None

        if status is Status.READING:
            self._current_page=self._validate_page(current_page)
        elif status is Status.FINISHED:
            self._current_page= total_page
            self._finish_date=finish_date or date.today()

        self._rating:Optional[int]=None
        if rating is not None:
            if status is not Status.FINISHED:
                raise InvalidBookDataError(
                    "Only finished books can have rating."
                )
            self._rating=_validate_rating(rating)
        self._notes= _clean_notes(notes)


#-----------------Properties-----------------------------------------
    @property
    def status(self)->Status:
        """Get the reading status of the book."""
        return self._status

    @property
    def current_page(self)->int:
        """Get the current page number of the book."""
        return self._current_page

    @property
    def finish_date(self)-> Optional[date]:
        """Date the book was finished , or None ."""
        return self._finish_date

    @property
    def rating(self)->Optional[int]:
        """Star rating from 1-5 , or None if not rated ."""
        return self._rating

    @property
    def notes(self)->str:
        """Free-text notes or review ."""
        return self._notes
    @property
    def progress_percent(self)->int:
        """Reading progress as a whole-number percentage."""
        return int(self._current_page*100/self.total_page)

#-------------------Behaviour-----------------------------------------
    def _validate_page(self, page:int)->int:
        """Ensure that pages must be greater-than zero and less-than total pages. """
        if type(page) is not int :
            raise  InvalidBookDataError("Page must be a whole number.")
        if not 0<=page<= self.total_page:
            raise InvalidBookDataError (f"page must be between 0 and {self.total_page}")
        return page

    def start_reading(self)->None:
        """Move a To-read book into the reading status."""
        if self._status is Status.FINISHED:
            raise InvalidOperationError(f"'{self.title}' is already finished .")
        self._status=Status.READING

    def update_progress(self,page:int)->None:
        """Record the current status of the book."""
        if self._status is not Status.READING:
            raise InvalidOperationError(
                f"'{self.title}'is not marked as 'Reading'."
            )
        self._current_page=self._validate_page(page)

    def mark_finished(self,finished_on:Optional[date]=None)->None:
        """Mark the book as finished and record the finish date."""
        if self._status is Status.FINISHED:
            raise InvalidOperationError(f"'{self.title}' is already finished.")
        self._status=Status.FINISHED
        self._current_page=self.total_page
        self._finish_date= finished_on or date.today()

    def set_rating(self,rating:int)->None:
        """Rate a finished book from 1-5 stars."""
        if self._status is not Status.FINISHED:
            raise InvalidOperationError(
                f"'{self.title}' must be finished before it can be rated."
            )
        self._rating= _validate_rating(rating)

    def set_notes(self,notes:str)->None:
        """Replace the Notes/Review the text ."""
        self._notes=_clean_notes(notes)

    #----- serialisation ---------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "genre": self.genre,
            "total_page": self.total_page,
            "status": self._status.value,
            "current_page": self._current_page,
            "finish_date": (
                self._finish_date.isoformat() if self._finish_date else None
            ),
            "rating": self._rating,
            "notes": self._notes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Book":
        """Rebuild a Book from :meth:`to_dict` output."""
        try:
            raw_date = data.get("finish_date")
            return cls(
                book_id=int(data["id"]),
                title=data["title"],
                author=data["author"],
                genre=data["genre"],
                total_page=data["total_page"],
                status=Status.parse(data["status"]),
                current_page=data.get("current_page", 0),
                finish_date=(
                    date.fromisoformat(raw_date) if raw_date else None
                ),
                rating=data.get("rating"),
                notes=data.get("notes", ""),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidBookDataError(
                f"Corrupt book record: {exc!r}"
            ) from exc

    def __repr__(self) -> str:
        """Debug-friendly representation."""
        return f"Book(id={self.id}, title={self.title!r})"
