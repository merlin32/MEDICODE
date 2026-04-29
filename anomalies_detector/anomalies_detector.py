import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db_connection import DatabaseConnection
import json
import sqlite3


def genereaza_raport_json(fisier_iesire="biomarkeri_problematici.json"):

    # Conectarea la baza de date folosind clasa Singleton din db_connection.py

    db_instanta = DatabaseConnection()
    conn = db_instanta.connection
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query care face join intre toate tabelele si filtreaza sexul conform cerintei
    # Folosim conditia: (sex_biomarker == sex_utilizator) SAU (sex_biomarker == 'I')

    query = """
    SELECT 
        u.id_utilizator, 
        a.id_sesiune, 
        b.nume_biomarker, 
        vm.valoare_masurata, 
        b.valoare_min_ref, 
        b.valoare_max_ref
    FROM Utilizatori u
    JOIN Analize a ON u.id_utilizator = a.id_utilizator
    JOIN Valori_Masurate vm ON a.id_sesiune = vm.id_analiza
    JOIN Biomarkeri b ON vm.id_biomarker = b.id_biomarker
    WHERE (b.sex = u.sex OR b.sex = 'I')
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    # Structura intermediara pentru a grupa datele: { id_utilizator: { id_sesiune: [nume_biomarkeri] } }
    rezultate = {}

    for row in rows:
        val = row["valoare_masurata"]
        v_min = row["valoare_min_ref"]
        v_max = row["valoare_max_ref"]

        # Verificam daca valoarea este in afara intervalului
        if val < v_min or val > v_max:
            u_id = row["id_utilizator"]
            s_id = row["id_sesiune"]

            if val < v_min:
                procent = ((v_min - val) / abs(v_min)) * 100 if v_min != 0 else 0
            else:
                procent = ((val - v_max) / abs(v_max)) * 100 if v_max != 0 else 0

            if u_id not in rezultate:
                rezultate[u_id] = {}
            if s_id not in rezultate[u_id]:
                rezultate[u_id][s_id] = []

            rezultate[u_id][s_id].append(
                {
                    "nume": row["nume_biomarker"],
                    "valoare_masurata": val,
                    "interval_referinta": f"{v_min} - {v_max}",
                    "deviere": f"{round(procent, 2)}%",
                }
            )

    # Transformam structura intr-o lista formatata pentru JSON conform cerintei
    output_final = []
    for u_id, sesiuni in rezultate.items():
        utilizator_data = {"id_utilizator": u_id, "analize_problematice": []}
        for s_id, biomarkeri in sesiuni.items():
            utilizator_data["analize_problematice"].append(
                {"id_sesiune": s_id, "biomarkeri_alerta": biomarkeri}
            )
        output_final.append(utilizator_data)

    # Scrierea in fisier JSON
    with open(fisier_iesire, "w", encoding="utf-8") as f:
        json.dump(output_final, f, indent=4, ensure_ascii=False)

    print(f"Raportul a fost generat cu succes in {fisier_iesire}")


# Rulare
if __name__ == "__main__":
    genereaza_raport_json()
