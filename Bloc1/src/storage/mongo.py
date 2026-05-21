import os
import io
import boto3
import soundfile as sf
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv(dotenv_path="../../.env") 

# 1. Connexion aux services
s3 = boto3.client('s3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id=os.getenv('MINIO_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('MINIO_SECRET_KEY')
)

dbname = os.getenv('MONGO_DBNAME')

mongo_client = MongoClient(
    host='localhost',
    port=27017,
    username=os.getenv('MONGO_USER'),
    password=os.getenv('MONGO_PASSWORD'),
    authSource= 'admin'
)

db = mongo_client[dbname]
collection = db['metadata']

IRMAS_INSTRUMENTS = {
    "cel": "celesta", "cla": "clarinet", "flg": "flute", "gac": "acoustic_guitar",
    "gel": "electric_guitar", "org": "organ", "pia": "piano", "sax": "saxophone",
    "tru": "trumpet", "vln": "violin", "voi": "voice"
}

# Ajout de bucket_name dans les paramètres de la fonction
def extract_instrument_label(bucket_name, file_key, source_name):
    file_key_lower = file_key.lower()
    
    if source_name == "philharmonia_scrap":
        return file_key.split('/')[0]
        
    elif source_name == "irmas_dataset":
        irmas_codes = list(IRMAS_INSTRUMENTS.keys())
        
        # Stratégie A : Dossier training (ex: training/sax/file.wav)
        parts = file_key_lower.split('/')
        if len(parts) > 1 and parts[1] in irmas_codes:
            return IRMAS_INSTRUMENTS[parts[1]] 
            
        # Stratégie B : Présence directe dans le nom (ex: part1/[sax]1234.wav)
        for code in irmas_codes:
            if f"[{code}]" in file_key_lower or f"_{code}_" in file_key_lower:
                return IRMAS_INSTRUMENTS[code] 
                
        # Stratégie C (La nouvelle !) : Lecture du fichier .txt associé pour le Testing
        # On remplace l'extension actuelle (.wav, .WAV) par .txt
        base_path, _ = os.path.splitext(file_key)
        txt_key = base_path + ".txt"
        
        try:
            # On va chercher le fichier texte portant le même nom sur MinIO
            txt_obj = s3.get_object(Bucket=bucket_name, Key=txt_key)
            # On lit le texte, décode le binaire et nettoie les sauts de ligne
            txt_content = txt_obj['Body'].read().decode('utf-8').strip().lower()
            
            # Le fichier texte d'IRMAS contient souvent les codes séparés par des espaces ou tabulations
            # On découpe le contenu mot par mot pour trouver le premier code d'instrument valide
            for word in txt_content.split():
                clean_word = word.strip()
                if clean_word in irmas_codes:
                    return IRMAS_INSTRUMENTS[clean_word]
                    
        except Exception:
            # Si le fichier .txt est introuvable ou illisible, on ne bloque pas le script
            return "unknown"
                
    return "unknown"




def get_minio_audio_duration(bucket_name, file_key):
    """Télécharge l'en-tête du fichier depuis MinIO pour calculer sa durée en secondes"""
    try:
        # On récupère l'objet binaire depuis MinIO
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        audio_data = response['Body'].read()
        
        # On le passe en mémoire à soundfile pour lire la durée
        with sf.SoundFile(io.BytesIO(audio_data)) as f:
            return len(f) / f.samplerate  # nb frames / fréquence = durée en secondes
    except Exception as e:
        print(f"Impossible de lire la durée de {file_key}: {e}")
        return None




def index_minio_to_mongodb(bucket_name, source_name):
    print(f"Indexation du bucket '{bucket_name}' (Source: {source_name})...")
    
    # On récupère la liste des objets dans le bucket
    paginator = s3.get_paginator('list_objects_v2')
    count = 0

    for page in paginator.paginate(Bucket=bucket_name):
        if 'Contents' in page:
            for obj in page['Contents']:
                file_key = obj['Key']
                
                # On ne traite que les fichiers audio
                if file_key.lower().endswith(('.wav', '.mp3')):
                    # SÉCURITÉ : On entoure le traitement par un try/except
                    try:
                        # 1. Extraction intelligente du label selon le dataset
                        label = extract_instrument_label(bucket_name, file_key, source_name)

                        # 2. Calcul de la durée en ligne depuis MinIO
                        duration = get_minio_audio_duration(bucket_name, file_key)

                        # 3. Création du document JSON enrichi
                        metadata = {
                            "filename": os.path.basename(file_key),
                            "minio_path": f"{bucket_name}/{file_key}",
                            "label": label,
                            "source": source_name,
                            "size_bytes": obj['Size'],
                            "duration_seconds": duration, 
                            "last_modified": obj['LastModified']
                        }

                        # Insertion ou mise à jour dans MongoDB
                        collection.update_one(
                            {"minio_path": metadata["minio_path"]}, 
                            {"$set": metadata}, 
                            upsert=True
                        )
                        count += 1
                        
                        if count % 500 == 0:
                            print(f"  {count} fichiers indexés...")
                            
                    except Exception as file_error:
                        # Si un fichier pose un problème critique, on l'affiche et on passe au suivant !
                        print(f"Fichier ignoré suite à une erreur sur {file_key}: {file_error}")
                        continue
    
    
    print(f"{count} documents indexés pour {source_name}.")

if __name__ == "__main__":
    index_minio_to_mongodb("philharmonia", "philharmonia_scrap")
    index_minio_to_mongodb("irmas", "irmas_dataset")