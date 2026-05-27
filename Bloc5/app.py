import os
import numpy as np
import librosa
import tensorflow as tf
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# 1. CHEMIN DE PRODUCTION DU MODÈLE
DOSSIER_DU_SCRIPT = os.path.dirname(os.path.abspath(__file__))
CHEMIN_MODELE = os.path.join(DOSSIER_DU_SCRIPT, "model_cnn_optimal.h5")

# 2. CHARGEMENT DU MODÈLE
if os.path.exists(CHEMIN_MODELE):
    print(f"Récupération du modèle optimal : {CHEMIN_MODELE}")
    model = tf.keras.models.load_model(CHEMIN_MODELE)
else:
    raise FileNotFoundError(f"Le modèle '{CHEMIN_MODELE}' est introuvable dans le dossier Bloc5.")

# Dictionnaire de secours universel pour mapper les indices de sortie
CLASSES_BRUTES_26 = [
    "acoustic_guitar", "banjo", "bass clarinet", "bassoon", 
    "celesta", "cello", "clarinet", "contrabassoon", 
    "cor anglais", "double bass", "electric_guitar", "flute", 
    "french horn", "guitar", "mandolin", "oboe", 
    "organ", "percussion", "piano", "saxophone", 
    "trombone", "trumpet", "tuba", "viola", 
    "violin", "voice"
]

# Les 7 familles cibles
FAMILLES_7 = [
    "Famille des Cordes Frottées",     # index 0
    "Famille des Cordes Pincées",     # index 1
    "Orgues & Claviers Anciens",        # index 2
    "Percussions",                      # index 3
    "Pianos & Claviers Frappés",       # index 4
    "Instruments à Vent & Cuivres",    # index 5
    "Chant & Voix Humaines"             # index 6
]

def traiter_et_predire_vrai(chemin_audio):
    """
    Pipeline de production adaptatif et sécurisé contre les crashs d'index
    """
    # Étape C4.1 : Prétraitement du signal audio
    y, sr = librosa.load(chemin_audio, sr=22050, duration=3.0)
    mel_spec = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=128, fmax=8000)
    mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)
    
    if mel_spec_db.shape[1] < 128:
        mel_spec_db = np.pad(mel_spec_db, ((0, 0), (0, 128 - mel_spec_db.shape[1])), mode='constant')
    else:
        mel_spec_db = mel_spec_db[:, :128]
        
    min_val = mel_spec_db.min()
    max_val = mel_spec_db.max()
    if max_val - min_val != 0:
        mel_spec_db = (mel_spec_db - min_val) / (max_val - min_val)
    else:
        mel_spec_db = np.zeros_like(mel_spec_db)

    matrice_input = np.expand_dims(mel_spec_db, axis=(0, -1))
    
    # Étape C4.2 : Prédiction brute
    predictions = model.predict(matrice_input)[0]
    nb_sorties_modele = len(predictions)
    index_predit = np.argmax(predictions)
    score_confiance = predictions[index_predit] * 100
    
    # CAS 1 : C'est bien le nouveau modèle à 7 sorties qui est chargé
    if nb_sorties_modele == 7:
        return FAMILLES_7[index_predit], score_confiance
        
    # CAS 2 : Sécurité si l'ancien modèle à 26/15 sorties est encore en mémoire cache
    else:
        # On récupère le nom de l'instrument d'origine pour éviter le crash de l'index out of range
        nom_instrument_brut = CLASSES_BRUTES_26[index_predit] if index_predit < len(CLASSES_BRUTES_26) else "autre"
        
        # Mapping logique à la volée vers les 7 familles
        if nom_instrument_brut in ["organ"]:
            return FAMILLES_7[2], score_confiance
        elif nom_instrument_brut in ["banjo", "guitar", "mandolin", "electric_guitar", "acoustic_guitar"]:
            return FAMILLES_7[1], score_confiance
        elif nom_instrument_brut in ["voice"]:
            return FAMILLES_7[6], score_confiance
        elif nom_instrument_brut in ["bassoon", "cello", "contrabassoon", "double bass", "viola", "violin"]:
            return FAMILLES_7[0], score_confiance
        elif nom_instrument_brut in ["piano", "celesta"]:
            return FAMILLES_7[4], score_confiance
        elif nom_instrument_brut in ["percussion"]:
            return FAMILLES_7[3], score_confiance
        else:
            return FAMILLES_7[5], score_confiance

# --- INTERFACE WEB MÉTIER (C5.3) ---
HTML_INTERFACE = """
<!DOCTYPE html>
<html>
<head>
    <title>IA Audio - Routage Securisé</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; background-color: #f4f6f9; display: flex; align-items: center; justify-content: center; height: 100vh; }
        .card { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 8px 25px rgba(0,0,0,0.05); max-width: 550px; width: 100%; text-align: center; }
        h2 { color: #2c3e50; margin: 0 0 10px 0; font-size: 24px; }
        p { color: #7f8c8d; margin-bottom: 30px; font-size: 14px; }
        .file-input { margin: 20px 0; padding: 15px; border: 2px dashed #3498db; border-radius: 8px; background: #f8fafc; width: 85%; font-size: 14px; }
        button { background: #3498db; color: white; border: none; padding: 14px 30px; border-radius: 6px; font-size: 16px; font-weight: bold; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #2980b9; }
        .footer { margin-top: 25px; font-size: 11px; color: #bdc3c7; }
    </style>
</head>
<body>
    <div class="card">
        <h2>🎵 Tri et Routage Audio Intel-Safe</h2>
        <p>Pipeline Hybride Tolérant aux Pannes — Objectif 7 Familles</p>
        <hr style="border: 0; border-top: 1px solid #edf2f7; margin-bottom: 20px;">
        <form action="/predict" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".wav,.mp3" class="file-input" required><br>
            <button type="submit">Analyser et Router</button>
        </form>
        <div class="footer">Démonstrateur de Production Auto-Synchronisé</div>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_INTERFACE)

@app.route('/predict', methods=['POST'])
def predict():
    if 'file' not in request.files:
        return jsonify({'erreur': 'Aucun fichier détecté'}), 400
    
    fichier = request.files['file']
    if fichier.filename == '':
        return jsonify({'erreur': 'Aucun fichier sélectionné'}), 400
        
    chemin_temporaire = os.path.join(".", fichier.filename)
    fichier.save(chemin_temporaire)
    
    try:
        famille_detectee, confiance = traiter_et_predire_vrai(chemin_temporaire)
        statut = "Succès"
    except Exception as e:
        famille_detectee = "Erreur de classification"
        confiance = 0.0
        statut = f"Erreur technique : {str(e)}"
    finally:
        if os.path.exists(chemin_temporaire):
            os.remove(chemin_temporaire)
    
    return jsonify({
        'statut': statut,
        'fichier_analyse': fichier.filename,
        'famille_instrument_identifiee': famille_detectee,
        'score_de_confiance_global': f"{confiance:.2f}%",
        'action_industrialisation': f"Routage automatique vers le répertoire industriel : {famille_detectee}"
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)