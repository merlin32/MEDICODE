import cv2


def verifica_calitate_imagine(cale_imagine):
    """
    Verifică dacă fotografia este suficient de clară (nu e blurată și e bine încadrată).
    Returnează: (este_valida: bool, mesaj_eroare: str)
    """
    img = cv2.imread(cale_imagine)

    if img is None:
        return (
            False,
            "Eroare la citirea imaginii. Asigură-te că fișierul este o poză validă.",
        )

    # alb-negru
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # verificare blur
    scor_blur = cv2.Laplacian(gray, cv2.CV_64F).var()
    limita_blur = 70.0

    if scor_blur < limita_blur:
        return (
            False,
            f"Fotografia este prea blurată (Scor claritate: {scor_blur:.1f} / {limita_blur}). Te rugăm să refaci poza dintr-un unghi stabil.",
        )

    # verificare incadrare
    aria_totala = img.shape[0] * img.shape[1]

    _, binar = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    contururi, _ = cv2.findContours(binar, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contururi:
        cel_mai_mare_contur = max(contururi, key=cv2.contourArea)
        aria_contur = cv2.contourArea(cel_mai_mare_contur)

        if (aria_contur / aria_totala) < 0.15:
            return (
                False,
                "Foaia cu analize nu este încadrată corect. Asigură-te că tabelul ocupă cea mai mare parte din fotografie.",
            )

    return True, "Imaginea este clară și gata de analiză."
