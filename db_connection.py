import sqlite3
import os

class DatabaseConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
            cls._instance._conn = None
            cls._instance._connect()
        return cls._instance

    def _connect(self):
        # Construim calea relativa catre folderul database
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, 'database', 'MEDICODE')
        
        try:
            self._conn = sqlite3.connect(db_path)
            # Activam suportul pentru Foreign Keys (optional, dar recomandat)
            self._conn.execute("PRAGMA foreign_keys = ON;")
            print("Conexiune stabilită cu succes către MEDICODE.")
        except sqlite3.Error as e:
            print(f"Eroare la conectare: {e}")

    @property
    def connection(self):
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            DatabaseConnection._instance = None
            print("Conexiune închisă.")