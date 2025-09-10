import os
import time
import itertools
import concurrent.futures as cf
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import re

BASE_URL = "http://10.11.200.159/"
ROOT_PATH = ".hidden/"
OUTPUT_DIR = "readmes"
TIMEOUT = 6
PAUSE_BETWEEN_REQUESTS = 0.02
MAX_WORKERS = 16
FILENAMES = "README"

os.makedirs(OUTPUT_DIR, exist_ok=True)

letters = [chr(c) for c in range(ord('a'), ord('z') + 1)]

def fetch_one(path_prefix):
    """Tente de récupérer un readme dans path_prefix (ex: .hidden/a/b/c/)."""
    results = []
    url = urljoin(BASE_URL, path_prefix + FILENAMES)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (pentest-legal/1.0)"})
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status == 200:
                data = resp.read()
                if data and len(data) != 34:  # Filtrer les README de taille différente de 34
                    # Créer un nom de fichier basé sur le chemin
                    safe_path = path_prefix.strip("/").replace("/", "_").replace(".", "")
                    out_path = os.path.join(OUTPUT_DIR, f"{safe_path}_README")
                    with open(out_path, "wb") as f:
                        f.write(data)
                    results.append((url, out_path, len(data)))

    except URLError as e:
        # Host down / refus -> remonter l'info minimalement
        return [("ERROR", url, str(e))]
    except Exception as e:
        return [("ERROR", url, repr(e))]
    finally:
        time.sleep(PAUSE_BETWEEN_REQUESTS)
    return results

def get_directories_from_html(url):
    """Récupère les répertoires depuis une page HTML"""
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (pentest-legal/1.0)"})
    try:
        with urlopen(req, timeout=TIMEOUT) as resp:
            if resp.status == 200:
                html = resp.read().decode('utf-8', errors='ignore')
                # Chercher les liens <a href="directory/"> suivi d'une date
                pattern = r'<a href="([^"]+/)">.*?(\d{2}-\w{3}-\d{4} \d{2}:\d{2})\s+(-|\d+)'
                matches = re.findall(pattern, html)
                directories = []
                for href, date, size in matches:
                    if href not in ['../', './']:  # Ignorer parent et current dir
                        directories.append(href.rstrip('/'))
                return directories
    except Exception as e:
        print(f"Erreur lors de la récupération de {url}: {e}")
        return []
    return []

def get_all_paths():
    """Récupère récursivement tous les chemins jusqu'à 3 niveaux de profondeur"""
    all_paths = []
    
    # Niveau 1: .hidden/
    base_url = urljoin(BASE_URL, ROOT_PATH)
    level1_dirs = get_directories_from_html(base_url)
    print(f"[*] Trouvé {len(level1_dirs)} répertoires niveau 1")
    
    for dir1 in level1_dirs:
        # Niveau 2: .hidden/dir1/
        level1_path = f"{ROOT_PATH}{dir1}/"
        level2_url = urljoin(BASE_URL, level1_path)
        level2_dirs = get_directories_from_html(level2_url)
        
        for dir2 in level2_dirs:
            # Niveau 3: .hidden/dir1/dir2/
            level2_path = f"{ROOT_PATH}{dir1}/{dir2}/"
            level3_url = urljoin(BASE_URL, level2_path)
            level3_dirs = get_directories_from_html(level3_url)
            
            for dir3 in level3_dirs:
                # Chemin final: .hidden/dir1/dir2/dir3/
                final_path = f"{ROOT_PATH}{dir1}/{dir2}/{dir3}/"
                all_paths.append(final_path)
                
        time.sleep(PAUSE_BETWEEN_REQUESTS)  # Pause entre les requêtes
    
    return all_paths

def main():
    paths = get_all_paths()
    found = []
    errors = []

    print(f"[*] Exploration de {len(paths)} chemins trouvés...")
    print(f"[*] Recherche des README avec une taille différente de 34 octets...")

    with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for res in ex.map(fetch_one, paths, chunksize=64):
            if not res:
                continue
            for item in res:
                if item[0] == "ERROR":
                    errors.append(item)
                else:
                    found.append(item)

    print(f"\n[+] README récupérés (taille != 34) : {len(found)}")
    for url, out_path, size in sorted(found):
        print(f" - {url}  ->  {out_path}  ({size} bytes)")

    if errors:
        print(f"\n[!] Erreurs : {len(errors)}")
        # On affiche seulement les 10 premières pour garder la sortie lisible
        for e in errors[:10]:
            print("   ", e)

    # Afficher le contenu des README trouvés
    if found:
        print(f"\n[+] Contenu des README trouvés :")
        for url, out_path, size in sorted(found):
            print(f"\n--- Contenu de {url} ({size} bytes) ---")
            try:
                with open(out_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().strip()
                    print(content)
            except Exception as e:
                print(f"Erreur lors de la lecture : {e}")
            print("-" * 50)

if __name__ == "__main__":
    main()
