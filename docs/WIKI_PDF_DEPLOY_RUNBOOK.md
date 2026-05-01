# Runbook Deploy Wiki PDF (Frontend + Backend)

Runbook operativo per rilasciare in sicurezza la funzionalita':
- generazione PDF wiki on-demand da staff;
- download ultimo PDF dalla homepage pubblica.

> Nota: questa feature richiede deploy **backend + frontend**.  
> Solo frontend non basta, perche' usa endpoint API nuovi.

---

## 1) Pre-check rapido

Eseguire dalla root progetto:

```bash
cd /home/django/progetti/kor35
git status
```

Confermare:
- branch corretta;
- nessun file locale non voluto;
- variabili ambiente presenti (`backend/.env.prod`, `backend/.env.mirror`).

---

## 2) Deploy Backend (OBBLIGATORIO)

La generazione PDF usa WeasyPrint + dipendenze native Docker: usare `deploy-be`.

### 2.1 Produzione

```bash
cd /home/django/progetti/kor35
make deploy-be ENV=prod
```

### 2.2 Mirror

```bash
cd /home/django/progetti/kor35
make deploy-be ENV=mirror
```

`deploy-be` fa:
- rebuild immagini backend/daphne;
- restart servizi backend/daphne;
- `migrate`;
- `collectstatic`.

---

## 3) Deploy Frontend

Se hai modifiche frontend da rilasciare:

### 3.1 Produzione

```bash
cd /home/django/progetti/kor35
make restart-fe ENV=prod
```

### 3.2 Mirror

```bash
cd /home/django/progetti/kor35
make restart-fe ENV=mirror
```

---

## 4) Smoke test post-deploy (2 minuti)

### 4.1 Health stack

```bash
cd /home/django/progetti/kor35
make status ENV=prod
make status ENV=mirror
```

Se necessario:

```bash
make logs ENV=prod
make logs ENV=mirror
```

### 4.2 Test funzionale staff (Prod e Mirror)

1. Login staff.
2. Apri Dashboard Staff.
3. Clicca `Genera Ultimo Manuale PDF`.
4. Verifica messaggio successo.

### 4.3 Test pubblico homepage wiki (Prod e Mirror)

1. Apri homepage wiki (`/`).
2. Verifica pulsante full-width `Scarica Manuale PDF Completo`.
3. Clic download:
   - se e' stato generato almeno una volta: deve scaricare/aprire PDF;
   - se mai generato: 404 atteso.

### 4.4 Test rendering contenuti PDF

Apri il PDF e verifica rapidamente:
- widget pulsanti non renderizzati (voluto);
- immagini presenti;
- widget lunghi senza pagina "vuota" con solo titolo;
- tabelle con header ripetuto e righe non spezzate male.

---

## 5) Cose da monitorare

- Persistenza file PDF:
  - percorso: `MEDIA_ROOT/wiki_exports/kor35-manuale-latest.pdf`;
  - deve stare su volume persistente, altrimenti si perde a restart container.
- Routing reverse proxy:
  - `/api/` e `/media/` devono puntare correttamente a Django.
- Permessi:
  - generazione PDF: staff-only;
  - download latest PDF: pubblico.

---

## 6) Rollback rapido

Se qualcosa va storto:

1. Torna al commit precedente stabile.
2. Redeploy backend:

```bash
cd /home/django/progetti/kor35
make deploy-be ENV=prod
make deploy-be ENV=mirror
```

3. Redeploy frontend:

```bash
make restart-fe ENV=prod
make restart-fe ENV=mirror
```

4. Riesegui smoke test del punto 4.

---

## 7) Checklist finale (go/no-go)

- [ ] `make deploy-be ENV=prod` completato
- [ ] `make deploy-be ENV=mirror` completato
- [ ] `make restart-fe ENV=prod` completato
- [ ] `make restart-fe ENV=mirror` completato
- [ ] generazione PDF staff OK su entrambi
- [ ] download homepage OK su entrambi
- [ ] rendering PDF verificato (immagini/widget/tabelle)

