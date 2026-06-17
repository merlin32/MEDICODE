import os
import re
import sys
import sqlite3
import requests
import datetime

# --- FIX PENTRU IMPORTURI ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ----------------------------

from src.backend.db.db_connection import DatabaseConnection  # noqa: E402

MODEL_NAME = "hf.co/gguf-org/medgemma-1.5-4b-it-gguf:Q4_0"
OLLAMA_URL = "http://localhost:11434/api/chat"


def ruleaza_analiza_avansata(
    pacient_id: int, id_sesiune: int, greutate: float, inaltime: float
) -> str:
    print(f"[🤖] Construim contextul clinic avansat pentru sesiunea {id_sesiune}...")

    db = DatabaseConnection()
    conn = db.connection
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Preluăm datele demografice (INCLUSIV Nume și Prenume)
    cursor.execute(
        "SELECT nume, prenume, sex, data_nasterii FROM Utilizatori WHERE id_utilizator = ?",
        (pacient_id,),
    )
    user_row = cursor.fetchone()

    sex_biologic = "Nespecificat"
    varsta = "Nespecificată"
    nume_pacient = "pacient"

    if user_row:
        nume_pacient = f"{user_row['prenume']} {user_row['nume']}"
        sex_biologic = "Masculin" if user_row["sex"] == "M" else "Feminin"
        if user_row["data_nasterii"]:
            try:
                data_nas = datetime.datetime.strptime(
                    user_row["data_nasterii"], "%Y-%m-%d"
                ).date()
                azi = datetime.date.today()
                varsta = (
                    azi.year
                    - data_nas.year
                    - ((azi.month, azi.day) < (data_nas.month, data_nas.day))
                )
            except Exception as e:
                print(f"[⚠️] Eroare la calculul vârstei: {e}")

    # 2. Preluăm biomarkerii
    cursor.execute(
        """
        SELECT b.nume_biomarker, vm.val_mas, vm.unit_mas, b.ref_min, b.ref_max, b.is_bool
        FROM Valori_Masurate vm
        JOIN Biomarkeri b ON vm.id_biomarker = b.id_biomarker
        WHERE vm.id_sesiune = ?
    """,
        (id_sesiune,),
    )
    randuri_analize = cursor.fetchall()

    # 3. Preluăm afecțiunile curente
    cursor.execute(
        "SELECT nume_afectiune, status FROM Utilizator_Afectiune WHERE id_utilizator = ?",
        (pacient_id,),
    )
    randuri_afectiuni = cursor.fetchall()

    # 4. Formatăm biomarkerii
    text_biomarkeri = ""
    for r in randuri_analize:
        if r["is_bool"] == 1:
            val_status = "Pozitiv/DA" if r["val_mas"] == 1.0 else "Negativ/NU"
            ref_status = "Pozitiv/DA" if r["ref_min"] == 1.0 else "Negativ/NU"
            text_biomarkeri += (
                f"- {r['nume_biomarker']}: {val_status} (Referință: {ref_status})\n"
            )
        else:
            text_biomarkeri += f"- {r['nume_biomarker']}: {r['val_mas']} {r['unit_mas']} (Referință: {r['ref_min']} - {r['ref_max']})\n"

    text_afectiuni = "\n".join(
        [f"- {af['nume_afectiune']}" for af in randuri_afectiuni]
    )
    imc = greutate / ((inaltime / 100) ** 2) if inaltime > 0 else 0.0

    # 5. Mega-Prompt-ul Complet Revizuit
    prompt_complex = f"""
    Sunteți MEDICODE, un asistent medical AI empatic și supraspecializat. Te rog să analizezi aceste rezultate pentru a-l ajuta pe pacient să înțeleagă mai bine starea sa de sănătate.

    CONTEXT PACIENT:
    - Nume: {nume_pacient}
    - Sex biologic: {sex_biologic}
    - Vârstă: {varsta} ani
    - IMC: {imc:.2f}

    DOSAR MEDICAL (Afecțiuni cunoscute):
    {text_afectiuni if text_afectiuni else "Fără istoric de afecțiuni."}

    REZULTATE ANALIZE:
    {text_biomarkeri}

    REGULI STRICTE DE REDACTARE:
    1. TON ȘI FORMĂ: Scrie în limba română impecabilă, naturală și caldă, la persoana a II-a de politețe. Începe cu "Bună ziua, domnule/doamnă {nume_pacient}". FĂRĂ emoji-uri (deoarece PDF-ul nu le poate randa).
    2. EVIDENȚIEREA ANOMALIILOR: Când analizezi un biomarker care se află în afara intervalului de referință (sau la limită), ești OBLIGAT să îl scrii cu MAJUSCULE, între asteriscuri (pentru bold) și să adaugi eticheta vizuală [⚠️ ATENȚIE - VALOARE MODIFICATĂ]. 
       Exemplu: **SIDEREMIE [⚠️ ATENȚIE - VALOARE MODIFICATĂ]**.
    3. SECȚIUNEA '🧬 ANALIZĂ ȘI CORELĂRI': Trebuie să fie foarte detaliată și personalizată. Explică biomarkerii anormali grupat (nu liste separate). Corelează imediat aceste valori modificate cu afecțiunile din Dosarul Medical ({text_afectiuni}). Dacă există riscul de a dezvolta alte afecțiuni (ex: pre-diabet, anemie cronică) din cauza acestor anomalii, explică clar și pe larg mecanismul.
    4. SECȚIUNEA '📋 RECOMANDĂRI': Trebuie să fie exhaustivă. Oferă sfaturi amănunțite despre: dietă (alimente de evitat/consumat), stil de viață (activitate fizică, somn) și care sunt pașii medicali următori (ce specialist ar trebui să consulte).
    5. FĂRĂ INFORMAȚII REDUNDANTE: Nu crea secțiuni separate de "Valori" și "Corelări", îmbină-le într-o singură poveste clinică. Fără textul de disclaimer la final (este adăugat de noi automat).
    """

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "Ești un medic expert, detaliat și extrem de corect gramatical. Nu afișa tag-uri <think>.",
            },
            {"role": "user", "content": prompt_complex},
        ],
        "stream": False,
        "options": {
            "temperature": 0.4
        },  # Ușor crescută pentru a-i da voie să fie mai descriptiv și fluent
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        if response.status_code == 200:
            raspuns_brut = response.json()["message"]["content"]
            return re.sub(
                r"<think>.*?</think>", "", raspuns_brut, flags=re.DOTALL
            ).strip()
        return "⚠️ Eroare la generarea raportului AI."
    except Exception as e:
        return f"⚠️ Eroare conexiune Ollama: {e}"


def normalizeaza_termen_medical(termen_brut: str) -> str:
    print(f"[🤖] Standardizăm termenul medical: {termen_brut}...")

    # Am eliminat mențiunea negativă despre <think> care îl deruta și am impus un output strict
    prompt = f"""
    Ești un medic expert în terminologia clinică.
    Standardizează afecțiunea pacientului într-un singur diagnostic medical oficial, concis, în limba română.
    
    Exemple de normalizare:
    - "diabet tip 2" -> "Diabet Zaharat Tip 2"
    - "tensiune mare" -> "Hipertensiune Arterială"
    - "RACEALA" -> "Infecție de tract respirator superior"
    - "durere de cap" -> "Cefalee"
    - "colesterol marit" -> "Hipercolesterolemie"
    
    Termen introdus de pacient: "{termen_brut}"
    
    REGULI STRICTE: 
    1. Returnează STRICT numele oficial al afecțiunii pe un singur rând.
    2. Fără alte explicații, introduceri, pași de gândire sau punct la final.
    3. Doar diagnosticul, capitalizat corect.
    """

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "Ești un API de normalizare. Răspunzi doar cu diagnosticul standardizat, nimic altceva.",
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {
            "temperature": 0.0  # Setăm temperatura la absolut zero pentru a opri halucinațiile
        },
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        if response.status_code == 200:
            raspuns_brut = response.json()["message"]["content"]

            # --- NOUA LOGICĂ INFAILIBILĂ DE CURĂȚARE ---
            # 1. Dacă a pus ambele tag-uri, luăm ce e DUPĂ tag-ul de închidere
            if "</think>" in raspuns_brut:
                raspuns_curat = raspuns_brut.split("</think>")[-1]
            # 2. Dacă a deschis tag-ul dar a uitat să îl închidă (eroarea ta curentă), luăm doar ultima linie de text!
            elif "<think>" in raspuns_brut:
                linii = [
                    linie.strip() for linie in raspuns_brut.split("\n") if linie.strip()
                ]
                raspuns_curat = linii[-1] if linii else termen_brut
            else:
                raspuns_curat = raspuns_brut

            # 3. Curățare finală de caractere și cuvinte parazit adăugate de model ("Yes.", "Da.")
            raspuns_curat = re.sub(
                r"^(Yes\.|Da\.|Answer:)\s*",
                "",
                raspuns_curat.strip(),
                flags=re.IGNORECASE,
            )
            raspuns_curat = raspuns_curat.strip("'\". \n\t")

            # 4. Fallback de siguranță: dacă rezultatul e prea lung (a eșuat complet), returnăm termenul original
            if not raspuns_curat or len(raspuns_curat) > 50:
                return termen_brut.strip().capitalize()

            return raspuns_curat
        else:
            return termen_brut.strip().capitalize()
    except Exception as e:
        print(f"[❌] Eroare la normalizarea AI: {e}")
        return termen_brut.strip().capitalize()
