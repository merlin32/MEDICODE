import sqlite3
import re
from src.backend.db.db_connection import DatabaseConnection


def proceseaza_si_salveaza_buletin(
    id_utilizator, sex_utilizator, data_recoltare, lista_analize_extrase, nume_clinica
):
    db = DatabaseConnection()
    conn = db.connection
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    biomarkeri_salvati = []

    try:
        # 1. Găsim sau inserăm clinica în tabela Clinici conform noului model SQL
        cursor.execute(
            "SELECT id_clinica FROM Clinici WHERE lower(nume_clinica) = lower(?)",
            (nume_clinica.strip(),),
        )
        clinica_row = cursor.fetchone()

        if clinica_row:
            id_clinica = clinica_row["id_clinica"]
        else:
            cursor.execute(
                "INSERT INTO Clinici (nume_clinica) VALUES (?)", (nume_clinica.strip(),)
            )
            id_clinica = cursor.lastrowid

        # 2. Creare sesiune nouă în tabela Analize folosind id_clinica obligatoriu
        cursor.execute(
            """
            INSERT INTO Analize (id_utilizator, id_clinica, data_recoltare)
            VALUES (?, ?, ?)
            """,
            (id_utilizator, id_clinica, data_recoltare),
        )

        id_sesiune = cursor.lastrowid
        biomarkeri_procesati_in_sesiune = set()

        # 3. Căutare biomarkeri și popularea tabelului Valori_Masurate
        for analiza_ocr in lista_analize_extrase:
            nume_brut_ocr = analiza_ocr["analiza"].lower()
            valoare = analiza_ocr["valoare_numerica"]

            # Interogăm catalogul de Biomarkeri (fără filtrul b.sex care a fost eliminat din SQL)
            cursor.execute(
                """
                SELECT id_biomarker, nume_biomarker, ref_min, ref_max
                FROM Biomarkeri 
                WHERE ? LIKE '%' || lower(nume_biomarker) || '%'
                """,
                (nume_brut_ocr,),
            )

            biomarker_gasit = cursor.fetchone()

            if biomarker_gasit:
                id_bio = biomarker_gasit["id_biomarker"]

                if id_bio not in biomarkeri_procesati_in_sesiune:
                    v_min = biomarker_gasit["ref_min"]
                    v_max = biomarker_gasit["ref_max"]

                    # Extragem unitatea de măsură (ex: "126 mg/dL" -> "mg/dL") pentru câmpul NOT NULL unit_mas
                    val_extrasa = analiza_ocr["valoare_extrasa"]
                    match_um = re.search(
                        r"[\d.,<>\s]+([a-zA-Z/%^0-9\s\-]+)", val_extrasa
                    )
                    unit_mas = match_um.group(1).strip() if match_um else "U/M"
                    if not unit_mas:
                        unit_mas = "U/M"

                    # Inserăm în Valori_Masurate folosind denumirile exacte din creareBD.sql
                    cursor.execute(
                        """
                        INSERT INTO Valori_Masurate (id_sesiune, id_biomarker, val_mas, unit_mas)
                        VALUES (?, ?, ?, ?)
                        """,
                        (id_sesiune, id_bio, valoare, unit_mas),
                    )

                    biomarkeri_procesati_in_sesiune.add(id_bio)

                    latime_interval = v_max - v_min
                    marja_galbena = 0.10 * latime_interval

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

                    biomarkeri_salvati.append(
                        {
                            "nume": biomarker_gasit["nume_biomarker"],
                            "valoare": valoare,
                            "min": v_min,
                            "max": v_max,
                            "um": unit_mas,
                            "stare": stare,
                        }
                    )

        conn.commit()
        return biomarkeri_salvati

    except Exception as e:
        conn.rollback()
        raise Exception(f"Eroare la inserarea în baza de date: {e}")
