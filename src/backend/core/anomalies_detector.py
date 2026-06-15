import json
import sqlite3
from src.backend.db.db_connection import DatabaseConnection


def genereaza_raport_json(fisier_iesire="biomarkeri_problematici.json"):
    db_instanta = DatabaseConnection()
    conn = db_instanta.connection
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query aliniat perfect cu tabela și coloanele din creareBD.sql
    query = """
    SELECT 
        u.id_utilizator, 
        a.id_sesiune, 
        b.nume_biomarker, 
        vm.val_mas, 
        b.ref_min, 
        b.ref_max
    FROM Utilizatori u
    JOIN Analize a ON u.id_utilizator = a.id_utilizator
    JOIN Valori_Masurate vm ON a.id_sesiune = vm.id_sesiune
    JOIN Biomarkeri b ON vm.id_biomarker = b.id_biomarker
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    rezultate = {}

    for row in rows:
        val = row["val_mas"]
        v_min = row["ref_min"]
        v_max = row["ref_max"]

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

    output_final = []
    for u_id, sesiuni in rezultate.items():
        utilizator_data = {"id_utilizator": u_id, "analize_problematice": []}
        for s_id, biomarkeri in sesiuni.items():
            utilizator_data["analize_problematice"].append(
                {"id_sesiune": s_id, "biomarkeri_alerta": biomarkeri}
            )
        output_final.append(utilizator_data)

    with open(fisier_iesire, "w", encoding="utf-8") as f:
        json.dump(output_final, f, indent=4, ensure_ascii=False)

    print(f"Raportul a fost generat cu succes in {fisier_iesire}")
