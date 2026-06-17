from streamlit.testing.v1 import AppTest


def test_afisare_pagina_autentificare():
    at = AppTest.from_file("src/frontend/interfata.py")
    # logout_requested = True blochează recuperarea sesiunii din cookie
    # în initialize_session_state(), prevenind redirectul spre dashboard
    at.session_state["authenticated"] = False
    at.session_state["current_user"] = None
    at.session_state["current_user_id"] = None
    at.session_state["logout_requested"] = True
    at = at.run(timeout=15)

    assert at.title[0].value == "🏥 MEDICODE"
    assert at.subheader[0].value == "Autentificare pacient"
    assert at.radio[0].value == "Conectare"


def test_eroare_login_fara_date():
    at = AppTest.from_file("src/frontend/interfata.py")
    at.session_state["authenticated"] = False
    at.session_state["current_user"] = None
    at.session_state["current_user_id"] = None
    at.session_state["logout_requested"] = True
    at = at.run()

    # form_submit_button nu există în AppTest — submit-urile din st.form
    # sunt expuse tot prin at.button
    at.button[0].click().run()

    assert at.error[0].value == "Completează emailul și parola."
