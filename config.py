from pathlib import Path

BASE_DIR = Path("data")
CLEAN_DIR = BASE_DIR / "clean"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "mtf_db",
    "user": "bseetharaman"
}