import requests
from bs4 import BeautifulSoup
import zipfile
import io
import os
from dotenv import load_dotenv

load_dotenv()

def etl_philharmonia_to_disk():
    url = "https://philharmonia.co.uk/resources/sound-samples/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    # --- PHASE 1 : SCRAPING (EXTRACT) ---
    print("Recherche du lien de téléchargement...")
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', class_='c-btn')
    print(f"Nombre de boutons trouvés : {len(links)}") # Vérification
    
    zip_url = None
    for link in links:
        href = link.get('href')
        print(f"Lien analysé : {href}") # Pour voir TOUS les liens
        if href and "zip" in href.lower(): # On ratisse plus large
            zip_url = href
            break

    if not zip_url:
        print("❌ Lien introuvable.")
        return

# --- PHASE 2 : TÉLÉCHARGEMENT ---
    print(f"Téléchargement en cours...")
    r = requests.get(zip_url, stream=True) # stream=True est plus sûr pour les gros fichiers
    
    # On vérifie la taille du fichier reçu
    taille_mo = len(r.content) / (1024 * 1024)
    print(f"Taille du fichier téléchargé : {taille_mo:.2f} Mo")

    if taille_mo < 0.1:
        print("❌ Le fichier téléchargé est trop petit, il y a eu un problème de réseau.")
        return

    z = zipfile.ZipFile(io.BytesIO(r.content))

# --- PHASE 3 : DOUBLE EXTRACTION AVEC RANGEMENT ---
    noms_fichiers = z.namelist()
    target_folder = "data/scrap/philharmonia"
    os.makedirs(target_folder, exist_ok=True)

    print(f"Extraction et organisation par instruments...")
    
    files_extracted = 0

    for filename in noms_fichiers:
        if filename.endswith('.zip') and "__MACOSX" not in filename:
            # On définit le nom de l'instrument à partir du nom du ZIP
            # "all-samples/banjo.zip" -> "banjo"
            instrument_name = os.path.basename(filename).replace('.zip', '')
            instrument_path = os.path.join(target_folder, instrument_name)
            os.makedirs(instrument_path, exist_ok=True)
            
            print(f"Traitement de : {instrument_name}")
            
            try:
                with z.open(filename) as sub_zip_file:
                    sub_zip_data = io.BytesIO(sub_zip_file.read())
                    with zipfile.ZipFile(sub_zip_data) as sub_z:
                        
                        for sub_filename in sub_z.namelist():
                            if sub_filename.lower().endswith(('.mp3', '.wav')) and "__MACOSX" not in sub_filename:
                                # On récupère juste le nom du fichier audio
                                audio_basename = os.path.basename(sub_filename)
                                if not audio_basename: continue # Skip les dossiers vides
                                
                                # On définit le chemin final : data/scrap/philharmonia/banjo/note.mp3
                                final_path = os.path.join(instrument_path, audio_basename)
                                
                                # On écrit le fichier à cet endroit précis
                                with sub_z.open(sub_filename) as source, open(final_path, "wb") as target:
                                    target.write(source.read())
                                
                                files_extracted += 1
            except Exception as e:
                print(f"Erreur sur {instrument_name}: {e}")

    print(f"Succès ! {files_extracted} sons rangés par catégories dans {target_folder}")


etl_philharmonia_to_disk()