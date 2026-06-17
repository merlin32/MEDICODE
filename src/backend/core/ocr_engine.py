import os
import re
import tempfile
import pdfplumber
from paddleocr import PaddleOCR

from src.backend.core.image_processor import curata_imagine_pentru_ocr

os.environ["FLAGS_enable_pir_api"] = "0"
os.environ["FLAGS_use_mkldnn"] = "0"

print("[0/3] Incarcare modele locale PaddleOCR (pentru Fallback)...")
ocr = PaddleOCR(use_angle_cls=True, lang="ro")


def extrage_text_nativ_pdf(cale_pdf):
    """Extrage textul digital nativ din PDF-uri (Super rapid)."""
    text_brut = ""
    try:
        with pdfplumber.open(cale_pdf) as pdf:
            for page in pdf.pages:
                text_pagina = page.extract_text(layout=True)
                if text_pagina:
                    text_brut += text_pagina + "\n"
    except Exception as e:
        print(f"Eroare la citirea nativa a PDF-ului: {e}")
    return text_brut


def extrage_text_cu_paddle_local(cale_imagine):
    """Fallback 1: Trage textul din poză offline dacă AI-ul pică."""
    text_brut = ""

    print(f"[⚙️ OCR Local] Aplicăm filtre optice pe: {cale_imagine}...")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        cale_curatata = tmp.name

    try:
        curata_imagine_pentru_ocr(cale_imagine, cale_curatata)

        res = ocr.ocr(cale_curatata)

        if res and res[0] is not None:
            cutii = []
            for linie in res[0]:
                coords = linie[0]
                cutii.append(
                    {
                        "y": sum(p[1] for p in coords) / 4.0,
                        "x": min(p[0] for p in coords),
                        "text": linie[1][0],
                    }
                )

            if cutii:
                cutii = sorted(cutii, key=lambda c: c["y"])
                randuri = [[cutii[0]]]
                for c in cutii[1:]:
                    if abs(c["y"] - randuri[-1][-1]["y"]) < 10:
                        randuri[-1].append(c)
                    else:
                        randuri.append([c])

                for rand in randuri:
                    rand = sorted(rand, key=lambda c: c["x"])
                    text_brut += " ".join(c["text"].strip() for c in rand) + "\n"

    finally:
        if os.path.exists(cale_curatata):
            os.remove(cale_curatata)

    return text_brut


def extrage_date_structurate_local(text_brut):
    """Fallback 2: Parsează textul folosind reguli (Regex) offline."""
    rezultate = []
    linii = [linie.strip() for linie in text_brut.split("\n") if linie.strip()]
    nume_in_asteptare = ""

    BAD_WORDS = [
        "SPITAL",
        "CLINIC",
        "TEL",
        "MAIL",
        "PROGRAM",
        "CNP",
        "VARSTA",
        "PAGINA",
        "ADRESA",
    ]

    for linie in linii:
        upper_line = linie.upper()
        if any(bad in upper_line for bad in BAD_WORDS):
            continue

        m_range = re.search(r"(\d+[\.,]?\d*)\s*[-_~/]\s*(\d+[\.,]?\d*)", linie)
        if m_range:
            ref_min = float(m_range.group(1).replace(",", "."))
            ref_max = float(m_range.group(2).replace(",", "."))
            left_part = linie[: m_range.start()] + linie[m_range.end() :]
        else:
            continue

        tokens = left_part.split()
        val_idx, valoare_num = -1, None

        for idx in range(len(tokens) - 1, -1, -1):
            if re.match(r"^[-<>]?\d+[\.,]?\d*[%]?$", tokens[idx]):
                try:
                    valoare_num = float(
                        re.sub(r"[^\d\.\-]", "", tokens[idx].replace(",", "."))
                    )
                    val_idx = idx
                    break
                except ValueError:
                    pass

        if val_idx != -1 and valoare_num is not None:
            nume = " ".join(tokens[:val_idx])
            unitate = " ".join(tokens[val_idx + 1 :]).strip()

            nume = re.sub(
                r"^[\d\.\*\-\s]+", "", (nume_in_asteptare + " " + nume)
            ).strip()

            if len(nume) > 2:
                rezultate.append(
                    {
                        "analiza": nume,
                        "valoare_numerica": valoare_num,
                        "unitate_masura": unitate,
                        "ref_min": ref_min,
                        "ref_max": ref_max,
                        "is_bool": 0,
                    }
                )
            nume_in_asteptare = ""
        else:
            nume_in_asteptare += " " + linie

    return rezultate
