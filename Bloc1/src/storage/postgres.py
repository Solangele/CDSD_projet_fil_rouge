import os
import psycopg2
from pymongo import MongoClient
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir)) 
load_dotenv(dotenv_path=os.path.join(project_root, '.env'))


def get_postgres_connection():
    return psycopg2.connect(
        host= "localhost",
        port= "5432",
        database= "datapulse_db",
        user= os.getenv("POSTGRES_USER"),
        password= os.getenv("POSTGRES_PASSWORD")
    )


def init_postgres_schema():
    """ Création de la structure des tables SQL (couche Gold)"""
    commands = (
        """
        CREATE TABLE IF NOT EXISTS instruments (
            id SERIAL PRIMARY KEY,
            label_name VARCHAR(100) UNIQUE NOT NULL
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS audio_tracks (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) NOT NULL,
            minio_path VARCHAR(550) UNIQUE NOT NULL,
            instrument_id INT references instruments(id) ON DELETE CASCADE,
            source_dataset VARCHAR(100) NOT NULL,
            size_bytes BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    conn = None
    try:
        conn = get_postgres_connection()
        cur = conn.cursor()
        for command in commands:
            cur.execute(command)
        cur.close()
        conn.commit()
        print("Schéma PostgreSQL (Gold) initialisé avec succès !!")
    except Exception as error:
        print(f"Erreur lors de l'initialisation de SQL : {error}")
    finally:
        if conn is not None:
            conn.close()


def load_silver_to_gold():
    """Aspire MongoDB (Silver) et insère de manière structurée dans PostgreSQL (Gold)"""
    print("Début de la transition Silver -> Gold")

    mongo_client = MongoClient(
        host= 'localhost',
        port= 27017,
        username= os.getenv('MONGO_USER'),
        password= os.getenv('MONGO_PASSWORD')
    )

    db_name = os.getenv('MONGO_DBNAME')
    db = mongo_client[db_name]
    mongo_docs = db.metadata.find()

    conn = get_postgres_connection()
    cur = conn.cursor()

    tracks_inserted = 0

    for doc in mongo_docs:
        label = doc.get('label', 'unknown').lower().strip()

        cur.execute(
            """
            INSERT INTO instruments (label_name) 
            VALUES (%s) 
            ON CONFLICT (label_name) DO NOTHING RETURNING id;
            """
            ,
            (label,)
        )
        res = cur.fetchone()

        if res :
            instrument_id = res[0]
        else :
            cur.execute(
                "SELECT ID FROM instruments WHERE label_name = %s",
                (label,)
                )
            instrument_id = cur.fetchone()[0]

        try:
            cur.execute(
                """
                INSERT INTO audio_tracks(filename, minio_path, instrument_id, source_dataset, size_bytes)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (minio_path) DO NOTHING;
                """,
                (doc['filename'], doc['minio_path'], instrument_id, doc['source'], doc['size_bytes'])
            )   
            tracks_inserted += cur.rowcount
        except Exception as e:
            print(f"Erreur insertion piste {doc['filename']} : {e}")
            conn.rollback()
            continue

    conn.commit()
    cur.close()
    conn.close()
    print(f"Transition terminée. {tracks_inserted} nouvelles pistes structurées dans PostgreSQL Gold.")

if __name__ == "__main__":
    init_postgres_schema()
    load_silver_to_gold()