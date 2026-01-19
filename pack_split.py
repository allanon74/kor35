import os
import platform

# --- CONFIGURAZIONE ---
# Percorso WINDOWS dove salvare i file
WINDOWS_DESTINATION = r"C:\AI_CONTEXT" 

# Dimensione massima per ogni file (400KB circa)
CHUNK_SIZE = 400000 

# Cartelle da IGNORARE
IGNORE_DIRS = {
    'node_modules', 'venv', 'env', '.venv', '__pycache__', 
    '.git', '.vscode', '.idea', 'dist', 'build', 'coverage',
    'media', 'static', 'staticfiles', 'filer_public', 
    'migrations', 'assets', 'images', 'fonts', 'public'
}

# Estensioni da INCLUDERE
INCLUDE_EXT = {
    # Backend
    '.py', '.html', 
    # Frontend
    '.js', '.jsx', '.ts', '.tsx', '.css', '.scss', 
    # Config/Data
    '.json', '.yaml', '.xml', '.md'
}

# File specifici da IGNORARE
IGNORE_FILES = {
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'poetry.lock', 
    'db.sqlite3', 'pack_split.py', 'prepare_context.py', 'stats.json',
    'Pipfile.lock', 'prepare_backend.py', 'prepare_frontend.py'
}

def get_smart_path(win_path):
    """Gestisce i percorsi tra WSL e Windows in modo sicuro."""
    if platform.system() == "Linux" and "microsoft" in platform.release().lower():
        # Parsing manuale per sicurezza
        if ":" in win_path:
            drive, rest = win_path.split(":", 1)
            drive_letter = drive.lower()
            clean_path = rest.replace('\\', '/')
            return f"/mnt/{drive_letter}{clean_path}"
    return win_path

def get_file_content(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if not content.strip(): return ""
            return f"\n{'='*40}\nFILE START: {filepath}\n{'='*40}\n{content}\n"
    except Exception as e:
        return f"\n[ERRORE lettura {filepath}: {e}]\n"

def save_chunk(directory, filename, content):
    full_path = os.path.join(directory, filename)
    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f" -> Salvato: {filename} in {directory}")
    except Exception as e:
        print(f"ERRORE salvataggio {filename}: {e}")

def main():
    project_name = os.path.basename(os.getcwd())
    
    # Calcola il percorso di destinazione corretto (Windows o WSL)
    dest_dir = get_smart_path(WINDOWS_DESTINATION)
    
    # Crea la cartella se non esiste
    if not os.path.exists(dest_dir):
        try:
            os.makedirs(dest_dir)
        except OSError:
            print(f"ERRORE: Non riesco a creare la cartella {dest_dir}")
            # Fallback alla cartella corrente se fallisce
            dest_dir = "."

    print(f"--- PACK SPLIT: {project_name} ---")
    print(f"Salvataggio in: {dest_dir}")
    
    current_content = f"PROGETTO: {project_name} - PARTE 1\n\n"
    current_chunk_size = 0
    chunk_index = 1
    total_files = 0
    
    for root, dirs, files in os.walk("."):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in INCLUDE_EXT and file not in IGNORE_FILES:
                filepath = os.path.join(root, file)
                clean_path = os.path.relpath(filepath, ".")
                
                file_text = get_file_content(clean_path)
                text_len = len(file_text)
                
                # Controllo dimensione chunk
                if current_chunk_size + text_len > CHUNK_SIZE:
                    # Salva il file corrente
                    filename = f"{project_name}_part_{chunk_index}.txt"
                    save_chunk(dest_dir, filename, current_content)
                    
                    # Prepara il prossimo
                    chunk_index += 1
                    current_content = f"PROGETTO: {project_name} - PARTE {chunk_index} (Continuazione)\n\n"
                    current_chunk_size = 0
                
                current_content += file_text
                current_chunk_size += text_len
                total_files += 1
                print(f"Aggiunto: {clean_path}", end='\r')

    # Salva l'ultimo pezzo
    if current_content:
        filename = f"{project_name}_part_{chunk_index}.txt"
        save_chunk(dest_dir, filename, current_content)

    print(f"\n\nFATTO! {total_files} file processati.")
    print(f"File generati in: {dest_dir}")

if __name__ == "__main__":
    main()