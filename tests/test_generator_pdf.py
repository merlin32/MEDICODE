import datetime
from src.backend.core.pdf_generator import exporta_raport_pdf_pacient


def test_generare_pdf_succes():
    """Verifică dacă funcția generează un PDF valid pe bază de text brut."""
    text_mock = "Acesta este un test de analiză medicală generat de AI."
    user_data_mock = {
        "nume": "Testescu",
        "prenume": "Ion",
        "afectiuni": ["Astm bronșic"],
    }
    clinica_mock = "Clinica de Testare"
    data_mock = datetime.date(2026, 6, 17)

    # Executăm funcția
    rezultat_bytes = exporta_raport_pdf_pacient(
        text_ai=text_mock,
        user_data=user_data_mock,
        clinica=clinica_mock,
        data_rec=data_mock,
    )

    # Asertări
    assert rezultat_bytes is not None, "Funcția a returnat None în loc de bytes."
    assert isinstance(rezultat_bytes, bytes), "Rezultatul nu este de tip bytes."
    # Un fișier PDF valid începe mereu cu magic number-ul %PDF
    assert rezultat_bytes.startswith(
        b"%PDF"
    ), "Fișierul generat nu are semnătura unui PDF valid."
    assert (
        len(rezultat_bytes) > 1000
    ), "Fișierul PDF pare prea mic pentru a conține textul și antetul."
