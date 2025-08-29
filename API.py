from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime

app = Flask(__name__)

# Connexion MySQL
db = mysql.connector.connect(
    host="localhost",
    port=8000,
    user="root",
    password="19721972Ben?",
    database="mypro"
)

# ✅ Route existante pour récupérer les données d'une ville et d'une date spécifique
@app.route('/ville', methods=['GET'])
def get_ville():
    ville = request.args.get('nom')
    date = request.args.get('date')

    if not ville or not date:
        return jsonify({"error": "Veuillez spécifier une ville et une date avec ?nom=Ville&date=YYYY-MM-DD"}), 400

    try:
        cursor = db.cursor(dictionary=True)

        # Extraire uniquement la partie 'YYYY-MM-DD'
        formatted_date = date.split()[0]

        query = """
            SELECT 
                Ville, 
                Date AS DateComplete,  # Date avec millisecondes
                Valeur, 
                T, 
                CdV, 
                Commentaire
            FROM simo
            WHERE Ville = %s AND DATE(Date) = %s
        """

        cursor.execute(query, (ville, formatted_date))
        result = cursor.fetchall()

        if not result:
            cursor.close()
            return jsonify({"error": "Aucune donnée trouvée pour cette ville et cette date"}), 404

        cursor.close()

        # ✅ **Conversion manuelle pour afficher les millisecondes**
        for row in result:
            if isinstance(row["DateComplete"], datetime):
                row["DateComplete"] = row["DateComplete"].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Garder 3 chiffres après la virgule

        return jsonify(result)

    except mysql.connector.Error as err:
        return jsonify({"error": f"Erreur MySQL : {err}"}), 500

    except Exception as e:
        return jsonify({"error": f"Erreur interne : {str(e)}"}), 500


# ✅ Nouvelle route pour récupérer la liste des villes DISTINCTES
@app.route('/get_cities', methods=['GET'])
def get_cities():
    try:
        cursor = db.cursor()
        cursor.execute("SELECT DISTINCT Ville FROM ville_test")  # Récupérer toutes les villes distinctes
        villes = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return jsonify({"villes": villes})  # Retourne la liste des villes
    except mysql.connector.Error as err:
        return jsonify({"error": f"Erreur MySQL : {err}"}), 500
    except Exception as e:
        return jsonify({"error": f"Erreur interne : {str(e)}"}), 500


# ✅ Démarrer le serveur Flask
if __name__ == '__main__':
    app.run(debug=True, port=5021)
