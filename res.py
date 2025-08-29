import os
import matplotlib.pyplot as plt
import pandas as pd

def analyser_et_exporter_simout(simOut):
    # Créer un dossier pour les fichiers CSV s'il n'existe pas
    dossier = "resultats_simulation"
    os.makedirs(dossier, exist_ok=True)

    # Vérifie s'il y a un signal temps
    temps = simOut.get("temps", None)
    if temps is not None:
        temps = temps["_data"].flatten()  # 1D array

    # Parcourir tous les signaux dans simOut
    for nom_signal, contenu in simOut.items():
        try:
            if isinstance(contenu, dict) and "_data" in contenu:
                data = contenu["_data"].flatten()  # 1D array

                # Enregistrer en CSV
                df = pd.DataFrame({nom_signal: data})
                if temps is not None and len(temps) == len(data):
                    df.insert(0, "temps", temps)
                df.to_csv(os.path.join(dossier, f"{nom_signal}.csv"), index=False)

                # Tracer le signal
                plt.figure()
                if temps is not None and len(temps) == len(data):
                    plt.plot(temps, data)
                    plt.xlabel("Temps (s)")
                else:
                    plt.plot(data)
                    plt.xlabel("Index")

                plt.ylabel(nom_signal)
                plt.title(f"Signal : {nom_signal}")
                plt.grid(True)
                plt.tight_layout()
                plt.savefig(os.path.join(dossier, f"{nom_signal}.png"))  # Enregistre aussi en image
                plt.close()
                print(f"✅ Signal traité : {nom_signal}")
        except Exception as e:
            print(f"⚠️ Erreur lors du traitement de {nom_signal} : {e}")

    print(f"📁 Tous les fichiers CSV et images sont enregistrés dans le dossier : {dossier}")
