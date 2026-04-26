import pytesseract
from PIL import Image, ImageEnhance
import re
import json

# Calea catre Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
FISIER_TEST = 'teste/test1.jpeg'

def extrage_text_din_imagine(cale_imagine):
    """Citeste imaginea si scoate textul brut folosind OCR."""
    print(f"[1/3] Incarcare si preprocesare imagine: {cale_imagine}...")
    imagine = Image.open(cale_imagine)
    imagine = imagine.convert('L') # Grayscale
    imagine = ImageEnhance.Contrast(imagine).enhance(2.0) # Contrast
    
    print("[2/3] Rulare motor Tesseract OCR (poate dura cateva secunde)...")
    text_brut = pytesseract.image_to_string(imagine, config=r'--oem 3 --psm 6')
    return text_brut

def extrage_date_structurate(text_brut):
    """Aplica Regex pentru a transforma textul haotic in JSON."""
    print("[3/3] Parsare text cu Expresii Regulate (Regex) imbunatatit...")
    rezultate = []
    
    # Grupul 1 (Nume): Accepta si cifre (0-9) la inceput (ex: "3. Acid uric")
    # Grupul 2 (Valoare): Accepta si simboluri matematice la inceput (ex: "<0.5" sau ">100")
    # Grupul 3 (Restul): Unitatea de masura si intervalul
    pattern = re.compile(r"^([A-Za-z0-9\(\)%\-#\.\* ]{4,})\s+([<>]?[0-9]+[\.,]?[0-9]*)\s+(.*)$")

    for linie in text_brut.split('\n'):
        linie = linie.strip()
        match = pattern.search(linie)
        
        if match:
            nume = match.group(1).strip()
            valoare_str = match.group(2).strip()
            restul = match.group(3).strip()
            
            #Filtram gunoiul
            nume_upper = nume.upper()
            if len(nume) < 4 or "MEDICALE" in nume_upper or "PAGINA" in nume_upper or "BULETIN" in nume_upper:
                continue
            
            #Curatam valoarea ca sa o putem transforma in numar real (float)
            #Daca e "<0.5", o transformam in "0.5" pentru baza de date
            valoare_curatata = valoare_str.replace('<', '').replace('>', '').replace(',', '.')
            
            try:
                valoare_numerica = float(valoare_curatata)
            except ValueError:
                continue
                
            if valoare_numerica == 0.0 and not any(char.isdigit() for char in restul):
                continue
                
            rezultate.append({
                "analiza": nume,
                "valoare_extrasa": valoare_str,
                "valoare_numerica": valoare_numerica, # Valoarea pentru Baza de Date
                "referinta": restul
            })
            
    return rezultate



if __name__ == "__main__":
    print("\nInceput demo")
    try:
        #OCR
        text_extras = extrage_text_din_imagine(FISIER_TEST)
        
        #Parsare
        date_finale = extrage_date_structurate(text_extras)
        
        #Afisare rezultate gata de trimis spre Baza de Date
        print("\n SUCCES! Datele au fost structurate pentru Baza de Date:")
        print(json.dumps(date_finale, indent=4, ensure_ascii=False))
        print("Sfarsit demo\n")
        
    except FileNotFoundError:
        print(f" Eroare: Nu am gasit fisierul '{FISIER_TEST}' in folder.")
    except Exception as e:
        print(f" A aparut o eroare neasteptata: {e}")