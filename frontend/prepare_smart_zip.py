import os
import zipfile
import platform
from datetime import datetime

# --- CONFIGURAZIONE ---
# Dove salvare lo zip (la tua cartella condivisa)
WINDOWS_DESTINATION = r"C:\AI_CONTEXT"

# Cartelle da IGNORARE COMPLETAMENTE (riduce drasticamente la dimensione)
IGNORE_DIRS = {
    'node_modules', 'venv', 'env', '.venv', '__pycache__', 
    '.git', '.vscode', '.idea', 'dist', 'build', 'coverage',
    'media', 'static', 'staticfiles', 'filer_public', # Asset pesanti
    'migrations' # Spesso inutili per la logica pura
}

# Estensioni da INCLUDERE (solo codice utile)
INCLUDE_EXT = {
    # Backend
    '.py', '.html', 
    # Frontend
    '.js', '.jsx', '.ts', '.tsx', '.css', '.scss', '.json',
    # Config
    '.yaml', '.yml', '.xml', '.md'
}

# File specifici da escludere
IGNORE_FILES = {
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock', 
    'db.sqlite3', 'prepare_smart_zip.py', 'prepare_backend.py', 'prepare_frontend.py',
    'stats.json'
}

def get_smart_path(win_path):
    """Gestisce i percorsi tra WSL e Windows."""
    if platform.system() == "Linux" and "microsoft" in platform.release().lower():
        if ":" in win_path:
            drive, rest = win_path.split(":", 1)
            drive_letter = drive.lower()
            clean_path = rest.replace('\\', '/')
            return f"/mnt/{drive_letter}{clean_path}"
    return win_path

def main():
    # Determina il nome dello zip in base alla cartella corrente
    project_name = os.path.basename(os.getcwd())
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    zip_filename = f"{project_name}_context_{timestamp}.zip"
    
    dest_dir = get_smart_path(WINDOWS_DESTINATION)
    
    if not os.path.exists(dest_dir):
        try:
            os.makedirs(dest_dir)
        except OSError:
            print(f"ERRORE: Impossibile creare {dest_dir}")
            return

    full_zip_path = os.path.join(dest_dir, zip_filename)
    
    print(f"--- CREAZIONE SMART ZIP PER: {project_name} ---")
    print(f"Destinazione: {full_zip_path}")
    
    file_count = 0
    skipped_count = 0
    
    try:
        with zipfile.ZipFile(full_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk("."):
                # Rimuove le cartelle ignorate dalla scansione
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in INCLUDE_EXT and file not in IGNORE_FILES:
                        file_path = os.path.join(root, file)
                        # Calcola il percorso relativo per mantenere la struttura nel zip
                        arcname = os.path.relpath(file_path, ".")
                        
                        try:
                            zipf.write(file_path, arcname)
                            file_count += 1
                            print(f"Zippato: {arcname}", end='\r')
                        except Exception as e:
                            print(f"\nErrore su {file}: {e}")
                    else:
                        skipped_count += 1
                        
        print(f"\n\nSUCCESSO! Zip creato con {file_count} file sorgente.")
        print(f"(Ignorati {skipped_count} file inutili/binari)")
        print(f"Ora carica '{zip_filename}' nella chat.")
        
    except Exception as e:
        print(f"\nERRORE CRITICO: {e}")

if __name__ == "__main__":
    main()