import pytest
import sqlite3
from interfata import register_user


# Suprascriem conexiunea la BD pentru teste ca să folosească memoria RAM
@pytest.fixture(autouse=True)
def mock_db_connection(monkeypatch):
    def fake_connection():
        conn = sqlite3.connect(":memory:")  # BD temporară care se șterge la final
        conn.row_factory = sqlite3.Row
        # Creăm structura tabelului pentru test
        conn.execute("""
            CREATE TABLE Utilizatori (
                id_utilizator INTEGER PRIMARY KEY, cnp TEXT, nume TEXT, 
                prenume TEXT, email TEXT, sex TEXT, data_nasterii TEXT, parola_hash TEXT
            )
        """)
        return conn

    # Păcălim aplicația să folosească BD-ul fals
    monkeypatch.setattr("interfata.get_db_connection", fake_connection)


def test_inregistrare_utilizator_nou():
    date_formular = {
        "nume": "Popescu",
        "prenume": "Ion",
        "cnp": "1990101123456",
        "email": "ion@test.com",
        "sex": "M",
        "data_nasterii": "1999-01-01",
        "parola": "parola123",
    }

    succes, rezultat = register_user(date_formular)
    assert succes is True
    assert rezultat == 1  # Primul ID inserat
