import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import sqlite3
from hypothesis import given, assume, strategies as st
from unittest.mock import patch
from src.backend.db.inserare_BD import (
    proceseaza_si_salveaza_buletin,
    asociere_afectiune,
    finalizeaza_analiza,
)

# ==========================================
# HELPERS
# ==========================================


def create_test_db():
    """
    Creează o bază de date izolată în memorie.
    Fiecare apel returnează o conexiune complet independentă —
    folosită direct în teste pytest și în Hypothesis (care nu trece prin fixture).
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE Utilizatori (
            id_utilizator INTEGER PRIMARY KEY AUTOINCREMENT,
            cnp TEXT UNIQUE NOT NULL,
            nume TEXT NOT NULL,
            prenume TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            sex TEXT NOT NULL,
            data_nasterii DATE NOT NULL,
            parola_hash TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE Clinici (
            id_clinica INTEGER PRIMARY KEY AUTOINCREMENT,
            nume_clinica TEXT UNIQUE NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE Analize (
            id_sesiune INTEGER PRIMARY KEY AUTOINCREMENT,
            id_utilizator INTEGER NOT NULL,
            id_clinica INTEGER NOT NULL,
            data_recoltare DATE NOT NULL,
            upload_hash TEXT,
            finalizata INTEGER DEFAULT 0,
            FOREIGN KEY (id_utilizator) REFERENCES Utilizatori(id_utilizator) ON DELETE CASCADE,
            FOREIGN KEY (id_clinica) REFERENCES Clinici(id_clinica)
        )
    """)
    cursor.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_analize_upload_hash "
        "ON Analize(id_utilizator, upload_hash)"
    )
    cursor.execute("""
        CREATE TABLE Biomarkeri (
            id_biomarker INTEGER PRIMARY KEY AUTOINCREMENT,
            nume_biomarker TEXT NOT NULL,
            ref_min REAL NOT NULL,
            ref_max REAL NOT NULL,
            is_bool BOOLEAN NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE Valori_Masurate (
            id_sesiune INTEGER NOT NULL,
            id_biomarker INTEGER NOT NULL,
            val_mas REAL NOT NULL,
            unit_mas TEXT NOT NULL,
            PRIMARY KEY (id_sesiune, id_biomarker),
            FOREIGN KEY (id_sesiune) REFERENCES Analize(id_sesiune) ON DELETE CASCADE,
            FOREIGN KEY (id_biomarker) REFERENCES Biomarkeri(id_biomarker) ON DELETE RESTRICT
        )
    """)
    cursor.execute("""
        CREATE TABLE Afectiuni (
            nume_afectiune TEXT PRIMARY KEY,
            descriere_generala TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE Utilizator_Afectiune (
            id_utilizator INTEGER NOT NULL,
            nume_afectiune TEXT NOT NULL,
            status TEXT,
            PRIMARY KEY (id_utilizator, nume_afectiune),
            FOREIGN KEY (id_utilizator) REFERENCES Utilizatori(id_utilizator) ON DELETE CASCADE,
            FOREIGN KEY (nume_afectiune) REFERENCES Afectiuni(nume_afectiune) ON DELETE CASCADE
        )
    """)
    cursor.execute(
        "INSERT INTO Utilizatori (cnp, nume, prenume, email, sex, data_nasterii, parola_hash) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "1990101123456",
            "Popescu",
            "Ion",
            "ion@test.com",
            "M",
            "1990-01-01",
            "hash123",
        ),
    )
    conn.commit()
    return conn


def make_mock_class(conn):
    """Returnează o clasă MockDatabaseConnection legată la conexiunea dată."""

    class MockDatabaseConnection:
        def __init__(self):
            self.connection = conn

    return MockDatabaseConnection


# ==========================================
# FIXTURES
# ==========================================


@pytest.fixture
def test_db():
    """
    Bază de date izolată per test.
    Nu este autouse — fiecare test o cere explicit, prevenind
    orice scurgere de stare între teste și clarificând dependențele.
    """
    conn = create_test_db()
    yield conn
    conn.close()


@pytest.fixture
def mock_db(monkeypatch, test_db):
    """
    Patch-ează DatabaseConnection să folosească test_db.
    Cerut explicit (nu autouse) pentru a evita aplicarea invizibilă
    pe teste care nu au nevoie de el (ex. Hypothesis, care își gestionează
    propria izolare prin create_test_db() + patch() în context manager).
    """
    monkeypatch.setattr(
        "src.backend.db.inserare_BD.DatabaseConnection",
        make_mock_class(test_db),
    )
    return test_db


# ==========================================
# TESTE: proceseaza_si_salveaza_buletin
# ==========================================


class TestProceseazaSiSalveazaBuletin:

    def test_inserare_buletin_cu_clinica_noua(self, mock_db):
        """Test: Inserare buletin cu clinică nouă"""
        lista_analize = [
            {
                "analiza": "Glicemie",
                "valoare_numerica": 95.5,
                "unitate_masura": "mg/dL",
                "ref_min": 70.0,
                "ref_max": 100.0,
                "is_bool": 0,
            },
            {
                "analiza": "Hemoglobina",
                "valoare_numerica": 14.2,
                "unitate_masura": "g/dL",
                "ref_min": 12.0,
                "ref_max": 17.0,
                "is_bool": 0,
            },
        ]

        rezultate, _, _, _ = proceseaza_si_salveaza_buletin(
            id_utilizator=1,
            data_recoltare="2026-06-15",
            lista_analize_extrase=lista_analize,
            nume_clinica="Regina Maria",
        )

        assert len(rezultate) == 2
        assert rezultate[0]["nume"] == "Glicemie"
        assert rezultate[0]["valoare"] == 95.5
        assert rezultate[1]["nume"] == "Hemoglobina"
        assert rezultate[1]["valoare"] == 14.2

        cursor = mock_db.cursor()
        clinici = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Clinici WHERE nume_clinica = ?",
            ("Regina Maria",),
        ).fetchone()
        assert clinici["cnt"] == 1

        analize = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Analize WHERE id_utilizator = ?", (1,)
        ).fetchone()
        assert analize["cnt"] == 1

        cnt_valori = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Valori_Masurate"
        ).fetchone()
        assert cnt_valori["cnt"] == 2

    def test_inserare_buletin_cu_clinica_existenta(self, mock_db):
        """Test: Inserare buletin cu clinică deja existentă — nu se duplică"""
        cursor = mock_db.cursor()
        cursor.execute("INSERT INTO Clinici (nume_clinica) VALUES (?)", ("MedLife",))
        mock_db.commit()

        lista_analize = [
            {
                "analiza": "Colesterol",
                "valoare_numerica": 200.0,
                "unitate_masura": "mg/dL",
                "ref_min": 0.0,
                "ref_max": 200.0,
                "is_bool": 0,
            }
        ]

        rezultate, _, _, _ = proceseaza_si_salveaza_buletin(
            id_utilizator=1,
            data_recoltare="2026-06-15",
            lista_analize_extrase=lista_analize,
            nume_clinica="MedLife",
        )

        clinici = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Clinici WHERE nume_clinica = ?", ("MedLife",)
        ).fetchone()
        assert clinici["cnt"] == 1
        assert len(rezultate) == 1
        assert rezultate[0]["nume"] == "Colesterol"

    def test_inserare_biomarker_nou(self, mock_db):
        """Test: Biomarker nou este creat în Biomarkeri"""
        lista_analize = [
            {
                "analiza": "Sodiu",
                "valoare_numerica": 138.0,
                "unitate_masura": "mEq/L",
                "ref_min": 135.0,
                "ref_max": 145.0,
                "is_bool": 0,
            }
        ]

        rezultate, _, _, _ = proceseaza_si_salveaza_buletin(
            id_utilizator=1,
            data_recoltare="2026-06-15",
            lista_analize_extrase=lista_analize,
            nume_clinica="Sanador",
        )

        cursor = mock_db.cursor()
        biomarker = cursor.execute(
            "SELECT * FROM Biomarkeri WHERE nume_biomarker = ?", ("Sodiu",)
        ).fetchone()
        assert biomarker is not None
        assert biomarker["ref_min"] == 135.0
        assert biomarker["ref_max"] == 145.0
        assert len(rezultate) == 1
        assert rezultate[0]["valoare"] == 138.0

    def test_inserare_biomarker_duplicat_cu_intervale_diferite(self, mock_db):
        """Test: Biomarker cu același nume dar intervale diferite = biomarker separat"""
        cursor = mock_db.cursor()
        cursor.execute(
            "INSERT INTO Biomarkeri (nume_biomarker, ref_min, ref_max, is_bool) VALUES (?, ?, ?, ?)",
            ("Potasiu", 3.5, 5.0, 0),
        )
        mock_db.commit()

        lista_analize = [
            {
                "analiza": "Potasiu",
                "valoare_numerica": 4.2,
                "unitate_masura": "mEq/L",
                "ref_min": 3.0,
                "ref_max": 5.5,
                "is_bool": 0,
            }
        ]

        _, _, _, _ = proceseaza_si_salveaza_buletin(
            id_utilizator=1,
            data_recoltare="2026-06-15",
            lista_analize_extrase=lista_analize,
            nume_clinica="Synevo",
        )

        biomarkeri = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Biomarkeri WHERE nume_biomarker = ?",
            ("Potasiu",),
        ).fetchone()
        assert biomarkeri["cnt"] == 2

    def test_inserare_valori_masurate(self, mock_db):
        """Test: Valorile măsurate sunt salvate corect în Valori_Masurate"""
        lista_analize = [
            {
                "analiza": "Proteine Totale",
                "valoare_numerica": 7.2,
                "unitate_masura": "g/dL",
                "ref_min": 6.0,
                "ref_max": 8.3,
                "is_bool": 0,
            }
        ]

        _, _, _, _ = proceseaza_si_salveaza_buletin(
            id_utilizator=1,
            data_recoltare="2026-06-15",
            lista_analize_extrase=lista_analize,
            nume_clinica="Bioclinica",
        )

        cursor = mock_db.cursor()
        valori = cursor.execute("SELECT * FROM Valori_Masurate").fetchall()
        assert len(valori) == 1
        assert valori[0]["val_mas"] == 7.2
        assert valori[0]["unit_mas"] == "g/dL"

    def test_inserare_buletin_trim_si_case_insensitive_nume_biomarker(self, mock_db):
        """
        Test: Două intrări cu același biomarker (diferite prin spații/casing) produc
        un singur rând în Biomarkeri și un singur rând în Valori_Masurate.

        Notă importantă: codul stochează numele AS-IS (cu spații), deci primul INSERT
        câștigă atât în Biomarkeri cât și în Valori_Masurate (INSERT OR IGNORE pe PK).
        Testul verifică explicit ce valoare a fost stocată, pentru a prinde orice
        regresie în ordinea procesării.
        """
        lista_analize = [
            {
                "analiza": "  Glicemie  ",
                "valoare_numerica": 95.5,
                "unitate_masura": "mg/dL",
                "ref_min": 70.0,
                "ref_max": 100.0,
                "is_bool": 0,
            },
            {
                "analiza": "glicemie",
                "valoare_numerica": 96.0,
                "unitate_masura": "mg/dL",
                "ref_min": 70.0,
                "ref_max": 100.0,
                "is_bool": 0,
            },
        ]

        _, _, _, _ = proceseaza_si_salveaza_buletin(
            id_utilizator=1,
            data_recoltare="2026-06-15",
            lista_analize_extrase=lista_analize,
            nume_clinica="Regina Maria",
        )

        cursor = mock_db.cursor()

        biomarkeri = cursor.execute("SELECT COUNT(*) as cnt FROM Biomarkeri").fetchone()
        assert biomarkeri["cnt"] == 1

        valori = cursor.execute("SELECT * FROM Valori_Masurate").fetchall()
        assert len(valori) == 1
        # Primul INSERT câștigă — valoarea stocată este 95.5, nu 96.0
        assert valori[0]["val_mas"] == 95.5

        # Numele stocat este cel original (netrunchiat) — limitare documentată a implementării
        biomarker_stocat = cursor.execute(
            "SELECT nume_biomarker FROM Biomarkeri"
        ).fetchone()
        assert biomarker_stocat["nume_biomarker"] == "  Glicemie  "

    def test_inserare_fara_upload_hash(self, mock_db):
        """Test: Inserarea fără upload_hash (None) creează sesiunea fără verificare duplicat."""
        lista_analize = [
            {
                "analiza": "Fier",
                "valoare_numerica": 80.0,
                "unitate_masura": "µg/dL",
                "ref_min": 60.0,
                "ref_max": 170.0,
                "is_bool": 0,
            }
        ]

        rezultate, sesiune_reutilizata, id_sesiune, upload_allowed = (
            proceseaza_si_salveaza_buletin(
                id_utilizator=1,
                data_recoltare="2026-06-15",
                lista_analize_extrase=lista_analize,
                nume_clinica="Gral Medical",
                upload_hash=None,
            )
        )

        assert upload_allowed is True
        assert sesiune_reutilizata is False
        assert id_sesiune is not None
        assert len(rezultate) == 1

        cursor = mock_db.cursor()
        analiza = cursor.execute(
            "SELECT upload_hash FROM Analize WHERE id_sesiune = ?", (id_sesiune,)
        ).fetchone()
        assert analiza["upload_hash"] is None

    def test_reutilizare_sesiune_nefinalizata(self, mock_db):
        """
        Test: Un upload cu același hash pentru o sesiune NEFINALIZATĂ reutilizează
        sesiunea și șterge valorile vechi.
        """
        lista_analize = [
            {
                "analiza": "Calciu",
                "valoare_numerica": 9.5,
                "unitate_masura": "mg/dL",
                "ref_min": 8.5,
                "ref_max": 10.5,
                "is_bool": 0,
            }
        ]
        hash_test = "abc123reutilizare"

        _, _, id_sesiune_1, _ = proceseaza_si_salveaza_buletin(
            id_utilizator=1,
            data_recoltare="2026-06-15",
            lista_analize_extrase=lista_analize,
            nume_clinica="Synevo",
            upload_hash=hash_test,
        )

        lista_analize_2 = [
            {
                "analiza": "Magneziu",
                "valoare_numerica": 2.0,
                "unitate_masura": "mg/dL",
                "ref_min": 1.7,
                "ref_max": 2.4,
                "is_bool": 0,
            }
        ]
        rezultate, sesiune_reutilizata, id_sesiune_2, upload_allowed = (
            proceseaza_si_salveaza_buletin(
                id_utilizator=1,
                data_recoltare="2026-06-15",
                lista_analize_extrase=lista_analize_2,
                nume_clinica="Synevo",
                upload_hash=hash_test,
            )
        )

        assert upload_allowed is True
        assert sesiune_reutilizata is True
        assert id_sesiune_1 == id_sesiune_2

        cursor = mock_db.cursor()
        valori = cursor.execute(
            "SELECT b.nume_biomarker FROM Valori_Masurate vm "
            "JOIN Biomarkeri b ON vm.id_biomarker = b.id_biomarker "
            "WHERE vm.id_sesiune = ?",
            (id_sesiune_1,),
        ).fetchall()
        nume_valori = [v["nume_biomarker"] for v in valori]
        assert "Magneziu" in nume_valori
        assert "Calciu" not in nume_valori

    def test_blocare_duplicat_finalizat(self, mock_db):
        """Test: Un upload cu același hash pentru o sesiune FINALIZATĂ este blocat."""
        lista_analize = [
            {
                "analiza": "TSH",
                "valoare_numerica": 2.5,
                "unitate_masura": "µIU/mL",
                "ref_min": 0.4,
                "ref_max": 4.0,
                "is_bool": 0,
            }
        ]
        hash_test = "finalizat_hash_xyz"

        _, _, id_sesiune, _ = proceseaza_si_salveaza_buletin(
            id_utilizator=1,
            data_recoltare="2026-06-15",
            lista_analize_extrase=lista_analize,
            nume_clinica="Regina Maria",
            upload_hash=hash_test,
        )
        finalizeaza_analiza(id_sesiune)

        rezultate, sesiune_reutilizata, id_sesiune_2, upload_allowed = (
            proceseaza_si_salveaza_buletin(
                id_utilizator=1,
                data_recoltare="2026-06-15",
                lista_analize_extrase=lista_analize,
                nume_clinica="Regina Maria",
                upload_hash=hash_test,
            )
        )

        assert upload_allowed is False
        assert rezultate == []
        assert id_sesiune_2 == id_sesiune

    def test_lista_analize_goala(self, mock_db):
        """Test: Lista goală de analize creează sesiunea dar nu inserează biomarkeri sau valori."""
        rezultate, _, id_sesiune, upload_allowed = proceseaza_si_salveaza_buletin(
            id_utilizator=1,
            data_recoltare="2026-06-15",
            lista_analize_extrase=[],
            nume_clinica="MedLife",
        )

        assert upload_allowed is True
        assert rezultate == []
        assert id_sesiune is not None

        cursor = mock_db.cursor()
        cnt_valori = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Valori_Masurate"
        ).fetchone()
        assert cnt_valori["cnt"] == 0

        analiza = cursor.execute(
            "SELECT * FROM Analize WHERE id_sesiune = ?", (id_sesiune,)
        ).fetchone()
        assert analiza is not None


# ==========================================
# TESTE: finalizeaza_analiza
# ==========================================


class TestFinalizeazaAnaliza:

    def test_finalizeaza_analiza_seteaza_flag(self, mock_db):
        """Test: finalizeaza_analiza setează finalizata = 1 pentru sesiunea dată."""
        cursor = mock_db.cursor()

        cursor.execute("INSERT INTO Clinici (nume_clinica) VALUES (?)", ("Synevo",))
        mock_db.commit()
        id_clinica = cursor.execute(
            "SELECT id_clinica FROM Clinici WHERE nume_clinica = ?", ("Synevo",)
        ).fetchone()["id_clinica"]

        cursor.execute(
            "INSERT INTO Analize (id_utilizator, id_clinica, data_recoltare, finalizata) VALUES (?, ?, ?, 0)",
            (1, id_clinica, "2026-06-15"),
        )
        mock_db.commit()
        id_sesiune = cursor.lastrowid

        result = finalizeaza_analiza(id_sesiune)

        assert result is True
        analiza = cursor.execute(
            "SELECT finalizata FROM Analize WHERE id_sesiune = ?", (id_sesiune,)
        ).fetchone()
        assert analiza["finalizata"] == 1

    def test_finalizeaza_analiza_id_inexistent(self, mock_db):
        """Test: finalizeaza_analiza pe un id inexistent nu aruncă excepție și nu modifică nimic."""
        result = finalizeaza_analiza(99999)
        assert result is True

        cursor = mock_db.cursor()
        cnt = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Analize WHERE finalizata = 1"
        ).fetchone()
        assert cnt["cnt"] == 0


# ==========================================
# TESTE: asociere_afectiune
# ==========================================


class TestAsociereAfectiune:

    def test_asociere_afectiune_noua(self, mock_db):
        """Test: Asociere cu o afecțiune nouă"""
        succes, mesaj = asociere_afectiune(
            nume_afectiune="Diabet Zaharat Tip 2",
            descriere_generala="Boală metabolică",
            id_utilizator=1,
            status="Actuală",
        )

        assert succes is True
        assert "asociată" in mesaj.lower()

        cursor = mock_db.cursor()
        afectiune = cursor.execute(
            "SELECT * FROM Afectiuni WHERE nume_afectiune = ?",
            ("Diabet Zaharat Tip 2",),
        ).fetchone()
        assert afectiune is not None
        assert afectiune["descriere_generala"] == "Boală metabolică"

        asociere = cursor.execute(
            "SELECT * FROM Utilizator_Afectiune WHERE id_utilizator = ? AND nume_afectiune = ?",
            (1, "Diabet Zaharat Tip 2"),
        ).fetchone()
        assert asociere is not None
        assert asociere["status"] == "Actuală"

    def test_asociere_afectiune_existenta(self, mock_db):
        """Test: Asociere cu afecțiune deja existentă în tabel — nu se duplică"""
        cursor = mock_db.cursor()
        cursor.execute(
            "INSERT INTO Afectiuni (nume_afectiune, descriere_generala) VALUES (?, ?)",
            ("Hipertensiune", "Presiune arterială ridicată"),
        )
        mock_db.commit()

        succes, mesaj = asociere_afectiune(
            nume_afectiune="Hipertensiune",
            descriere_generala="Descriere ignorată dacă deja există",
            id_utilizator=1,
            status="Actuală",
        )

        assert succes is True
        assert "asociată" in mesaj.lower()

        afectiuni = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Afectiuni WHERE nume_afectiune = ?",
            ("Hipertensiune",),
        ).fetchone()
        assert afectiuni["cnt"] == 1

    def test_update_status_afectiune(self, mock_db):
        """Test: Update status când utilizatorul are deja afecțiunea"""
        cursor = mock_db.cursor()
        cursor.execute(
            "INSERT INTO Afectiuni (nume_afectiune, descriere_generala) VALUES (?, ?)",
            ("Astm", "Boală respiratorie"),
        )
        cursor.execute(
            "INSERT INTO Utilizator_Afectiune (id_utilizator, nume_afectiune, status) VALUES (?, ?, ?)",
            (1, "Astm", "Actuală"),
        )
        mock_db.commit()

        succes, mesaj = asociere_afectiune(
            nume_afectiune="Astm",
            descriere_generala="Nu conteaza",
            id_utilizator=1,
            status="Vindecată",
        )

        assert succes is True
        assert "actualizat" in mesaj.lower()

        asociere = cursor.execute(
            "SELECT status FROM Utilizator_Afectiune WHERE id_utilizator = ? AND nume_afectiune = ?",
            (1, "Astm"),
        ).fetchone()
        assert asociere["status"] == "Vindecată"

    def test_case_insensitive_afectiune(self, mock_db):
        """Test: Căutare case-insensitive — nu se duplică afecțiunea"""
        cursor = mock_db.cursor()
        cursor.execute(
            "INSERT INTO Afectiuni (nume_afectiune, descriere_generala) VALUES (?, ?)",
            ("Colesterol Ridicat", "Descriere"),
        )
        mock_db.commit()

        succes, _ = asociere_afectiune(
            nume_afectiune="COLESTEROL RIDICAT",
            descriere_generala="Nu conteaza",
            id_utilizator=1,
            status="Actuală",
        )

        assert succes is True

        afectiuni = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Afectiuni WHERE lower(nume_afectiune) = lower(?)",
            ("Colesterol Ridicat",),
        ).fetchone()
        assert afectiuni["cnt"] == 1

    def test_asociere_multipli_utilizatori_aceeasi_afectiune(self, mock_db):
        """Test: Aceeași afecțiune asociată la mai mulți utilizatori"""
        cursor = mock_db.cursor()
        cursor.execute(
            "INSERT INTO Utilizatori (cnp, nume, prenume, email, sex, data_nasterii, parola_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "1995101234567",
                "Oancea",
                "Maria",
                "maria@test.com",
                "F",
                "1995-01-01",
                "hash456",
            ),
        )
        mock_db.commit()

        succes1, _ = asociere_afectiune(
            nume_afectiune="Insomnii",
            descriere_generala="Tulburare de somn",
            id_utilizator=1,
            status="Actuală",
        )
        succes2, _ = asociere_afectiune(
            nume_afectiune="Insomnii",
            descriere_generala="Tulburare de somn",
            id_utilizator=2,
            status="Vindecată",
        )

        assert succes1 is True
        assert succes2 is True

        cursor = mock_db.cursor()
        afectiuni = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Afectiuni WHERE nume_afectiune = ?",
            ("Insomnii",),
        ).fetchone()
        assert afectiuni["cnt"] == 1

        asocieri = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Utilizator_Afectiune WHERE nume_afectiune = ?",
            ("Insomnii",),
        ).fetchone()
        assert asocieri["cnt"] == 2

    def test_asociere_pastreaza_numele_original_din_bd(self, mock_db):
        """
        Test: Când afecțiunea există deja cu un alt casing, asocierea folosește
        numele exact din BD pentru a respecta FK-ul din Utilizator_Afectiune.
        """
        cursor = mock_db.cursor()
        cursor.execute(
            "INSERT INTO Afectiuni (nume_afectiune, descriere_generala) VALUES (?, ?)",
            ("Epilepsie", "Boală neurologică"),
        )
        mock_db.commit()

        succes, _ = asociere_afectiune(
            nume_afectiune="EPILEPSIE",
            descriere_generala="Nu conteaza",
            id_utilizator=1,
            status="Actuală",
        )

        assert succes is True

        asociere = cursor.execute(
            "SELECT nume_afectiune FROM Utilizator_Afectiune WHERE id_utilizator = 1"
        ).fetchone()
        assert asociere["nume_afectiune"] == "Epilepsie"


# ==========================================
# TESTE HYPOTHESIS
# ==========================================

# Strategie comună pentru un biomarker valid cu valori float sigure pentru SQLite.
# Folosim valori rotunjite la 6 zecimale pentru a evita discrepanțe între
# comparațiile Python și stocarea SQLite REAL (IEEE 754), care altfel pot face
# ca Python set-deduplication și SQLite WHERE ref_min = ? să nu fie de acord.
safe_float_ref = st.floats(
    min_value=0.0,
    max_value=500.0,
    allow_nan=False,
    allow_infinity=False,
).map(lambda x: round(x, 6))

biomarker_strategy = st.fixed_dictionaries(
    {
        "analiza": st.text(min_size=3, max_size=30).filter(lambda s: s.strip() != ""),
        "valoare_numerica": st.floats(
            min_value=0, max_value=1000, allow_nan=False, allow_infinity=False
        ),
        "unitate_masura": st.sampled_from(["mg/dL", "g/dL", "mEq/L", "µg/dL", "%", ""]),
        "ref_min": safe_float_ref,
        "ref_max": safe_float_ref,
        "is_bool": st.integers(min_value=0, max_value=1),
    }
).filter(lambda d: d["ref_min"] < d["ref_max"])


@given(
    lista=st.lists(biomarker_strategy, min_size=1, max_size=5),
    clinica=st.sampled_from(
        ["Regina Maria", "MedLife", "Sanador", "Synevo", "Bioclinica"]
    ),
)
def test_proceseaza_si_salveaza_buletin_hypothesis(lista, clinica):
    """Hypothesis: inserarea produce exact atâția biomarkeri câte semnături unice există."""
    conn = create_test_db()
    try:
        with patch(
            "src.backend.db.inserare_BD.DatabaseConnection", make_mock_class(conn)
        ):
            _, _, _, upload_allowed = proceseaza_si_salveaza_buletin(
                id_utilizator=1,
                data_recoltare="2026-06-15",
                lista_analize_extrase=lista,
                nume_clinica=clinica,
            )

        assert upload_allowed is True

        cursor = conn.cursor()

        # Semnătura unică după care codul deduplicează biomarkerii.
        # Folosim round() cu aceeași precizie ca strategia, astfel încât Python set
        # și SQLite REAL să fie de acord la comparație.
        unique_signatures = set(
            (
                el["analiza"].strip().lower(),
                round(float(el["ref_min"]), 6),
                round(float(el["ref_max"]), 6),
                int(el["is_bool"]),
            )
            for el in lista
        )

        cnt_biomarkeri = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Biomarkeri"
        ).fetchone()["cnt"]
        assert cnt_biomarkeri == len(unique_signatures)

        cnt_valori = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Valori_Masurate"
        ).fetchone()["cnt"]
        # INSERT OR IGNORE pe PK (id_sesiune, id_biomarker) elimină duplicate în sesiune
        assert cnt_valori <= cnt_biomarkeri

    finally:
        conn.close()


@given(
    analiza=biomarker_strategy,
    repeat=st.integers(min_value=2, max_value=5),
    clinica=st.sampled_from(
        ["Regina Maria", "MedLife", "Sanador", "Synevo", "Bioclinica"]
    ),
)
def test_proceseaza_si_salveaza_buletin_hypothesis_duplicate_entries(
    analiza, repeat, clinica
):
    """Hypothesis: intrările identice duplicate produc exact 1 biomarker și 1 valoare."""
    lista = [analiza] * repeat

    conn = create_test_db()
    try:
        with patch(
            "src.backend.db.inserare_BD.DatabaseConnection", make_mock_class(conn)
        ):
            _, _, _, _ = proceseaza_si_salveaza_buletin(
                id_utilizator=1,
                data_recoltare="2026-06-15",
                lista_analize_extrase=lista,
                nume_clinica=clinica,
            )

        cursor = conn.cursor()
        biomarkeri = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Biomarkeri"
        ).fetchone()["cnt"]
        valori = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Valori_Masurate"
        ).fetchone()["cnt"]
    finally:
        conn.close()

    assert biomarkeri == 1
    assert valori == 1


@given(
    nume=st.text(min_size=3, max_size=30).filter(lambda s: s.strip() != ""),
    ref_min=safe_float_ref,
    ref_max=safe_float_ref,
    clinica=st.sampled_from(
        ["Regina Maria", "MedLife", "Sanador", "Synevo", "Bioclinica"]
    ),
)
def test_proceseaza_si_salveaza_buletin_hypothesis_same_name_different_is_bool(
    nume, ref_min, ref_max, clinica
):
    """Hypothesis: același nume cu is_bool diferit produce 2 biomarkeri separați."""
    # FIX: folosim assume() în loc de return silent, astfel Hypothesis
    # contorizează corect exemplele respinse și nu consumă bugetul inutil.
    assume(ref_min < ref_max)

    lista = [
        {
            "analiza": nume.strip(),
            "valoare_numerica": 1.0,
            "unitate_masura": "mg/dL",
            "ref_min": ref_min,
            "ref_max": ref_max,
            "is_bool": 0,
        },
        {
            "analiza": nume.strip(),
            "valoare_numerica": 0.0,
            "unitate_masura": "mg/dL",
            "ref_min": ref_min,
            "ref_max": ref_max,
            "is_bool": 1,
        },
    ]

    conn = create_test_db()
    try:
        with patch(
            "src.backend.db.inserare_BD.DatabaseConnection", make_mock_class(conn)
        ):
            _, _, _, _ = proceseaza_si_salveaza_buletin(
                id_utilizator=1,
                data_recoltare="2026-06-15",
                lista_analize_extrase=lista,
                nume_clinica=clinica,
            )

        cursor = conn.cursor()
        biomarkeri = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Biomarkeri"
        ).fetchone()["cnt"]
        valori = cursor.execute(
            "SELECT COUNT(*) as cnt FROM Valori_Masurate"
        ).fetchone()["cnt"]
    finally:
        conn.close()

    assert biomarkeri == 2
    assert valori == 2


@given(
    nume=st.text(min_size=1, max_size=40).filter(lambda s: s.strip() != ""),
    descr=st.text(min_size=1, max_size=120),
    status=st.sampled_from(["Actuală", "Vindecată"]),
)
def test_asociere_afectiune_hypothesis(nume, descr, status):
    """Hypothesis: asociere_afectiune funcționează cu nume generate aleatoriu."""
    conn = create_test_db()
    try:
        with patch(
            "src.backend.db.inserare_BD.DatabaseConnection", make_mock_class(conn)
        ):
            succes, _ = asociere_afectiune(
                nume_afectiune=nume.strip(),
                descriere_generala=descr,
                id_utilizator=1,
                status=status,
            )

        assert succes is True

        cursor = conn.cursor()
        af = cursor.execute(
            "SELECT * FROM Afectiuni WHERE lower(nume_afectiune) = lower(?)",
            (nume.strip(),),
        ).fetchone()
        assert af is not None

        asociere = cursor.execute(
            "SELECT status FROM Utilizator_Afectiune WHERE id_utilizator = 1"
        ).fetchone()
        assert asociere["status"] == status

    finally:
        conn.close()
