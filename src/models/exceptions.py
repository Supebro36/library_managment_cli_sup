<<<<<<< HEAD
"""Custom exceptions for the Personal Library app."""


class LibraryError(Exception):
    """Base class for every error this app raises on purpose."""


class InvalidBookDataError(LibraryError):
    """A book field has an invalid value."""


class InvalidRatingError(InvalidBookDataError):
    """A rating is not a whole number from 1 to 5."""


class InvalidOperationError(LibraryError):
    """The action is not allowed in the book's current state."""


class BookNotFoundError(LibraryError):
    """No book exists with the requested id."""


class StorageError(LibraryError):
    """The data file could not be read or written."""
=======
class InvalidBookDataError(Exception):
    """A book field has an invalid value."""
    pass

class InvalidOperationError(Exception):
    """The action is not allowed in the book's current state."""
    pass

class InvalidRatingError(Exception):
    """A rating is not a whole number from 1 to 5."""
    pass

class BookNotFoundError(Exception):
    """No book exists with the requested id."""
    pass

class StorageError(Exception):
    """The data file could not be read or written."""
    pass

class LibraryError(Exception):
    """Base class for every error this app raises on purpose."""
    pass
>>>>>>> 2383e5a (day04: update the keywords)
