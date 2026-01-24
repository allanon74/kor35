# 🚀 Deploy Sistema QR Code & A_vista Unificato

## 📋 Riepilogo Modifiche

### Backend

1. **`gestione_plot/models.py`**
   - `QuestVista`: Aggiunti campi FK per tutti i tipi a_vista (personaggio, oggetto, tessitura, infusione, cerimoniale)
   - Tutti con `related_name` univoci

2. **`gestione_plot/serializers.py`**
   - `QuestVistaSerializer`: Aggiunti `_details` serializer methods per tutti i tipi

3. **`gestione_plot/views.py`**
   - **NUOVO** `EventoViewSet.a_vista_disponibili()`: Restituisce tutti gli A_vista con tipo calcolato
   - `QuestVistaViewSet.perform_create()`: Gestione intelligente creazione con a_vista_id
   - `EventoViewSet.get_queryset()`: Prefetch ottimizzato per tutti i campi vista
   - `QuestViewSet.get_queryset()`: Prefetch ottimizzato
   - `risorse_editor`: Inventari filtrati (esclude personaggi), oggetti leggeri

### Frontend

1. **`src/api.js`**
   - Aggiunto `getAVistaDisponibili()`

2. **`src/components/PlotTab.jsx`**
   - Carica `a_vista` in parallelo con risorse
   - Aggiunge `a_vista: []` agli stati

3. **`src/components/QuestItem.jsx`**
   - Semplificato drasticamente: usa solo `risorse.a_vista`
   - Filtra per tipo
   - Invia `{quest, tipo, a_vista_id}` al backend

4. **`src/components/editors/SearchableSelect.jsx`**
   - Usa React Portal per dropdown sempre visibile
   - ID univoco per gestione eventi click
   - Fix gestione click fuori con Portal

## 🔧 Istruzioni Deploy

### 1. Backend (Server Remoto)

```bash
ssh tuoserver
cd /home/django/progetti/kor35
source venv/bin/activate

# IMPORTANTE: Crea migration per gestione_plot
python manage.py makemigrations gestione_plot

# Dovresti vedere:
# Migrations for 'gestione_plot':
#   gestione_plot/migrations/0XXX_auto_YYYYMMDD_HHMM.py
#     - Add field personaggio to questvista
#     - Add field oggetto to questvista
#     - Add field tessitura to questvista
#     - Add field infusione to questvista
#     - Add field cerimoniale to questvista
#     - Alter field tipo on questvista (max_length aumentato se necessario)

# Applica migration
python manage.py migrate gestione_plot

# Restart server
sudo systemctl restart gunicorn
sudo systemctl status gunicorn
```

### 2. Frontend

Il deploy frontend avviene automaticamente via GitHub Actions quando fai push su `main`.

```bash
# Dalla tua macchina di sviluppo
cd /home/django/progetti/kor35
git add .
git commit -m "Sistema QR unificato con A_vista + SearchableSelect Portal fix"
git push origin main

cd /home/django/progetti/kor35-app
git add .
git commit -m "Sistema QR unificato con A_vista + SearchableSelect Portal fix"
git push origin main
```

## ✅ Verifica Funzionamento

### Test Backend

```bash
# Test endpoint a_vista_disponibili
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://www.kor35.it/plot/api/eventi/a_vista_disponibili/

# Dovresti vedere:
# {
#   "a_vista": [
#     {"id": 1, "nome": "Nomepg", "tipo": "PG", "tipo_display": "Personaggio (PG)"},
#     {"id": 2, "nome": "Spada", "tipo": "OGG", "tipo_display": "Oggetto"},
#     ...
#   ]
# }
```

### Test Frontend

1. Vai su **Staff Dashboard** → **Plot**
2. Apri una Quest
3. Scorri in fondo a **"Elementi di Gioco & QR Code"**
4. Verifica:
   - ✅ Dropdown tipo funziona
   - ✅ Dropdown elemento si popola correttamente
   - ✅ Puoi selezionare elementi (click funziona)
   - ✅ Il dropdown rimane visibile anche se va oltre i bordi
   - ✅ Il salvataggio funziona
   - ✅ Gli elementi salvati mostrano il nome corretto (non "Elemento")

## 🐛 Troubleshooting

### Dropdown non si apre o non seleziona

- **Cache browser**: Ctrl+F5 per forzare reload
- **Verifica console**: Cerca errori JS
- **Verifica network**: L'endpoint `/a_vista_disponibili/` deve restituire dati

### "Elemento" invece del nome

- **Verifica migration**: `python manage.py showmigrations gestione_plot`
- **Verifica prefetch**: I `_details` devono essere popolati
- **Console backend**: Guarda i log Django per N+1 queries

### Inventari mostrano personaggi

- **Verifica query**: `Inventario.objects.filter(personaggio__isnull=True)`
- **Database**: `SELECT * FROM personaggi_inventario WHERE id NOT IN (SELECT id FROM personaggi_personaggio);`

## 📊 Risultato Atteso

- ✅ 8 tipi A_vista supportati: PG, PNG, INV, OGG, TES, INF, CER, MAN
- ✅ PG/PNG distinti automaticamente da `tipologia.giocante`
- ✅ Inventari escludono personaggi
- ✅ Dropdown funzionante con Portal
- ✅ Nomi corretti per tutti i tipi
- ✅ Performance ottimizzate (prefetch, cache)
