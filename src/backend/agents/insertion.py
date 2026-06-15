import json
import os
import re
import sqlite3
import sys

# --- FIX PENTRU IMPORTURI ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# ----------------------------

from openai import OpenAI
from src.backend.db.db_connection import DatabaseConnection

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
MODEL_NAME = "hf.co/gguf-org/medgemma-1.5-4b-it-gguf:Q4_0"


def genereaza_afectiuni_cu_ai(numar_afectiuni: int = 10) -> list:
    print(f"[🤖] Cerem lui MedGemma să genereze {numar_afectiuni} afecțiuni...")

    prompt = f"""
    Ești un expert medical. Trebuie să populezi un dicționar medical pentru o bază de date.
    Generează exact {numar_afectiuni} afecțiuni medicale variate (metabolice, hepatice, renale, cardiovasculare etc.).
    
    REGULI STRICTE:
    1. Răspunde EXCLUSIV cu un array JSON valid. Fără nicio introducere, fără niciun comentariu.
    2. Structura fiecărui obiect JSON trebuie să fie exact aceasta:
    {{
        "nume_afectiune": "Numele Bolii",
        "descriere_generala": "O descriere medicală clară, de 1-2 propoziții, în limba română."
    }}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": "Răspunzi doar cu JSON pur. Fără markdown, fără text adițional.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,  # O temperatură mică face modelul mai strict și previzibil
        )

        raspuns_brut = response.choices[0].message.content

        # --- Curățarea și Extragerea JSON-ului ---
        # În cazul în care modelul adaugă ```json ... ``` din reflex
        match = re.search(r"\[.*\]", raspuns_brut, re.DOTALL)
        if match:
            json_text = match.group(0)
        else:
            json_text = raspuns_brut

        lista_afectiuni = json.loads(json_text)
        return lista_afectiuni

    except Exception as e:
        print(f"[❌] Eroare la generarea cu AI: {e}")
        return []


def populeaza_tabela_afectiuni():
    afectiuni_noi = genereaza_afectiuni_cu_ai(10)

    if not afectiuni_noi:
        print("Nu s-a putut genera lista. Renunțăm la inserare.")
        return

    conn = DatabaseConnection().connection
    cursor = conn.cursor()

    inserate = 0
    erori = 0

    print("[💾] Începem inserarea în baza de date...")
    for af in afectiuni_noi:
        try:
            cursor.execute(
                "INSERT INTO Afectiuni (nume_afectiune, descriere_generala) VALUES (?, ?)",
                (af["nume_afectiune"].strip(), af["descriere_generala"].strip()),
            )
            inserate += 1
        except sqlite3.IntegrityError:
            # Dacă rulăm scriptul de 2 ori și boala deja există
            print(f" ⚠️ Afecțiunea '{af['nume_afectiune']}' există deja. O sărim.")
            erori += 1
        except Exception as e:
            print(f" ❌ Eroare la inserare {af['nume_afectiune']}: {e}")
            erori += 1

    conn.commit()
    print("=" * 40)
    print(f"✅ S-au inserat cu succes {inserate} afecțiuni noi!")
    print(f"⚠️ Omise (duplicate/erori): {erori}")
    print("=" * 40)


if __name__ == "__main__":
    populeaza_tabela_afectiuni()
