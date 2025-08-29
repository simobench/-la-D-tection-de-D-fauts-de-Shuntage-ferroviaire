from flask import Flask, request, jsonify
import pickle
import Orange
import matlab.engine
import traceback
import io
from influxdb_client import InfluxDBClient, Point, WriteOptions
from datetime import datetime, timezone


# ─── 1. Flask app ───────
app = Flask(__name__)

# ─── 2. Charger le modèle IA (une fois)
with open(
    r"c:/Users/mohammed.benchekroun/Downloads/Shuntage_Online - current/Shuntage_Online - current/predictReByUres_NN.pkcls",
    "rb"
) as f:
    learner = pickle.load(f)


def predict_impedance(val_list):
    """Prédit l'impédance Z pour chaque tension de val_list."""
    data = Orange.data.Table.from_list(learner.domain, [[v] for v in val_list])
    return [p / 100 for p in learner(data)]  # Ajuster la normalisation si besoin


# ─── 3. Démarrer MATLAB Engine (une seule fois)
print("⏳ Démarrage de MATLAB...")
eng = matlab.engine.start_matlab()
print("✅ MATLAB démarré.")


# ─── 4. Configuration du modèle Simulink
model_name = "IM_deux_cdv_avec_JES_1Essieu_25112024_SimuEvast"
model_path = r"C:/Users/mohammed.benchekroun/Downloads/IM_deux_cdv_avec_JES_1Essieu_25112024_VariaConst"


# ─── 5. Configurer InfluxDB
INFLUXDB_URL = "http://localhost:8086"
INFLUXDB_TOKEN = "hiX3flY9wXXEAf9bpRM4V3ETb79l_Xn_o7T0DnIEuCV8DIu2QE1j-zW37a39F5DSpncCpsUpu7qeqKI4tyvYRg=="  
INFLUXDB_ORG = "Test"
INFLUXDB_BUCKET = "Simulation"

client = InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)
write_api = client.write_api(write_options=WriteOptions(batch_size=1))


def send_results_to_influxdb(sim_out_data):
    """Envoie les résultats du SimOut vers InfluxDB"""
    try:
        print("📡 Envoi des données vers InfluxDB...")

        # Récupérer les signaux depuis SimOut
        current = sim_out_data['Current']
        current_rms = sim_out_data['Current_RMS']
        tension = sim_out_data['Tension']
        tension_rms = sim_out_data['Tension_RMS']
        time_vector = sim_out_data['time']  # Temps de simulation

        # Parcourir et envoyer chaque point
        for t, i, irms, u, urms in zip(sim_out_data['time'],
            sim_out_data['Current'],
            sim_out_data['Current_RMS'],
            sim_out_data['Tension'],
            sim_out_data['Tension_RMS']
        ):
            point = (
                Point("resultats_simulink")
                .tag("Simulation", model_name)
                .field("Current", float(i))
                .field("Current_RMS", float(irms))
                .field("Tension", float(u))
                .field("Tension_RMS", float(urms))
                .time(datetime.now(timezone.utc))
            )
            write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)

        print("✅ Données envoyées à InfluxDB.")

    except Exception as err:
        print(f"❌ Erreur d’envoi vers InfluxDB : {err}")


# ─── 6. Endpoint POST pour recevoir les données
@app.route('/envoyer_donnees', methods=['POST'])
def run_simulation():
    try:
        # 6.1 Récupère JSON [{"indice":…, "valeur":…}, …]
        donnees = request.get_json()
        indices = [d["indice"] for d in donnees]
        tensions = [d["valeur"] for d in donnees]

        if not indices or not tensions:
            return jsonify({'error': 'Indices ou tensions manquants'}), 400

        # 6.2 Debug dans la console Python
        print("\n📩 Données reçues d'AnyLogic :")
        for i, t in zip(indices, tensions):
            print(f"  Indice: {i}, Tension: {t}")

        # 6.3 Prédiction IA
        Z_values = predict_impedance(tensions)
        print("\n🧠 Impédances prédites par l'IA :")
        for i, z in zip(indices, Z_values):
            print(f"  Indice: {i}, Z: {z}")

        # 6.4 Préparation MATLAB
        eng.addpath(
            r"C:/Users/mohammed.benchekroun/Downloads/Shuntage_Online - current/Shuntage_Online - current",
            nargout=0
        )
        eng.cd(model_path, nargout=0)

        # 6.5 Injection des données dans le workspace MATLAB
        eng.eval("clear Vecteur_TempsRe Reet stop_time", nargout=0)

        eng.workspace['Vecteur_TempsRe'] = matlab.double(indices)
        if len(Z_values) == 1:
            Reet_mat = matlab.double([[Z_values[0]]])  # single valeur
        else:
            Reet_mat = matlab.double([[z] for z in Z_values])  # vecteur colonne
        eng.workspace['Reet'] = Reet_mat

        stop_time = max(indices)
        eng.workspace['stop_time'] = float(stop_time)
        print(f"⏱️ stop_time défini à {stop_time}.")

        print("📤 Données injectées dans le workspace MATLAB.")

        # 6.6 Lancer la simulation
        try:
            print("🚪 Ouverture visuelle du modèle Simulink...")
            eng.eval(f"open_system('{model_name}')", nargout=0)

            print("🚦 Lancement de la simulation Simulink...")
            eng.eval(f"simOut = sim('{model_name}', 'StopTime', num2str(stop_time), 'SaveOutput','on');", nargout=0)
            print("✅ Simulation terminée.")
        
        except Exception as sim_err:
            print("❌ Erreur lors de la simulation Simulink :")
            print(sim_err)
 
 
        out = io.StringIO()
        eng.eval("disp(simOut)", nargout=0, stdout=out)
        print("📊 Résultats de la simulation Simulink :")
        print(out.getvalue())


        out = io.StringIO()
        nombre_elements = eng.analyser_donnees(
            matlab.double(indices),
            matlab.double(Z_values),
            nargout=1,
            stdout=out
        )
        print("\n📤 Sortie console MATLAB (disp) :")
        print(out.getvalue())
        print(f"🧪 analyser_donnees a traité {nombre_elements} éléments.")

        # 6.7 Récupération des signaux
        sim_out_data = {
            'Current': list(eng.getfield(eng.workspace['simOut'], 'Current')[0]),  # conversion en liste
            'Current_RMS': list(eng.getfield(eng.workspace['simOut'], 'Current_RMS')[0]),
            'Tension': list(eng.getfield(eng.workspace['simOut'], 'Tension')[0]),
            'Tension_RMS': list(eng.getfield(eng.workspace['simOut'], 'Tension_RMS')[0]),
            'time': list(eng.getfield(eng.workspace['simOut'], 'temps')[0])

        }
        print("📊 Données extraites depuis SimOut.")

        # 6.8 Envoi vers InfluxDB
        send_results_to_influxdb(sim_out_data)

        # 6.9 Construction de la réponse JSON
        resultats = [
            {"indice": idx, "Z": z}
            for idx, z in zip(indices, Z_values)
        ]
        return jsonify({
            "message": "✅ Simulation terminée et résultats envoyés à InfluxDB.",
            "resultats": resultats
        }), 200

    except Exception as e:
        tb = traceback.format_exc()
        print("❌ Exception complète dans /envoyer_donnees :")
        print(tb)
        return jsonify({
            "error": str(e),
            "traceback": tb
        }), 500


# ─── 7. Lancer le serveur Flask
if __name__ == "__main__":
    app.run(port=5049, debug=True)
