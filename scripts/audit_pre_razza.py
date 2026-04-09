#!/usr/bin/env python3
"""
Confronta il codice pre-RAZZE (commit 953bd6b) con la working tree.

Controlli:
- ogni classe top-level in personaggi/models.py e i suoi campi ``= models.`` (solo corpo classe,
  indentazione +4; stesso criterio su pre e post → coerente per il merge RAZZE);
- classi in views.py / serializers.py;
- voci INSTALLED_APPS in settings.py;
- riferimenti views.* / views_staff.* in personaggi/urls.py.

Opzionale: ``python3 scripts/audit_pre_razza.py --with-django-check``
(esegue anche ``manage.py check`` con l'interprete corrente, es. venv).

Limiti: non vede campi solo sulle classi base (es. nome su Inventario per Personaggio):
per quello serve ``manage.py check`` o lo schema DB.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PRE = "953bd6b"
BASE = Path(__file__).resolve().parent.parent


def git_show(rev: str, path: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(BASE), "show", f"{rev}:{path}"],
        text=True,
        stderr=subprocess.PIPE,
    )


def read_head(path: str) -> str:
    return (BASE / path).read_text(encoding="utf-8", errors="replace")


def top_level_classes_and_model_fields(source: str) -> dict[str, set[str]]:
    """
    Classi a livello modulo (riga 'class Nome') e campi models.* nel corpo a indent +4.
    Supporta più assegnazioni sulla stessa riga separate da ';'.
    """
    lines = source.splitlines()
    current: str | None = None
    fields: dict[str, set[str]] = {}
    class_body_indent: int | None = None

    for line in lines:
        if re.match(r"^class \w+", line):
            m = re.match(r"^class (\w+)", line)
            current = m.group(1) if m else None
            fields.setdefault(current, set())
            class_body_indent = len(line) - len(line.lstrip())
            continue

        if current is None or class_body_indent is None:
            continue

        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(stripped)
        if indent != class_body_indent + 4:
            continue
        if stripped.startswith("class ") or stripped.startswith("def "):
            continue

        for fname in re.findall(r"(\w+)\s*=\s*models\.", stripped):
            fields[current].add(fname)

    return fields


def extract_class_names(source: str, pattern: str = r"^class (\w+)\b") -> set[str]:
    return {m.group(1) for line in source.splitlines() if (m := re.match(pattern, line))}


def installed_apps_entries(source: str) -> set[str]:
    """Tutte le stringhe letterali in INSTALLED_APPS = [ ... ]."""
    m = re.search(r"INSTALLED_APPS\s*=\s*\[(.*?)\n\s*\]", source, re.DOTALL)
    if not m:
        return set()
    block = m.group(1)
    return {x.group(1) for x in re.finditer(r"['\"]([^'\"]+)['\"]", block)}


def main() -> int:
    files_models = "personaggi/models.py"
    files_views = "personaggi/views.py"
    files_serial = "personaggi/serializers.py"
    files_urls = "personaggi/urls.py"
    files_settings = "kor35/settings.py"

    old_models = git_show(PRE, files_models)
    new_models = read_head(files_models)

    old_f = top_level_classes_and_model_fields(old_models)
    new_f = top_level_classes_and_model_fields(new_models)

    issues = []

    for cls in sorted(old_f.keys()):
        if cls not in new_f:
            issues.append(f"[models] Classe mancante: {cls}")
            continue
        missing_fields = old_f[cls] - new_f[cls]
        if missing_fields:
            issues.append(
                f"[models] {cls}: campi models.* presenti pre-RAZZE ma assenti ora: "
                f"{sorted(missing_fields)}"
            )

    old_views = extract_class_names(git_show(PRE, files_views))
    new_views = extract_class_names(read_head(files_views))
    for v in sorted(old_views - new_views):
        issues.append(f"[views] Classe mancante: {v}")

    old_ser = extract_class_names(git_show(PRE, files_serial))
    new_ser = extract_class_names(read_head(files_serial))
    for s in sorted(old_ser - new_ser):
        issues.append(f"[serializers] Classe mancante: {s}")

    # Ogni views.Xxx usato in urls deve esistere in views (classe o funzione)
    urls_src = read_head(files_urls)
    missing_view_refs = []
    for m in re.finditer(r"\bviews\.([A-Za-z_][A-Za-z0-9_]*)", urls_src):
        ref = m.group(1)
        if ref not in new_views:
            missing_view_refs.append(ref)
    for m in re.finditer(r"views\.([a-z_][a-z0-9_]*)\s*\(", urls_src):
        ref = m.group(1)
        if ref not in new_views and ref not in ("qr_code_html_view", "qr_code_list_view", "qr_code_detail_view", "equipaggia_item_view", "assembla_item_view", "smonta_item_view", "forgia_item_view"):
            if ref not in missing_view_refs:
                missing_view_refs.append(ref)

    # funzioni view module-level (def xxx)
    new_defs = set()
    for line in read_head(files_views).splitlines():
        if m := re.match(r"^def ([a-z_][a-z0-9_]*)", line):
            new_defs.add(m.group(1))

    for ref in sorted(set(missing_view_refs)):
        if ref in new_defs:
            continue
        issues.append(f"[urls→views] Riferimento 'views.{ref}' ma non è classe né def in views.py")

    staff_src = read_head("personaggi/views_staff.py")
    staff_classes = extract_class_names(staff_src)
    staff_defs = {
        m.group(1)
        for line in staff_src.splitlines()
        if (m := re.match(r"^def ([a-z_][a-z0-9_]*)", line))
    }
    for m in re.finditer(r"views_staff\.([A-Za-z_][A-Za-z0-9_]*)", read_head(files_urls)):
        ref = m.group(1)
        if ref not in staff_classes and ref not in staff_defs:
            issues.append(
                f"[urls→views_staff] Riferimento 'views_staff.{ref}' assente in views_staff.py"
            )

    old_settings = git_show(PRE, files_settings)
    new_settings = read_head(files_settings)
    apps_old = installed_apps_entries(old_settings)
    apps_new = installed_apps_entries(new_settings)
    for app in sorted(apps_old - apps_new):
        if app.startswith("#"):
            continue
        issues.append(f"[settings] INSTALLED_APPS: era presente pre-RAZZE, assente ora: {app!r}")

    if issues:
        print("=== Audit pre-RAZZE (953bd6b) vs working tree ===\n")
        for i in issues:
            print(i)
        print(f"\nTotale problemi: {len(issues)}")
        return 1

    print(
        "OK: allineamento 953bd6b → working tree (models/views/serializers/settings), "
        "urls risolvibili."
    )
    print(
        "\nNota: per admin (E108, …) usa `python manage.py check` — i campi ereditati "
        "non sono rilevabili senza caricare Django."
    )
    print("\n--- File toccati dal commit RAZZE (29f5655) rispetto a pre-RAZZE ---")
    names = subprocess.check_output(
        ["git", "-C", str(BASE), "diff", "--name-only", PRE, "29f5655"],
        text=True,
    ).strip()
    print(names or "(nessuno)")
    return 0


if __name__ == "__main__":
    if "--with-django-check" in sys.argv:
        rc = main()
        if rc != 0:
            sys.exit(rc)
        print("\n--- python manage.py check ---")
        r = subprocess.run(
            [sys.executable, str(BASE / "manage.py"), "check"],
            cwd=str(BASE),
        )
        sys.exit(r.returncode)
    sys.exit(main())
