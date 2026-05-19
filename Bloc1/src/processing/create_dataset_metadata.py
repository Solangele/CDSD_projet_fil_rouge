import os
import pandas as pd

def generate_irmas_csv(data_path, output_filename="metadata_irmas.csv"):
    data_list = []
    
    # On parcourt le dossier data/IRMAS-Training
    # Structure attendue : data/IRMAS-Training/[instrument]/[fichier.wav]
    for root, dirs, files in os.walk(data_path):
        for file in files:
            if file.endswith(".wav"):
                # Le label est souvent le nom du dossier parent (ex: 'vln', 'cel')
                label = os.path.basename(root)
                # Chemin complet pour que Python retrouve le fichier plus tard
                file_path = os.path.join(root, file)
                
                data_list.append({
                    "file_path": file_path,
                    "label": label,
                    "instrument_full": label_to_name(label) # Optionnel : nom complet
                })
    
    # Création du DataFrame
    df = pd.DataFrame(data_list)
    
    # Sauvegarde en CSV
    df.to_csv(output_filename, index=False)
    print(f"✅ Terminé ! {len(df)} fichiers indexés dans {output_filename}")

def label_to_name(label):
    """Convertit les codes IRMAS en noms clairs pour ton App enfant"""
    mapping = {
        "cel": "Violoncelle",
        "cla": "Clarinette",
        "flt": "Flûte",
        "gac": "Guitare Acoustique",
        "gel": "Guitare Électrique",
        "org": "Orgue",
        "pia": "Piano",
        "sax": "Saxophone",
        "tru": "Trompette",
        "vio": "Violon",
        "voi": "Voix"
    }
    return mapping.get(label.lower(), "Inconnu")

# Utilisation
generate_irmas_csv("data/IRMAS-TrainingData")