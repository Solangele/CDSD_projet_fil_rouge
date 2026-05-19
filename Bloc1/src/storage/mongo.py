import os
import boto3
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv(dotenv_path="../../.env") # Ajuste le chemin selon ton arborescence

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

def index_minio_to_mongodb(bucket_name, source_name):
    print(f"📂 Indexation du bucket '{bucket_name}' (Source: {source_name})...")
    
    # On récupère la liste des objets dans le bucket
    paginator = s3.get_paginator('list_objects_v2')
    count = 0

    for page in paginator.paginate(Bucket=bucket_name):
        if 'Contents' in page:
            for obj in page['Contents']:
                file_key = obj['Key']
                
                # Extraction simplifiée du label (le nom du dossier parent)
                # Exemple : "banjo/son_01.wav" -> label = "banjo"
                parts = file_key.split('/')
                label = parts[0] if len(parts) > 1 else "unknown"

                # Création du document JSON
                metadata = {
                    "filename": os.path.basename(file_key),
                    "minio_path": f"{bucket_name}/{file_key}",
                    "label": label,
                    "source": source_name,
                    "size_bytes": obj['Size'],
                    "last_modified": obj['LastModified']
                }

                # Insertion dans MongoDB (update si existe déjà pour éviter les doublons)
                collection.update_one(
                    {"minio_path": metadata["minio_path"]}, 
                    {"$set": metadata}, 
                    upsert=True
                )
                count += 1
    
    print(f"✅ {count} documents indexés pour {source_name}.")

if __name__ == "__main__":
    index_minio_to_mongodb("philharmonia", "philharmonia_scrap")
    index_minio_to_mongodb("irmas", "irmas_dataset")