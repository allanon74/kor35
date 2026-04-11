# Cartella legacy

GitHub Actions carica **solo** i workflow in `.github/workflows/` alla **root del monorepo**.

Il vecchio file `workflows/deploy.yml` (solo frontend, deploy Apache / doppio job mirror) è stato **rimosso** per evitare confusione e doppie logiche: il deploy ufficiale è:

`/.github/workflows/deploy.yml`

(build frontend su CI, rsync `react_build`, deploy Docker produzione e mirror).
