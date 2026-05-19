import os
import boto3
from botocore.client import Config
from dotenv import load_dotenv

load_dotenv()

# Connexion avec les variables du .env
s3 = boto3.client('s3',
    endpoint_url='http://localhost:9000',
    aws_access_key_id=os.getenv('MINIO_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('MINIO_SECRET_KEY'),
    config=Config(signature_version='s3v4')
)

def upload_folder_to_minio(local_dir, bucket_name):
    """Vérifie le bucket, le crée si besoin, et envoie le dossier local."""
    
    # 1. Vérification/Création du Bucket
    try:
        # On essaie de voir si le bucket existe
        s3.head_bucket(Bucket=bucket_name)
        print(f"Le bucket '{bucket_name}' existe déjà.")
    except:
        # Si head_bucket échoue, c'est que le bucket n'existe pas
        print(f"Création du bucket manquant : '{bucket_name}'...")
        try:
            s3.create_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' créé avec succès.")
        except Exception as e:
            print(f"❌ Impossible de créer le bucket : {e}")
            return # On s'arrête si on ne peut pas créer le bucket

    # 2. Parcours et envoi des fichiers
    print(f"Début de l'envoi de {local_dir}...")
    
    count = 0
    for root, dirs, files in os.walk(local_dir):
        for file in files:
            local_path = os.path.join(root, file)
            relative_path = os.path.relpath(local_path, local_dir)
            s3_path = relative_path.replace("\\", "/")

            try:
                s3.upload_file(local_path, bucket_name, s3_path)
                count += 1
                if count % 100 == 0:
                    print(f"  {count} fichiers synchronisés...")
            except Exception as e:
                print(f"Erreur sur {file}: {e}")

    print(f"Terminé ! {count} fichiers sont dans le bucket '{bucket_name}'.")