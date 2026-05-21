import os
import time
# from dotenv import load_dotenv
from pyspark.sql import SparkSession
from pyspark.sql import functions as F

# 1. Chargement du fichier .env situé à la racine 
# load_dotenv(dotenv_path=".env") 

# 2. Récupération des variables d'environnement de PostgreSQL
db_name = os.getenv('POSTGRES_DB')
db_user = os.getenv('POSTGRES_USER')
db_pass = os.getenv('POSTGRES_PASSWORD')

if not db_name or not db_user or not db_pass:
    print("Erreur : Impossible de charger les variables PostgreSQL depuis le .env")
    exit(1)

print("Configuration de l'environnement chargée avec succès.")

# 3. Initialisation de la session Spark connectée au Master Docker
# On demande à Spark de charger automatiquement le connecteur JDBC Postgres
print("Connexion au cluster Spark (Docker) en cours...")
spark = SparkSession.builder \
    .appName("AudioProject_BigData_Analysis") \
    .master("spark://spark-master:7077") \
    .config("spark.jars.packages", "org.postgresql:postgresql:42.7.3") \
    .getOrCreate()

# 4. Configuration de la connexion JDBC vers PostgreSQL Gold
# Attention : sous Windows, pour que le script Python (local) parle à Postgres (Docker),
# on utilise 'localhost:5432'.
jdbc_url = f"jdbc:postgresql://pfr-postgres:5432/{db_name}"
connection_properties = {
    "user": db_user,
    "password": db_pass,
    "driver": "org.postgresql.Driver"
}

# 5. Lecture parallélisée de la table Gold via une sous-requête (pour avoir les vrais noms d'instruments)
# Cela nous évite de récupérer un simple 'instrument_id' numérique
query_table = """
(SELECT t.filename, t.duration_seconds, t.size_bytes, t.source_dataset, i.label_name as instrument 
 FROM audio_tracks t 
 JOIN instruments i ON t.instrument_id = i.id) as audio_gold_data
"""

print("Chargement distribué des données depuis PostgreSQL Gold...")
try:
    spark_df = spark.read.jdbc(
        url=jdbc_url, 
        table=query_table, 
        properties=connection_properties
    )
except Exception as e:
    print(f"❌ Erreur lors de la lecture JDBC : {e}")
    print("Vérifie que ta base PostgreSQL est bien allumée et contient des données.")
    spark.stop()
    exit(1)

# 6. Traitement statistique Big Data (Critère C2.3)
print("Lancement de l'analyse statistique distribuée sur le cluster...")
start_time = time.time()

# Agrégation multivariée
statistiques_multivariees = spark_df.groupBy("instrument", "source_dataset") \
    .agg(
        F.count("filename").alias("total_pistes"),
        F.round(F.mean("duration_seconds"), 2).alias("duree_moyenne_sec"),
        F.round(F.mean("size_bytes") / 1024 / 1024, 2).alias("taille_moyenne_mo"),
        F.min("duration_seconds").alias("duree_min"),
        F.max("duration_seconds").alias("duree_max")
    ) \
    .orderBy("instrument")

# Déclenchement physique du calcul (Action Spark)
statistiques_multivariees.show(40, truncate=False)

execution_time = time.time() - start_time
print(f"Temps de calcul parallélisé avec Spark : {execution_time:.4f} secondes")

# Fermeture propre de la session
spark.stop()
print("Session Spark clôturée.")