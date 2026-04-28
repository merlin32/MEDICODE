import sqlite3
from db_connection import DatabaseConnection

def proceseaza_si_salveaza_buletin(id_utilizator, sex_utilizator, data_recoltare, lista_analize_extrase):
    db = DatabaseConnection()
    conn = db.connection
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    biomarkeri_salvati = []

    try:
        # 1. Creare sesiune nouă în tabela Analize
        cursor.execute("""
            INSERT INTO Analize (id_utilizator, data_recoltare, tip_sesiune)
            VALUES (?, ?, ?)
        """, (id_utilizator, data_recoltare, 'Sânge'))
        
        id_sesiune = cursor.lastrowid 

        biomarkeri_procesati_in_sesiune = set()
        
        # 2. Cautare biomarkerii și popularea tabelului Valori_Masurate
        for analiza_ocr in lista_analize_extrase:
            nume_brut_ocr = analiza_ocr['analiza'].lower()
            valoare = analiza_ocr['valoare_numerica']

            cursor.execute("""
                SELECT id_biomarker, nume_biomarker, valoare_min_ref, valoare_max_ref, unitate_masura
                FROM Biomarkeri 
                WHERE ? LIKE '%' || lower(nume_biomarker) || '%'
                AND (sex = ? OR sex = 'I')
            """, (nume_brut_ocr, sex_utilizator))
            
            biomarker_gasit = cursor.fetchone()

            if biomarker_gasit:
                id_bio = biomarker_gasit['id_biomarker']
                
                if id_bio not in biomarkeri_procesati_in_sesiune:
                    v_min = biomarker_gasit['valoare_min_ref']
                    v_max = biomarker_gasit['valoare_max_ref']

                    cursor.execute("""
                        INSERT INTO Valori_Masurate (id_analiza, id_biomarker, valoare_masurata)
                        VALUES (?, ?, ?)
                    """, (id_sesiune, id_bio, valoare))
                    
                    biomarkeri_procesati_in_sesiune.add(id_bio)
                    
                    latime_interval = v_max - v_min
                    marja_galbena = 0.10 * latime_interval # 10% marja pt galben
                    
                    if valoare < v_min:
                        stare = "SCAZUT_ROSU"
                    elif valoare > v_max:
                        stare = "CRESCUT_ROSU"
                    elif valoare <= v_min + marja_galbena:
                        stare = "BORDERLINE_MIN_GALBEN"
                    elif valoare >= v_max - marja_galbena:
                        stare = "BORDERLINE_MAX_GALBEN"
                    else:
                        stare = "OPTIM_VERDE"

                    biomarkeri_salvati.append({
                        "nume": biomarker_gasit['nume_biomarker'],
                        "valoare": valoare,
                        "min": v_min,
                        "max": v_max,
                        "um": biomarker_gasit['unitate_masura'],
                        "stare": stare
                    })

        # Salvare tranzactie în baza de date după procesarea tuturor biomarkerilor
        conn.commit()
        return biomarkeri_salvati

    except Exception as e:
        conn.rollback()
        raise Exception(f"Eroare la inserarea în baza de date: {e}")