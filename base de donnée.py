import mysql.connector
import pandas as pd
import pickle
import Orange
from datetime import datetime

# ─── 1. Charger le modèle IA ───────────────────────────────
with open(
    r"c:/Users/mohammed.benchekroun/Downloads/Shuntage_Online - current/Shuntage_Online - current/predictReByUres_NN.pkcls",
    "rb"
) as f:
    learner = pickle.load(f)

def predict_impedance(val_list):
    """Prédit l'impédance Z pour chaque tension de val_list."""
    data = Orange.data.Table.from_list(learner.domain, [[v] for v in val_list])
    return [float(p) / 100 for p in learner(data)]  # Ajustement normalisation si besoin


# ─── 2. Connexion à MySQL ───────────────────────────────
db = mysql.connector.connect(
    host="localhost",
    port=8000,
    user="root",
    password="19721972Ben?",
    database="mypro"
)


# ─── 3. Fonction pour récupérer les données ───────────────────────────────
def get_data(ville, date):
    cursor = db.cursor(dictionary=True)

    # Extraire uniquement la date (YYYY-MM-DD)
    formatted_date = date.split()[0]

    query = """
        SELECT 
            Ville, 
            Date AS DateComplete,
            Valeur AS Tension,
            T, 
            CdV, 
            Commentaire
        FROM simo
        WHERE Ville = %s AND DATE(Date) = %s
    """

    cursor.execute(query, (ville, formatted_date))
    result = cursor.fetchall()
    cursor.close()
    return result


# ─── 4. Fonction principale pour exporter en Excel ───────────────────────────────
def export_to_excel(ville, date, output_file="resultats.xlsx"):
    # Récupérer les données
    data = get_data(ville, date)

    if not data:
        print("⚠️ Aucune donnée trouvée pour cette ville et cette date.")
        return

    # Convertir en DataFrame
    df = pd.DataFrame(data)

    # Conversion format date lisible
    df["DateComplete"] = df["DateComplete"].apply(
        lambda x: x.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] if isinstance(x, datetime) else x
    )

    # Prédire l'impédance pour chaque tension
    df["Impedance_Predite"] = predict_impedance(df["Tension"].tolist())

    # Exporter en Excel
    df.to_excel(output_file, index=False)
    print(f"✅ Fichier Excel généré : {output_file}")


# ─── 5. Exemple d’utilisation ───────────────────────────────
if __name__ == "__main__":
    ville = "Dardilly 1 TR"   # 👉 à changer par la ville voulue
    date = "2013-10-22"  # 👉 à changer par la date voulue (YYYY-MM-DD)
    export_to_excel(ville, date, "resultats_impedance.xlsx")
