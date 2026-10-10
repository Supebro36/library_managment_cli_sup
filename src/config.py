"""Application Settings. """

import os
from pathlib import Path

PROJECT_ROOT:Path=Path(__file__).resolve().parent.parent

DATA_DIR: Path=Path(os.environ.get("LIBRARY_HOME",PROJECT_ROOT))

DATA_FILE:Path=DATA_DIR/"data.json"
EXPORT_DIR:Path=DATA_DIR/"export"
LOG_FILE:Path=DATA_DIR/"library.log"
APP_TITLE:str="PERSONAL LIBRARY & READING TRACKER📖"