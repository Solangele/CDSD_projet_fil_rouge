# 1. On part d'une image officielle Python légère
FROM python:3.10-slim

# 2. On installe les dépendances système nécessaires pour l'audio (librosa / soundfile)
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# 3. On définit le dossier de travail dans le conteneur
WORKDIR /app

# 4. On copie le fichier des dépendances et on les installe
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. On copie le modèle entraîné et le script d'API dans le conteneur
COPY model_cnn_optimal.h5 .
COPY app.py .

# 6. On expose le port sur lequel notre API va tourner
EXPOSE 5000

# 7. Commande de lancement de l'application
CMD ["python", "app.py"]