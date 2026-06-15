import json
import os
import re
import sys

# --- FIX PENTRU IMPORTURI ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ----------------------------

from openai import OpenAI  # noqa: E402
from src.backend.db.db_connection import DatabaseConnection  # noqa: E402

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODEL_NAME = "hf.co/gguf-org/medgemma-1.5-4b-it-gguf:Q4_0"


def cauta_clinica_si_intervale_sql(text_ocr: str):
    """Interogare SQL pură pentru a găsi datele clinicii."""
    conn = DatabaseConnection().get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, nume_clinica FROM clinici")
        clinici = cursor.fetchall()
        for clinica_id, nume in clinici:
            if nume.lower() in text_ocr.lower():
                cursor.execute(
                    """
                    SELECT biomarker, interval_minim, interval_maxim, unitate_masura 
                    FROM intervale_referinta_clinica WHERE clinica_id = ?
                """,
                    (clinica_id,),
                )
                return {r[0]: f"{r[1]}-{r[2]} {r[3]}" for r in cursor.fetchall()}
    except Exception:
        pass
    return None


def ruleaza_analiza_clinica(pacient_id: int, text_ocr: str) -> str:
    print("[🤖] MedGemma analizează datele brute...")

    # PASUL 1: Solicităm AI-ului să decidă dacă are nevoie de baza de date
    # Folosim un prompt care forțează modelul să ceară date dacă nu le are
    prompt_initial = f"""
    Sunteți un medic expert. Analizați textul de mai jos extras dintr-un buletin de analize.
    Dacă textul NU conține intervale de referință clare pentru toți biomarkerii, răspundeți EXACT cu textul: SEARCH_DATABASE
    Dacă aveți deja toate informațiile, generați direct raportul clinic.

    TEXT ANALIZE:
    {text_ocr}
    """

    response = client.chat.completions.create(
        model=MODEL_NAME, messages=[{"role": "user", "content": prompt_initial}]
    )

    decizie_ai = response.choices[0].message.content

    # PASUL 2: Logica de "Manual Tool Calling"
    context_suplimentar = ""
    if "SEARCH_DATABASE" in decizie_ai or "search_database" in decizie_ai:
        print("[🛠️] MedGemma a solicitat acces la baza de date SQL...")
        date_db = cauta_clinica_si_intervale_sql(text_ocr)

        if date_db:
            print("[✅] Date găsite în cache-ul SQL.")
            context_suplimentar = f"\nDATE DIN BAZA DE DATE (INTERVALE DE REFERINȚĂ): {json.dumps(date_db)}"
        else:
            print("[⚠️] Clinica nu a fost găsită în baza de date.")
            context_suplimentar = "\nNOTĂ: Clinica nu este în baza de date. Folosește-ți cunoștințele medicale generale pentru intervale standard."

    # PASUL 3: Generarea raportului final cu toate datele la un loc
    print("[🩺] Generare raport clinic final...")
    prompt_final = f"""
    Pe baza acestor date, generează un raport clinic structurat sub formă de tabel (Biomarker, Valoare, Stare, Concluzie).
    
    REGULI STRICTE:
    1. Răspunde DIRECT cu raportul final în limba română.
    2. NU afișa procesul tău de gândire.
    3. NU folosi cuvinte precum "thought", "Here is the thinking process", etc.
    4. Începe direct cu tabelul sau cu salutul medical.
    
    DATE OCR: {text_ocr}
    {context_suplimentar}
    """

    final_res = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": "Ești un medic specialist de elită. Ești scurt, la obiect și nu îți expui procesul de gândire pacienților.",
            },
            {"role": "user", "content": prompt_final},
        ],
    )

    raspuns_brut = final_res.choices[0].message.content

    # --- FILTRU DE SIGURANȚĂ (Post-procesare) ---

    # 1. Eliminăm eventualele tag-uri de <think>...</think> dacă modelul le folosește
    raspuns_curat = re.sub(r"<think>.*?</think>", "", raspuns_brut, flags=re.DOTALL)

    # 2. Dacă modelul tot returnează blocul text "thought... OK.", tăiem tot până la cuvântul cheie de start (sau tabel)
    if "thought" in raspuns_curat.lower()[:50] and "OK." in raspuns_curat:
        # Păstrăm doar ce este după "OK." (finalul raționamentului în cazul tău)
        raspuns_curat = raspuns_curat.split("OK.", 1)[-1].strip()

    return raspuns_curat.strip()


if __name__ == "__main__":
    text_test = "Laborator: SYNEVO. Glicemie: 126 mg/dL. TGO: 45 U/L."
    print(ruleaza_analiza_clinica(999, text_test))
