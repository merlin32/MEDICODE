import sqlite3
from src.backend.db.db_connection import DatabaseConnection


def proceseaza_si_salveaza_buletin(
    id_utilizator,
    data_recoltare,
    lista_analize_extrase,
    nume_clinica,
    upload_hash=None,
):
    """
    Procesează și salvează buletinul de analize în baza de date.

    Pași:
    1. Creează o nouă analiză (sesiune) asociată utilizatorului sau reia una incompletă
    2. Verifică dacă clinica există; dacă nu, o creează
    3. Verifică upload_hash pentru duplicate finale
    4. Procesează biomarkerii:
       a) Verifică dacă biomarkerul există în Biomarkeri
       b) Dacă există, salvează măsurătorile în Valori_Masurate
       c) Dacă nu există, creează biomarkerul și apoi salvează măsurătorile
    5. Returnează id_sesiune și dacă datele au fost reutilizate ca duplicate finale
    """
    db = DatabaseConnection()
    conn = db.connection
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    biomarkeri_salvati = []

    try:
        # 1. Gestionarea clinicii
        cursor.execute(
            """
            SELECT id_clinica FROM Clinici WHERE nume_clinica = ?
            """,
            (nume_clinica,),
        )
        clinica_gasita = cursor.fetchone()

        if clinica_gasita:
            id_clinica = clinica_gasita["id_clinica"]
        else:
            # Clinica nu există, deci o creăm
            cursor.execute(
                """
                INSERT INTO Clinici (nume_clinica) VALUES (?)
                """,
                (nume_clinica,),
            )
            id_clinica = cursor.lastrowid

        # 2. Căutăm o sesiune existentă pentru același upload_hash.
        # Dacă există și a fost finalizată, o blocăm ca duplicat final.
        sesiune_reutilizata = False
        sesiune_id_reutilizata = None

        if upload_hash:
            cursor.execute(
                """
                SELECT id_sesiune, finalizata FROM Analize
                WHERE upload_hash = ? AND id_utilizator = ?
                """,
                (upload_hash, id_utilizator),
            )
            analiza_existenta = cursor.fetchone()

            if analiza_existenta:
                if analiza_existenta["finalizata"] == 1:
                    conn.rollback()
                    return [], True, analiza_existenta["id_sesiune"], False
                id_sesiune = analiza_existenta["id_sesiune"]
                sesiune_reutilizata = True
                sesiune_id_reutilizata = id_sesiune
                cursor.execute(
                    "DELETE FROM Valori_Masurate WHERE id_sesiune = ?",
                    (id_sesiune,),
                )
                cursor.execute(
                    """
                    UPDATE Analize
                    SET id_utilizator = ?, id_clinica = ?, data_recoltare = ?, finalizata = 0
                    WHERE id_sesiune = ?
                    """,
                    (id_utilizator, id_clinica, data_recoltare, id_sesiune),
                )

        if not upload_hash or not sesiune_reutilizata:
            cursor.execute(
                """
                INSERT INTO Analize (id_utilizator, id_clinica, data_recoltare, upload_hash, finalizata)
                VALUES (?, ?, ?, ?, 0)
                """,
                (id_utilizator, id_clinica, data_recoltare, upload_hash),
            )
            id_sesiune = cursor.lastrowid

        # 3. Procesarea biomarkerilor
        for analiza_ocr in lista_analize_extrase:
            nume_biomarker = analiza_ocr["analiza"]
            valoare_masurata = analiza_ocr["valoare_numerica"]
            # Unitatea de măsură va fi extrasă din referință sau din valoare_extrasa
            # Pentru acum, presupunem că este deja disponibilă
            unitate_masura = analiza_ocr.get("unitate_masura", "")

            # Preluare date extrase din buletinul de analize
            ref_min = analiza_ocr.get("ref_min") or 0.0
            ref_max = analiza_ocr.get("ref_max") or 100.0
            is_bool = analiza_ocr.get("is_bool") or 0

            # 4.a) Verificare dacă biomarkerul există deja în Biomarkeri
            # Se verifică toate coloanele: nume_biomarker, ref_min, ref_max, is_bool
            cursor.execute(
                """
                SELECT id_biomarker FROM Biomarkeri 
                WHERE trim(lower(nume_biomarker)) = trim(lower(?))
                  AND ref_min = ?
                  AND ref_max = ?
                  AND is_bool = ?
                """,
                (nume_biomarker, ref_min, ref_max, is_bool),
            )
            biomarker_gasit = cursor.fetchone()

            if biomarker_gasit:
                # 4.b) Biomarkerul cu toate caracteristicile același există, deci salvez măsurătorile
                id_biomarker = biomarker_gasit["id_biomarker"]
            else:
                # 4.c) Biomarkerul (cu aceste caracteristici) nu există, deci il creez mai întâi
                cursor.execute(
                    """
                    INSERT INTO Biomarkeri (nume_biomarker, ref_min, ref_max, is_bool)
                    VALUES (?, ?, ?, ?)
                    """,
                    (nume_biomarker, ref_min, ref_max, is_bool),
                )
                id_biomarker = cursor.lastrowid

            # Inserare valorile măsurate în laborator în Valori_Masurate
            cursor.execute(
                """
                INSERT OR IGNORE INTO Valori_Masurate (id_sesiune, id_biomarker, val_mas, unit_mas)
                VALUES (?, ?, ?, ?)
                """,
                (id_sesiune, id_biomarker, valoare_masurata, unitate_masura),
            )

            # Adaugare în lista de rezultate pentru returnare
            biomarkeri_salvati.append(
                {
                    "id_biomarker": id_biomarker,
                    "nume": nume_biomarker,
                    "valoare": valoare_masurata,
                    "unitate": unitate_masura,
                    "min": ref_min,
                    "max": ref_max,
                    "is_bool": is_bool,
                }
            )

        # Salvare tranzacție în baza de date
        conn.commit()
        return biomarkeri_salvati, sesiune_reutilizata, id_sesiune, True

    except Exception as e:
        conn.rollback()
        if "id_sesiune" in locals() and upload_hash and sesiune_id_reutilizata is None:
            cursor.execute(
                "DELETE FROM Analize WHERE id_sesiune = ?",
                (id_sesiune,),
            )
            conn.commit()
        raise Exception(f"Eroare la inserarea în baza de date: {e}")


def finalizeaza_analiza(id_sesiune, raport_text=None):
    db = DatabaseConnection()
    conn = db.connection
    cursor = conn.cursor()

    try:
        if raport_text:
            cursor.execute(
                "UPDATE Analize SET finalizata = 1, raport_text = ? WHERE id_sesiune = ?",
                (raport_text, id_sesiune),
            )
        else:
            cursor.execute(
                "UPDATE Analize SET finalizata = 1 WHERE id_sesiune = ?",
                (id_sesiune,),
            )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        raise Exception(f"Eroare la finalizarea analizei: {e}")


def asociere_afectiune(nume_afectiune, descriere_generala, id_utilizator, status):
    """
    Realizează asocierea unei afecțiuni cu un utilizator.

    Pași:
    1. Verifică dacă afecțiunea există în tabelul Afectiuni
    2. Dacă existe: salvează numele și creează asocierea în Utilizator_Afectiuni
    3. Dacă nu existe: inserează în Afectiuni, apoi creează asocierea
    """
    db = DatabaseConnection()
    conn = db.connection
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # 1. Verificare dacă afecțiunea există
        cursor.execute(
            "SELECT nume_afectiune FROM Afectiuni WHERE trim(lower(nume_afectiune)) = trim(lower(?))",
            (nume_afectiune,),
        )
        afectiune_gasita = cursor.fetchone()

        if not afectiune_gasita:
            # Inserez afecțiunea dacă nu există
            cursor.execute(
                "INSERT INTO Afectiuni (nume_afectiune, descriere_generala) VALUES (?, ?)",
                (nume_afectiune, descriere_generala),
            )
            nume_afectiune_final = nume_afectiune
        else:
            nume_afectiune_final = afectiune_gasita["nume_afectiune"]

        # 2. Verificare dacă utilizatorul are deja această afecțiune
        cursor.execute(
            "SELECT status FROM Utilizator_Afectiune WHERE id_utilizator = ? AND nume_afectiune = ?",
            (id_utilizator, nume_afectiune_final),
        )
        asociere_existenta = cursor.fetchone()

        if asociere_existenta:
            # 3. Dacă există deja, actualizez statusul
            cursor.execute(
                "UPDATE Utilizator_Afectiune SET status = ? WHERE id_utilizator = ? AND nume_afectiune = ?",
                (status, id_utilizator, nume_afectiune_final),
            )
            mesaj = (
                f"Status afecțiunii '{nume_afectiune_final}' actualizat la '{status}'."
            )
        else:
            # 4. Dacă nu există, o inserez
            cursor.execute(
                "INSERT INTO Utilizator_Afectiune (id_utilizator, nume_afectiune, status) VALUES (?, ?, ?)",
                (id_utilizator, nume_afectiune_final, status),
            )
            mesaj = (
                f"Afecțiunea '{nume_afectiune_final}' asociată cu status '{status}'."
            )

        conn.commit()
        return True, mesaj

    except Exception as e:
        conn.rollback()
        raise Exception(f"Eroare la inserarea afecțiunii: {e}")
