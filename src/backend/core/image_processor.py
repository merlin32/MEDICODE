import cv2
import numpy as np


def corecteaza_inclinarea(imagine):
    """Calculează unghiul textului din imagine și rotește foaia pentru a o îndrepta."""
    gray = cv2.cvtColor(imagine, cv2.COLOR_BGR2GRAY)
    gray_inv = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray_inv, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    coordonate = np.column_stack(np.where(thresh > 0))

    try:
        unghi = cv2.minAreaRect(coordonate)[-1]

        if unghi < -45:
            unghi = -(90 + unghi)
        else:
            unghi = -unghi

        if abs(unghi) < 0.5:
            return imagine

        h, w = imagine.shape[:2]
        centru = (w // 2, h // 2)
        matrice_rotatie = cv2.getRotationMatrix2D(centru, unghi, 1.0)
        imagine_rotita = cv2.warpAffine(
            imagine,
            matrice_rotatie,
            (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE,
        )

        return imagine_rotita
    except Exception:
        return imagine


def curata_imagine_pentru_ocr(cale_fisier_intrare, cale_fisier_iesire):
    """
    Trece imaginea prin bariera de curățare: Îndreptare -> Grayscale -> Blur Moiré -> Binarizare.
    Returnează calea către fișierul curățat.
    """
    # Citim imaginea originală
    img = cv2.imread(cale_fisier_intrare)

    if img is None:
        return cale_fisier_intrare

    # 1. Corectăm înclinarea
    img = corecteaza_inclinarea(img)

    # 2. Conversie la Alb-Negru
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 3. Eliminare Efect Moiré (dungile de la monitor)
    blur = cv2.medianBlur(gray, 3)

    # 4. Binarizare Adaptivă (creează contrast perfect chiar dacă foaia are umbre)
    binarizata = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )

    cv2.imwrite(cale_fisier_iesire, binarizata)
    return cale_fisier_iesire
