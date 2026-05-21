import sqlite3
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_database_path() -> Path:
    data_dir = get_project_root() / "data" / "database"
    data_dir.mkdir(parents=True, exist_ok=True)

    db_without_extension = data_dir / "MEDICODE"
    db_with_extension = data_dir / "MEDICODE.db"

    if db_without_extension.exists():
        return db_without_extension
    if db_with_extension.exists():
        return db_with_extension
    return db_without_extension


class DatabaseConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._conn = None
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        db_path = get_database_path()

        try:
            self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
            # Activam suportul pentru Foreign Keys (optional, dar recomandat)
            self._conn.execute("PRAGMA foreign_keys = ON;")
            print(f"Conexiune stabilita cu succes catre {db_path}.")
        except sqlite3.Error as e:
            print(f"Eroare la conectare: {e}")

    @property
    def connection(self):
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            DatabaseConnection._instance = None
            print("Conexiune inchisa.")
