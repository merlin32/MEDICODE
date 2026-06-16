import os
import json
import re
import base64
import requests

api_key = os.environ.get("GEMINI_API_KEY", "")

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"

HEADERS = {"Content-Type": "application/json", "x-goog-api-key": api_key}

PROMPT_AGENT_1 = """
Acționează ca un Agent de Procesare Date Medicale. Sarcina ta este să extragi rezultatele biomarkerilor din documentul furnizat.

REGULI STRICTE:
1. Ignoră complet antetul, datele pacientului, clinicile, adresele, telefoanele, semnăturile, ștampilele sau watermark-urile.
2. Identifică rândurile care conțin un nume de analiză, un rezultat și un interval de referință. Dacă rândul este strâmb sau scris pe două linii, unește-l logic.
3. Ignoră liniile care conțin DOAR referințe generale pe vârste/sexe (ex: "Copii 0-14 zile", "Femei", "Adulți", "Optim", "G1") care nu sunt o analiză în sine.
4. Returnează EXCLUSIV un array JSON valid, fără absolut nicio altă formatare (fără markdown sau ```json), cu această structură exactă:
[
    {
        "analiza": "Numele curat al analizei",
        "valoare_numerica": 10.5,
        "unitate_masura": "mg/dL",
        "ref_min": 5.0,
        "ref_max": 15.0,
        "is_bool": 0
    }
]
- Valorile valoare_numerica, ref_min, ref_max TREBUIE să fie de tip float (ex: 4.5, nu "4,5").
- Dacă e test DA/NU sau Pozitiv/Negativ, pune 'is_bool': 1 și 'valoare_numerica': 1.0 (DA/Pozitiv) sau 0.0 (NU/Negativ). Limitele (ref_min/ref_max) vor fi 0.0 sau 1.0.
- Dacă o limită lipsește (ex: < 10), setează ref_min: 0.0 și ref_max: 10.0.
"""


def curata_json(text_raspuns):
    text_raspuns = re.sub(r"^```json\s*", "", text_raspuns.strip())
    text_raspuns = re.sub(r"\s*```$", "", text_raspuns)

    start_idx = text_raspuns.find("[")
    end_idx = text_raspuns.rfind("]")
    if start_idx != -1 and end_idx != -1:
        text_raspuns = text_raspuns[start_idx : end_idx + 1]

    return json.loads(text_raspuns)


def extrage_date_din_text(text_brut):
    print("🤖 [AGENT 1 - TEXT] Procesăm semantic textul nativ din PDF...")
    try:
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": PROMPT_AGENT_1},
                        {"text": f"TEXT BULETIN:\n{text_brut}"},
                    ]
                }
            ]
        }
        # Adăugăm HEADERS la request
        response = requests.post(GEMINI_URL, headers=HEADERS, json=payload)

        if not response.ok:
            raise Exception(f"Eroare HTTP {response.status_code}: {response.text}")

        response_data = response.json()
        if "candidates" not in response_data or len(response_data["candidates"]) == 0:
            raise Exception(f"Răspuns invalid: {response_data}")

        text_raspuns = response_data["candidates"][0]["content"]["parts"][0]["text"]
        return curata_json(text_raspuns)
    except Exception as e:
        print(f"❌ [AGENT 1 - TEXT] Eroare: {e}")
        raise Exception(f"API Cloud: {str(e)}")


def extrage_date_din_imagine(cale_imagine):
    print(f"👁️ [AGENT 1 - VISION] Analizăm vizual imaginea: {cale_imagine}...")
    try:
        with open(cale_imagine, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

        mime_type = "image/jpeg"
        if cale_imagine.lower().endswith(".png"):
            mime_type = "image/png"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": PROMPT_AGENT_1},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": encoded_string,
                            }
                        },
                    ]
                }
            ]
        }

        response = requests.post(GEMINI_URL, headers=HEADERS, json=payload)

        if not response.ok:
            raise Exception(f"Eroare HTTP {response.status_code}: {response.text}")

        response_data = response.json()
        if "candidates" not in response_data or len(response_data["candidates"]) == 0:
            raise Exception(f"Răspuns invalid: {response_data}")

        text_raspuns = response_data["candidates"][0]["content"]["parts"][0]["text"]
        return curata_json(text_raspuns)
    except Exception as e:
        print(f"❌ [AGENT 1 - VISION] Eroare: {e}")
        raise Exception(f"API Cloud: {str(e)}")
