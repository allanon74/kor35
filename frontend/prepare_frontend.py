import os
import platform

# --- CONFIGURAZIONE ---
# Percorso WINDOWS dove salvare i file
WINDOWS_DESTINATION = r"C:\AI_CONTEXT" 

OUTPUT_FILENAME = "contesto_frontend.txt"

IGNORE_DIRS = {
    'node_modules', '.git', 'dist', 'build', 'coverage', 
    '.vscode', '.idea', 'public', 'assets', 'images'
}

INCLUDE_EXT = {
    '.js', '.jsx', '.ts', '.tsx', 
    '.css', '.scss', '.html', '.json'
}

IGNORE_FILES = {
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 
    'prepare_frontend.py', 'stats.json'
}

def get_smart_path(win_path):
    """Converte il percorso Windows in percorso WSL se necessario."""
    if platform.system() == "Linux" and "microsoft" in platform.release().lower():
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
    
    if not os.path.exists(dest_dir):
        try:
            os.makedirs(dest_dir)
        except OSError:
            print(f"ERRORE: Non riesco a creare la cartella {dest_dir}")
            return

    full_output_path = os.path.join(dest_dir, OUTPUT_FILENAME)
    
    print(f"--- ANALISI FRONTEND ---")
    print(f"Working Directory: {os.getcwd()}")
    print(f"Output su: {full_output_path}")
    
    count = 0
    try:
        with open(full_output_path, 'w', encoding='utf-8') as outfile:
            outfile.write("CONTESTO REACT/VITE (kor35-app)\n\n")
            
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