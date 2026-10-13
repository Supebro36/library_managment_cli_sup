"""Entry point: run with `python -m src` from the project root."""


from src.app.cli import run
from src.app.library import Library
from src.app.storage import JsonStorage
from src.config import DATA_FILE
from src.logger import setup_logging

def main() -> None:
    setup_logging()
    run(Library(JsonStorage(DATA_FILE)))

if __name__ == "__main__":
    main()

