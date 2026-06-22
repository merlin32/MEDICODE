import os
import re
import sys
import sqlite3
import requests
import datetime

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

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
                   Exemplu: **SIDEREMIE [ATENȚIE - VALOARE MODIFICATĂ]**.
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
        "options": {"temperature": 0.4},
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
    print(f"[🤖] Standardizăm termenul și generăm descrierea: {termen_brut}...")

    # Cerem AI-ului să returneze ambele informații structurate JSON
    prompt = f"""
          Ești un medic expert. Standardizează afecțiunea pacientului într-un singur diagnostic medical oficial, concis, în limba română.
          De asemenea, generează o descriere generală a acestei afecțiuni (2-3 propoziții clare, pe înțelesul pacientului).
          
          Termen introdus de pacient: "{termen_brut}"
          
          REGULI STRICTE: 
          1. Returnează STRICT un obiect JSON valid, fără niciun alt text înainte sau după.
          2. Fără caractere '*' (asterisc) și fără formatare markdown.
          3. Folosește exact această structură:
          {{
                    "diagnostic": "Numele Oficial",
                    "descriere": "Descrierea afecțiunii..."
          }}
          """

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "Răspunzi exclusiv cu obiectul JSON solicitat, fără tag-uri de gândire.",
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.1},
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        if response.status_code == 200:
            raspuns_brut = response.json()["message"]["content"]

            if "</think>" in raspuns_brut:
                raspuns_brut = raspuns_brut.split("</think>")[-1]

            raspuns_curat = (
                raspuns_brut.replace("*", "")
                .replace("```json", "")
                .replace("```", "")
                .strip()
            )

            import json

            try:
                match = re.search(r"\{.*\}", raspuns_curat, re.DOTALL)
                if match:
                    raspuns_curat = match.group(0)

                date_json = json.loads(raspuns_curat)
                diagnostic_final = date_json.get(
                    "diagnostic", termen_brut.strip().capitalize()
                )
                descriere_finala = date_json.get("descriere", "")

                if descriere_finala:
                    db_conn = DatabaseConnection().connection
                    db_conn.execute(
                        "INSERT INTO Afectiuni (nume_afectiune, descriere_generala) VALUES (?, ?) "
                        "ON CONFLICT(nume_afectiune) DO UPDATE SET descriere_generala = ?",
                        (diagnostic_final, descriere_finala, descriere_finala),
                    )
                    db_conn.commit()

                return diagnostic_final

            except json.JSONDecodeError:
                print(f"[❌] Eroare parsare JSON. Răspuns AI: {raspuns_curat}")
                return termen_brut.strip().capitalize()
        else:
            return termen_brut.strip().capitalize()
    except Exception as e:
        print(f"[❌] Eroare la normalizarea AI: {e}")
        return termen_brut.strip().capitalize()
