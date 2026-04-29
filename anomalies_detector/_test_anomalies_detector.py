import unittest
import json
from unittest.mock import MagicMock, patch, mock_open

from hypothesis import given, assume, settings
from hypothesis import strategies as st

from anomalies_detector import genereaza_raport_json

# ---------------------------------------------------------------------------
# Strategii reutilizabile
# ---------------------------------------------------------------------------

# Valori reale finite (fara NaN / Infinity) intr-un interval rezonabil
valoare_reala = st.floats(
    min_value=-10_000, max_value=10_000, allow_nan=False, allow_infinity=False
)

# ID-uri pozitive de utilizator si sesiune
id_pozitiv = st.integers(min_value=1, max_value=10_000)

# Nume de biomarker: text simplu, cel putin 1 caracter
nume_biomarker = st.text(
    min_size=1,
    max_size=50,
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
)


def make_mock_db(mock_db_class, rows):
    """Configureaza mock-ul pentru DatabaseConnection."""
    mock_db_instance = MagicMock()
    mock_db_class.return_value = mock_db_instance

    mock_conn = MagicMock()
    mock_db_instance.connection = mock_conn

    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = rows

    return mock_conn, mock_cursor


def ruleaza_functie_cu_randuri(mock_db_class, rows):
    """
    Apeleaza genereaza_raport_json cu rows injectate prin mock
    si returneaza datele JSON captate.
    """
    make_mock_db(mock_db_class, rows)
    with patch("json.dump") as mock_json_dump:
        with patch("builtins.open", mock_open()):
            genereaza_raport_json("test_output.json")
            return mock_json_dump.call_args[0][0]


# ---------------------------------------------------------------------------
# Proprietate 1 — Valorile normale NU apar niciodata in output
# ---------------------------------------------------------------------------
class TestValoriNormale(unittest.TestCase):

    @given(
        u_id=id_pozitiv,
        s_id=id_pozitiv,
        nume=nume_biomarker,
        v_min=valoare_reala,
        v_max=valoare_reala,
        val=valoare_reala,
    )
    @settings(max_examples=200)
    @patch("anomalies_detector.DatabaseConnection")
    def test_valoare_normala_nu_apare_in_output(
        self, mock_db_class, u_id, s_id, nume, v_min, v_max, val
    ):
        """
        PROPRIETATE: Daca v_min <= val <= v_max, biomarkerul NU apare in JSON.
        Hypothesis va genera sute de combinatii (u_id, s_id, val, v_min, v_max).
        """
        assume(v_min <= v_max)  # interval valid
        assume(v_min <= val <= v_max)  # valoare in interval

        fake_row = {
            "id_utilizator": u_id,
            "id_sesiune": s_id,
            "nume_biomarker": nume,
            "valoare_masurata": val,
            "valoare_min_ref": v_min,
            "valoare_max_ref": v_max,
        }

        result = ruleaza_functie_cu_randuri(mock_db_class, [fake_row])
        self.assertEqual(
            result,
            [],
            f"Valoarea normala {val} in [{v_min}, {v_max}] "
            f"nu trebuia sa apara in output!",
        )


# ---------------------------------------------------------------------------
# Proprietate 2 — Valorile anormale INTOTDEAUNA apar in output
# ---------------------------------------------------------------------------
class TestValoriAnormale(unittest.TestCase):

    @given(
        u_id=id_pozitiv,
        s_id=id_pozitiv,
        nume=nume_biomarker,
        v_min=valoare_reala,
        v_max=valoare_reala,
        val=valoare_reala,
    )
    @settings(max_examples=200)
    @patch("anomalies_detector.DatabaseConnection")
    def test_valoare_anormala_apare_in_output(
        self, mock_db_class, u_id, s_id, nume, v_min, v_max, val
    ):
        """
        PROPRIETATE: Daca val < v_min sau val > v_max, biomarkerul TREBUIE sa apara in JSON.
        """
        assume(v_min <= v_max)
        assume(val < v_min or val > v_max)  # valoare in afara intervalului

        fake_row = {
            "id_utilizator": u_id,
            "id_sesiune": s_id,
            "nume_biomarker": nume,
            "valoare_masurata": val,
            "valoare_min_ref": v_min,
            "valoare_max_ref": v_max,
        }

        result = ruleaza_functie_cu_randuri(mock_db_class, [fake_row])
        self.assertEqual(
            len(result),
            1,
            f"Valoarea anormala {val} in [{v_min}, {v_max}] "
            f"trebuia sa apara in output!",
        )


# ---------------------------------------------------------------------------
# Proprietate 3 — Devierea este intotdeauna >= 0%
# ---------------------------------------------------------------------------
class TestDeviere(unittest.TestCase):

    @given(
        u_id=id_pozitiv,
        s_id=id_pozitiv,
        v_min=valoare_reala,
        v_max=valoare_reala,
        val=valoare_reala,
    )
    @settings(max_examples=200)
    @patch("anomalies_detector.DatabaseConnection")
    def test_devierea_este_intotdeauna_pozitiva(
        self, mock_db_class, u_id, s_id, v_min, v_max, val
    ):
        """
        PROPRIETATE: Devierea procentuala calculata este intotdeauna >= 0.
        Nu poate exista deviere negativa, indiferent de valorile introduse.
        """
        assume(v_min <= v_max)
        assume(val < v_min or val > v_max)

        fake_row = {
            "id_utilizator": u_id,
            "id_sesiune": s_id,
            "nume_biomarker": "Test",
            "valoare_masurata": val,
            "valoare_min_ref": v_min,
            "valoare_max_ref": v_max,
        }

        result = ruleaza_functie_cu_randuri(mock_db_class, [fake_row])
        if result:
            biomarker = result[0]["analize_problematice"][0]["biomarkeri_alerta"][0]
            deviere = float(biomarker["deviere"].replace("%", ""))
            self.assertGreaterEqual(
                deviere,
                0.0,
                f"Devierea nu poate fi negativa! "
                f"val={val}, v_min={v_min}, v_max={v_max}",
            )

    @given(
        v_min=st.floats(
            min_value=0.01, max_value=10_000, allow_nan=False, allow_infinity=False
        ),
        v_max=st.floats(
            min_value=0.01, max_value=10_000, allow_nan=False, allow_infinity=False
        ),
        val=valoare_reala,
    )
    @settings(max_examples=200)
    @patch("anomalies_detector.DatabaseConnection")
    def test_devierea_cu_referinte_pozitive(self, mock_db_class, v_min, v_max, val):
        """
        PROPRIETATE: Cand v_min > 0 si v_max > 0, formula de deviere
        produce intotdeauna un numar finit si >= 0.
        """
        assume(v_min < v_max)
        assume(val < v_min or val > v_max)

        fake_row = {
            "id_utilizator": 1,
            "id_sesiune": 1,
            "nume_biomarker": "Test",
            "valoare_masurata": val,
            "valoare_min_ref": v_min,
            "valoare_max_ref": v_max,
        }

        result = ruleaza_functie_cu_randuri(mock_db_class, [fake_row])
        if result:
            biomarker = result[0]["analize_problematice"][0]["biomarkeri_alerta"][0]
            deviere = float(biomarker["deviere"].replace("%", ""))
            self.assertGreaterEqual(deviere, 0.0)
            self.assertFalse(
                deviere != deviere, "Devierea nu trebuie sa fie NaN!"  # NaN check
            )


# ---------------------------------------------------------------------------
# Proprietate 4 — Gruparea pe utilizatori este corecta
# ---------------------------------------------------------------------------
class TestGrupare(unittest.TestCase):

    @given(
        u_ids=st.lists(id_pozitiv, min_size=1, max_size=10, unique=True),
        v_min=st.just(70.0),
        v_max=st.just(100.0),
        val=st.just(150.0),  # mereu anormal
    )
    @settings(max_examples=100)
    @patch("anomalies_detector.DatabaseConnection")
    def test_numar_utilizatori_in_output(self, mock_db_class, u_ids, v_min, v_max, val):
        """
        PROPRIETATE: Numarul de utilizatori distincti din output
        este egal cu numarul de u_id-uri unice din input (care au valori anormale).
        """
        rows = [
            {
                "id_utilizator": u_id,
                "id_sesiune": i + 1,
                "nume_biomarker": "Glicemie",
                "valoare_masurata": val,
                "valoare_min_ref": v_min,
                "valoare_max_ref": v_max,
            }
            for i, u_id in enumerate(u_ids)
        ]

        result = ruleaza_functie_cu_randuri(mock_db_class, rows)
        id_uri_in_output = {u["id_utilizator"] for u in result}
        self.assertEqual(
            id_uri_in_output,
            set(u_ids),
            "Toti utilizatorii cu valori anormale trebuie sa apara in output!",
        )

    @given(
        s_ids=st.lists(id_pozitiv, min_size=1, max_size=10, unique=True),
    )
    @settings(max_examples=100)
    @patch("anomalies_detector.DatabaseConnection")
    def test_numar_sesiuni_per_utilizator(self, mock_db_class, s_ids):
        """
        PROPRIETATE: Numarul de sesiuni per utilizator in output
        este egal cu numarul de s_id-uri unice din input.
        """
        rows = [
            {
                "id_utilizator": 1,
                "id_sesiune": s_id,
                "nume_biomarker": "Glicemie",
                "valoare_masurata": 150.0,
                "valoare_min_ref": 70.0,
                "valoare_max_ref": 100.0,
            }
            for s_id in s_ids
        ]

        result = ruleaza_functie_cu_randuri(mock_db_class, rows)
        sesiuni_in_output = result[0]["analize_problematice"]
        self.assertEqual(
            len(sesiuni_in_output),
            len(s_ids),
            "Numarul de sesiuni in output nu corespunde cu inputul!",
        )


# ---------------------------------------------------------------------------
# Proprietate 5 — Output-ul este intotdeauna JSON serializabil
# ---------------------------------------------------------------------------
class TestJsonSerializabil(unittest.TestCase):

    @given(
        u_id=id_pozitiv,
        s_id=id_pozitiv,
        v_min=valoare_reala,
        v_max=valoare_reala,
        val=valoare_reala,
    )
    @settings(max_examples=200)
    @patch("anomalies_detector.DatabaseConnection")
    def test_output_este_json_serializabil(
        self, mock_db_class, u_id, s_id, v_min, v_max, val
    ):
        """
        PROPRIETATE: Indiferent de input, output-ul functiei
        trebuie sa fie intotdeauna serializabil ca JSON valid.
        """
        assume(v_min <= v_max)

        fake_row = {
            "id_utilizator": u_id,
            "id_sesiune": s_id,
            "nume_biomarker": "Test",
            "valoare_masurata": val,
            "valoare_min_ref": v_min,
            "valoare_max_ref": v_max,
        }

        result = ruleaza_functie_cu_randuri(mock_db_class, [fake_row])

        try:
            json.dumps(result)
        except (TypeError, ValueError) as e:
            self.fail(f"Output-ul nu este JSON serializabil: {e}")


if __name__ == "__main__":
    unittest.main()
