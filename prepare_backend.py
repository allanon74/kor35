import os
import platform

# --- CONFIGURAZIONE ---
# Percorso WINDOWS dove salvare i file (es. C:\AI_CONTEXT)
WINDOWS_DESTINATION = r"C:\AI_CONTEXT"

OUTPUT_FILENAME = "contesto_backend.txt"

IGNORE_DIRS = {
    'venv', 'env', '.venv', '__pycache__', '.git', '.vscode', '.idea',
    'media', 'static', 'migrations', 'htmlcov', 'staticfiles', 'filer_public'
}

INCLUDE_EXT = {
    '.py', '.html', '.css', '.js'
}

IGNORE_FILES = {
    'db.sqlite3', 'poetry.lock', 'Pipfile.lock', 
    'prepare_backend.py'
}

def get_smart_path(win_path):
    """Converte il percorso Windows in percorso WSL se necessario."""
    # Controllo se siamo su WSL
    if platform.system() == "Linux" and "microsoft" in platform.release().lower():
        # Parsing manuale per sicurezza (os.path.splitdrive non funziona bene su Linux con path Windows)
        if ":" in win_path:
            drive, rest = win_path.split(":", 1)
            drive_letter = drive.lower()
            # FIX: Eseguo il replace fuori dalla f-string
            clean_path = rest.replace('\\', '/')
            return f"/mnt/{drive_letter}{clean_path}"
    return win_path

def get_file_content(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            return f"\n{'='*50}\nFILE: {filepath}\n{'='*50}\n{content}\n"
    except Exception as e:
        return f"\n[ERRORE lettura {filepath}: {e}]\n"

def main():
    dest_dir = get_smart_path(WINDOWS_DESTINATION)
    
    # Crea la cartella se non esiste
    if not os.path.exists(dest_dir):
        try:
            os.makedirs(dest_dir)
        except OSError:
            print(f"ERRORE: Non riesco a creare la cartella {dest_dir}")
            return

    full_output_path = os.path.join(dest_dir, OUTPUT_FILENAME)

    print(f"--- ANALISI BACKEND ---")
    print(f"Working Directory: {os.getcwd()}")
    print(f"Output su: {full_output_path}")
    
    count = 0
    try:
        with open(full_output_path, 'w', encoding='utf-8') as outfile:
            outfile.write("CONTESTO DJANGO (kor35)\n\n")
            
            for root, dirs, files in os.walk("."):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in INCLUDE_EXT and file not in IGNORE_FILES:
                        filepath = os.path.join(root, file)
                        clean_path = os.path.relpath(filepath, ".")
                        outfile.write(get_file_content(clean_path))
                        count += 1
        print(f"SUCCESSO! {count} file salvati in {full_output_path}")
    except Exception as e:
        print(f"ERRORE SCRITTURA FILE: {e}")

if __name__ == "__main__":
    main()