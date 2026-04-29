from streamlit.testing.v1 import AppTest


def test_afisare_pagina_autentificare():
    # Pornim aplicația invizibil
    at = AppTest.from_file("interfata.py").run()

    # Verificăm dacă textele principale se randează corect
    assert at.title[0].value == "🏥 MEDICODE"
    assert at.subheader[0].value == "Autentificare"

    # Verificăm dacă selectorul Conectare/Înregistrare este pe poziție
    assert at.radio[0].value == "Conectare"


def test_eroare_login_fara_date():
    at = AppTest.from_file("interfata.py").run()

    # Simulăm apăsarea butonului "Conectează-te" cu câmpurile goale
    at.button[0].click().run()

    # Trebuie să apară eroarea din cod
    assert at.error[0].value == "Completează emailul și parola."
