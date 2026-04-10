Backend Django (target monorepo layout).

Questo branch `docker` sta migrando gradualmente il backend da root verso `backend/`.
Durante la fase di transizione, il codice sorgente resta ancora in root per non
rompere pipeline e deploy esistenti.

Step successivi:
- spostamento app Django e `manage.py` in `backend/`
- aggiornamento script/deploy a path nuovi
- rimozione compat layer temporanei
