import os
from pathlib import Path

BASE_DIR = Path(os.getenv("DATA_BASE_DIR", "data"))
CLEAN_DIR = BASE_DIR / "clean"

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "mtf_db"),
    "user": os.getenv("DB_USER", "bseetharaman"),
}
_db_password = os.getenv("DB_PASSWORD")
if _db_password:
    DB_CONFIG["password"] = _db_password

_db_sslmode = os.getenv("DB_SSLMODE")
if _db_sslmode:
    DB_CONFIG["sslmode"] = _db_sslmode
