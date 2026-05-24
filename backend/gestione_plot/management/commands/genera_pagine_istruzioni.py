"""
Management command per generare pagine di istruzione per l'app Kor35.

Questo script:
1. Crea un utente di sistema (se non esiste) con permessi staff
2. Genera pagine di istruzione complete per l'utilizzo dell'app
3. Le inserisce direttamente nel database

Uso:
    python manage.py genera_pagine_istruzioni
    python manage.py genera_pagine_istruzioni --force  # Sovrascrive pagine esistenti
    python manage.py genera_pagine_istruzioni --utente-sistema kor35_system  # Nome utente personalizzato
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from gestione_plot.models import PaginaRegolamento
import os

User = get_user_model()


class Command(BaseCommand):
    help = 'Genera pagine di istruzione per l\'app Kor35 e crea un utente di sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Sovrascrive le pagine esistenti con lo stesso slug',
        )
        parser.add_argument(
            '--utente-sistema',
            type=str,
            default='kor35_system',
            help='Username per l\'utente di sistema (default: kor35_system)',
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password per l\'utente di sistema (se non specificata, viene generata)',
        )

    def create_system_user(self, username, password=None):
        """Crea o recupera l'utente di sistema"""
        try:
            user = User.objects.get(username=username)
            self.stdout.write(self.style.WARNING(f'Utente "{username}" già esistente'))
            return user
        except User.DoesNotExist:
            if password is None:
                import secrets
                password = secrets.token_urlsafe(32)
            
            user = User.objects.create_user(
                username=username,
                email=f'{username}@kor35.it',
                password=password,
                is_staff=True,
                is_superuser=True,
            )
            self.stdout.write(self.style.SUCCESS(f'✓ Utente di sistema "{username}" creato'))
            self.stdout.write(self.style.WARNING(f'  Password: {password}'))
            self.stdout.write(self.style.WARNING('  ⚠️ Salva questa password in un luogo sicuro!'))
            return user

    def get_or_create_page(self, slug, titolo, contenuto, parent=None, ordine=0, 
                          public=True, visibile_solo_staff=False, force=False):
        """Crea o aggiorna una pagina wiki"""
        try:
            page = PaginaRegolamento.objects.get(slug=slug)
            if force:
                page.titolo = titolo
                page.contenuto = contenuto
                page.parent = parent
                page.ordine = ordine
                page.public = public
                page.visibile_solo_staff = visibile_solo_staff
                page.save()
                self.stdout.write(self.style.WARNING(f'  ↻ Pagina "{titolo}" aggiornata'))
                return page
            else:
                self.stdout.write(self.style.WARNING(f'  ⊘ Pagina "{titolo}" già esistente (usa --force per sovrascrivere)'))
                return page
        except PaginaRegolamento.DoesNotExist:
            page = PaginaRegolamento.objects.create(
                slug=slug,
                titolo=titolo,
                contenuto=contenuto,
                parent=parent,
                ordine=ordine,
                public=public,
                visibile_solo_staff=visibile_solo_staff,
            )
            self.stdout.write(self.style.SUCCESS(f'  ✓ Pagina "{titolo}" creata'))
            return page

    def handle(self, *args, **options):
        force = options.get('force', False)
        username = options.get('utente_sistema', 'kor35_system')
        password = options.get('password', None)

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Generazione Pagine di Istruzione Kor35'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        # 1. Crea utente di sistema
        self.stdout.write('\n📋 Passo 1: Creazione utente di sistema...')
        system_user = self.create_system_user(username, password)

        # 2. Genera pagine di istruzione
        self.stdout.write('\n📋 Passo 2: Generazione pagine di istruzione...')

        with transaction.atomic():
            # Pagina parent: Istruzioni
            pagina_istruzioni = self.get_or_create_page(
                slug='istruzioni',
                titolo='Istruzioni',
                contenuto='''
<h2>Istruzioni per l'utilizzo dell'App Kor35</h2>
<p>Benvenuto nella sezione istruzioni! Qui troverai tutte le guide per utilizzare al meglio l'applicazione.</p>

<h3>Guide Generali</h3>
<ul>
    <li><a href="/regolamento/istruzioni/primo-accesso">Primo Accesso</a> - Come iniziare</li>
    <li><a href="/regolamento/istruzioni/navigazione-app">Navigazione nell'App</a> - Scopri l'interfaccia</li>
    <li><a href="/regolamento/istruzioni/gestione-personaggio">Gestione del Personaggio</a> - Statistiche e abilità</li>
</ul>

<h3>Guide per Sezione</h3>
<ul>
    <li><a href="/regolamento/istruzioni/inventario">Inventario e Zaino</a> - Gestisci i tuoi oggetti</li>
    <li><a href="/regolamento/istruzioni/abilita">Abilità</a> - Competenze e talenti</li>
    <li><a href="/regolamento/istruzioni/tessiture">Tessiture</a> - Modifiche permanenti</li>
    <li><a href="/regolamento/istruzioni/infusioni">Infusioni</a> - Potenziamenti temporanei</li>
    <li><a href="/regolamento/istruzioni/cerimoniali">Cerimoniali</a> - Riti e rituali</li>
    <li><a href="/regolamento/istruzioni/messaggi">Messaggi</a> - Comunicazione con altri giocatori</li>
    <li><a href="/regolamento/istruzioni/scanner-qr">Scanner QR</a> - Come usare lo scanner</li>
    <li><a href="/regolamento/istruzioni/diario">Diario</a> - Log delle azioni</li>
    <li><a href="/regolamento/istruzioni/transazioni">Transazioni</a> - Scambi e trasferimenti</li>
    <li><a href="/regolamento/istruzioni/scommesse">Scommesse</a> - Pronostici sportivi in-game</li>
</ul>
                ''',
                ordine=1,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina principale: Guida all'utilizzo (sotto istruzioni)
            pagina_principale = self.get_or_create_page(
                slug='guida-utilizzo-app',
                titolo='Guida all\'utilizzo dell\'App Kor35',
                contenuto='''
<h2>Benvenuto nell'App Kor35!</h2>
<p>Questa guida ti aiuterà a comprendere tutte le funzionalità dell'applicazione Kor35.</p>

<h3>Indice delle Guide</h3>
<ul>
    <li><a href="/regolamento/primo-accesso">Primo Accesso</a> - Come iniziare</li>
    <li><a href="/regolamento/navigazione-app">Navigazione nell'App</a> - Scopri l'interfaccia</li>
    <li><a href="/regolamento/gestione-personaggio">Gestione del Personaggio</a> - Statistiche e abilità</li>
    <li><a href="/regolamento/inventario-oggetti">Inventario e Oggetti</a> - Gestisci i tuoi oggetti</li>
    <li><a href="/regolamento/messaggi-comunicazione">Messaggi e Comunicazione</a> - Interagisci con gli altri</li>
    <li><a href="/regolamento/quest-missioni">Quest e Missioni</a> - Partecipa alle avventure</li>
    <li><a href="/regolamento/amministrazione">Area Amministrazione</a> - Per lo staff</li>
</ul>

<h3>Supporto</h3>
<p>Se hai domande o problemi, contatta lo staff tramite l'app o visita il forum della community.</p>
                ''',
                ordine=1,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Primo Accesso
            self.get_or_create_page(
                slug='primo-accesso',
                titolo='Primo Accesso all\'App',
                contenuto='''
<h2>Come accedere all'App Kor35</h2>

<h3>1. Registrazione</h3>
<p>Se non hai ancora un account:</p>
<ol>
    <li>Vai alla pagina di login</li>
    <li>Clicca su "Registrati" o "Crea Account"</li>
    <li>Compila il form con i tuoi dati</li>
    <li>Verifica la tua email (se richiesto)</li>
</ol>

<h3>2. Login</h3>
<p>Per accedere all'app:</p>
<ol>
    <li>Vai su <strong>https://app.kor35.it</strong> o <strong>https://www.kor35.it/admin</strong></li>
    <li>Inserisci il tuo username e password</li>
    <li>Clicca su "Accedi"</li>
</ol>

<h3>3. Prima Configurazione</h3>
<p>Al primo accesso potresti dover:</p>
<ul>
    <li>Completare il profilo del tuo personaggio</li>
    <li>Configurare le statistiche base</li>
    <li>Esplorare l'interfaccia principale</li>
</ul>

<h3>4. Navigazione</h3>
<p>Una volta dentro, vedrai:</p>
<ul>
    <li><strong>Home</strong>: Dashboard principale con informazioni rilevanti</li>
    <li><strong>Personaggio</strong>: Gestione del tuo personaggio</li>
    <li><strong>Inventario</strong>: I tuoi oggetti e equipaggiamenti</li>
    <li><strong>Messaggi</strong>: Comunicazione con altri giocatori</li>
    <li><strong>Quest</strong>: Missioni e avventure disponibili</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=1,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Navigazione
            self.get_or_create_page(
                slug='navigazione-app',
                titolo='Navigazione nell\'App',
                contenuto='''
<h2>Come navigare nell'App Kor35</h2>

<h3>Struttura dell'Interfaccia</h3>
<p>L'app è organizzata in sezioni principali accessibili dalla barra laterale o dal menu:</p>

<h3>📱 Sezioni Principali</h3>

<h4>🏠 Home</h4>
<p>La dashboard principale mostra:</p>
<ul>
    <li>Eventi in corso e prossimi</li>
    <li>Notifiche e messaggi importanti</li>
    <li>Stato del personaggio (salute, risorse, etc.)</li>
    <li>Accesso rapido alle funzioni più usate</li>
</ul>

<h4>👤 Personaggio</h4>
<p>Gestisci tutte le informazioni del tuo personaggio:</p>
<ul>
    <li><strong>Statistiche</strong>: Forza, Destrezza, Intelligenza, etc.</li>
    <li><strong>Abilità</strong>: Competenze e talenti</li>
    <li><strong>Caratteristiche</strong>: Tratti distintivi del personaggio</li>
    <li><strong>Infusioni</strong>: Potenziamenti magici o tecnologici</li>
    <li><strong>Tessiture</strong>: Modifiche permanenti al corpo</li>
</ul>

<h4>🎒 Inventario</h4>
<p>Gestisci i tuoi oggetti:</p>
<ul>
    <li>Visualizza tutti gli oggetti posseduti</li>
    <li>Equipaggia oggetti</li>
    <li>Usa consumabili</li>
    <li>Organizza per categorie</li>
</ul>

<h4>💬 Messaggi</h4>
<p>Comunica con altri giocatori:</p>
<ul>
    <li>Messaggi privati</li>
    <li>Conversazioni di gruppo</li>
    <li>Notifiche e avvisi</li>
</ul>

<h4>⚔️ Quest</h4>
<p>Partecipa alle avventure:</p>
<ul>
    <li>Visualizza quest disponibili</li>
    <li>Accetta missioni</li>
    <li>Traccia il progresso</li>
    <li>Completa obiettivi</li>
</ul>

<h3>🔍 Ricerca e Filtri</h3>
<p>Molte sezioni hanno funzioni di ricerca e filtri per trovare rapidamente ciò che cerchi.</p>

<h3>📱 Versione Mobile</h3>
<p>L'app è responsive e funziona su dispositivi mobili. Il menu si adatta automaticamente allo schermo.</p>
                ''',
                parent=pagina_istruzioni,
                ordine=2,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Gestione Personaggio
            self.get_or_create_page(
                slug='gestione-personaggio',
                titolo='Gestione del Personaggio',
                contenuto='''
<h2>Gestione Completa del Personaggio</h2>

<h3>📊 Statistiche Base</h3>
<p>Le statistiche rappresentano le capacità fondamentali del tuo personaggio:</p>
<ul>
    <li><strong>Forza</strong>: Potenza fisica e capacità di combattimento corpo a corpo</li>
    <li><strong>Destrezza</strong>: Agilità, riflessi e precisione</li>
    <li><strong>Costituzione</strong>: Resistenza fisica e salute</li>
    <li><strong>Intelligenza</strong>: Capacità mentali e apprendimento</li>
    <li><strong>Saggezza</strong>: Percezione e intuizione</li>
    <li><strong>Carisma</strong>: Capacità sociali e leadership</li>
</ul>

<h3>🎯 Abilità</h3>
<p>Le abilità sono competenze specifiche che il tuo personaggio può sviluppare:</p>
<ul>
    <li>Visualizza tutte le abilità disponibili</li>
    <li>Vedi il tuo livello di competenza in ciascuna</li>
    <li>Usa punti esperienza per migliorare le abilità</li>
    <li>Alcune abilità possono essere sbloccate completando quest o eventi</li>
</ul>

<h3>✨ Caratteristiche Speciali</h3>
<p>Le caratteristiche includono:</p>
<ul>
    <li><strong>Aure</strong>: Poteri magici o tecnologici unici</li>
    <li><strong>Tratti</strong>: Caratteristiche innate del personaggio</li>
    <li><strong>Modificatori</strong>: Bonus o penalità temporanee o permanenti</li>
</ul>

<h3>🔬 Infusioni</h3>
<p>Le infusioni sono potenziamenti che possono essere applicati al personaggio:</p>
<ul>
    <li>Visualizza infusioni disponibili</li>
    <li>Applica infusioni per ottenere bonus</li>
    <li>Gestisci slot di infusione disponibili</li>
    <li>Alcune infusioni possono avere effetti collaterali</li>
</ul>

<h3>🧬 Tessiture</h3>
<p>Le tessiture sono modifiche permanenti al corpo del personaggio:</p>
<ul>
    <li>Modifiche biologiche o tecnologiche</li>
    <li>Effetti permanenti (positivi o negativi)</li>
    <li>Richiedono spesso procedure speciali o eventi</li>
</ul>

<h3>📈 Punteggi e Livelli</h3>
<p>Monitora il progresso del tuo personaggio:</p>
<ul>
    <li>Livello complessivo</li>
    <li>Punti esperienza (XP)</li>
    <li>Punti abilità disponibili</li>
    <li>Statistiche derivate (come Punti Ferita, Armature, etc.)</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=3,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Inventario
            self.get_or_create_page(
                slug='inventario-oggetti',
                titolo='Inventario e Gestione Oggetti',
                contenuto='''
<h2>Gestione dell'Inventario</h2>

<h3>📦 Visualizzazione Inventario</h3>
<p>L'inventario mostra tutti gli oggetti in tuo possesso:</p>
<ul>
    <li>Organizzati per categoria</li>
    <li>Ricerca rapida per nome o tipo</li>
    <li>Filtri per rarità, tipo, stato</li>
    <li>Visualizzazione a griglia o lista</li>
</ul>

<h3>⚔️ Equipaggiamento</h3>
<p>Per equipaggiare un oggetto:</p>
<ol>
    <li>Vai alla sezione Inventario</li>
    <li>Clicca sull'oggetto che vuoi equipaggiare</li>
    <li>Seleziona "Equipaggia"</li>
    <li>L'oggetto verrà posizionato nello slot appropriato</li>
</ol>

<p><strong>Nota:</strong> Alcuni oggetti possono essere equipaggiati solo in slot specifici (arma principale, armatura, accessori, etc.)</p>

<h3>🔧 Utilizzo Oggetti</h3>
<p>Gli oggetti consumabili possono essere usati direttamente:</p>
<ul>
    <li>Pozioni e consumabili: clicca su "Usa"</li>
    <li>Oggetti speciali: possono avere azioni specifiche</li>
    <li>Alcuni oggetti possono essere combinati o assemblati</li>
</ul>

<h3>🏭 Forging e Creazione</h3>
<p>Alcuni oggetti possono essere creati o migliorati:</p>
<ul>
    <li>Accedi alla sezione "Forging" o "Creazione"</li>
    <li>Seleziona la ricetta desiderata</li>
    <li>Verifica di avere i materiali necessari</li>
    <li>Avvia la creazione (può richiedere tempo)</li>
</ul>

<h3>📋 Categorie di Oggetti</h3>
<ul>
    <li><strong>Armi</strong>: Spade, archi, fucili, etc.</li>
    <li><strong>Armature</strong>: Elmi, corazze, scudi</li>
    <li><strong>Accessori</strong>: Anelli, amuleti, cinture</li>
    <li><strong>Consumabili</strong>: Pozioni, cibo, materiali</li>
    <li><strong>Oggetti Speciali</strong>: Chiavi, documenti, artefatti</li>
</ul>

<h3>💼 Capacità Inventario</h3>
<p>L'inventario ha una capacità limitata. Gestisci lo spazio:</p>
<ul>
    <li>Vendi oggetti non necessari</li>
    <li>Deposita oggetti in magazzini (se disponibili)</li>
    <li>Usa oggetti consumabili quando possibile</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=4,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Messaggi
            self.get_or_create_page(
                slug='messaggi-comunicazione',
                titolo='Messaggi e Comunicazione',
                contenuto='''
<h2>Sistema di Messaggistica</h2>

<h3>💬 Messaggi Privati</h3>
<p>Per inviare un messaggio privato:</p>
<ol>
    <li>Vai alla sezione "Messaggi"</li>
    <li>Clicca su "Nuovo Messaggio" o "Componi"</li>
    <li>Seleziona il destinatario</li>
    <li>Scrivi il tuo messaggio</li>
    <li>Invia</li>
</ol>

<h3>👥 Conversazioni di Gruppo</h3>
<p>Partecipa a conversazioni con più giocatori:</p>
<ul>
    <li>Visualizza tutte le conversazioni attive</li>
    <li>Crea una nuova conversazione di gruppo</li>
    <li>Invita altri giocatori</li>
    <li>Gestisci le notifiche per ogni conversazione</li>
</ul>

<h3>🔔 Notifiche</h3>
<p>Ricevi notifiche per:</p>
<ul>
    <li>Nuovi messaggi</li>
    <li>Risposte alle tue conversazioni</li>
    <li>Menzioni nei messaggi</li>
    <li>Eventi importanti del gioco</li>
</ul>

<p>Puoi configurare le notifiche nelle impostazioni del profilo.</p>

<h3>📨 Messaggi Staff</h3>
<p>Lo staff può inviare messaggi importanti a tutti i giocatori:</p>
<ul>
    <li>Annunci di eventi</li>
    <li>Aggiornamenti del sistema</li>
    <li>Avvisi importanti</li>
</ul>

<p>Questi messaggi sono evidenziati e non possono essere eliminati.</p>

<h3>🔍 Ricerca Messaggi</h3>
<p>Trova rapidamente messaggi specifici:</p>
<ul>
    <li>Cerca per mittente</li>
    <li>Cerca per contenuto</li>
    <li>Filtra per data</li>
    <li>Organizza per conversazione</li>
</ul>

<h3>⚙️ Impostazioni Messaggi</h3>
<p>Personalizza la tua esperienza:</p>
<ul>
    <li>Notifiche email (opzionale)</li>
    <li>Suoni di notifica</li>
    <li>Auto-archiviazione messaggi vecchi</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=5,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Quest
            self.get_or_create_page(
                slug='quest-missioni',
                titolo='Quest e Missioni',
                contenuto='''
<h2>Sistema Quest e Missioni</h2>

<h3>📜 Visualizzazione Quest</h3>
<p>Nella sezione Quest puoi vedere:</p>
<ul>
    <li><strong>Quest Disponibili</strong>: Missioni che puoi iniziare</li>
    <li><strong>Quest Attive</strong>: Missioni in corso</li>
    <li><strong>Quest Completate</strong>: Storia delle tue avventure</li>
    <li><strong>Quest Fallite</strong>: Missioni non completate</li>
</ul>

<h3>🎯 Accettare una Quest</h3>
<p>Per iniziare una nuova quest:</p>
<ol>
    <li>Vai alla sezione "Quest"</li>
    <li>Sfoglia le quest disponibili</li>
    <li>Leggi la descrizione e i requisiti</li>
    <li>Verifica di soddisfare i prerequisiti</li>
    <li>Clicca su "Accetta Quest"</li>
</ol>

<h3>✅ Completare Obiettivi</h3>
<p>Ogni quest ha obiettivi specifici da completare:</p>
<ul>
    <li>Visualizza gli obiettivi nella pagina della quest</li>
    <li>Segui le istruzioni per completarli</li>
    <li>Alcuni obiettivi si completano automaticamente</li>
    <li>Altri richiedono azioni specifiche del giocatore</li>
</ul>

<h3>🏆 Ricompense</h3>
<p>Completando le quest riceverai:</p>
<ul>
    <li>Punti esperienza (XP)</li>
    <li>Oggetti e ricompense</li>
    <li>Denaro o risorse</li>
    <li>Accesso a nuove aree o abilità</li>
</ul>

<h3>⏱️ Quest Temporali</h3>
<p>Alcune quest hanno scadenze:</p>
<ul>
    <li>Verifica la data di scadenza</li>
    <li>Pianifica il tuo tempo di conseguimento</li>
    <li>Le quest scadute possono diventare non disponibili</li>
</ul>

<h3>👥 Quest di Gruppo</h3>
<p>Alcune quest possono essere completate in gruppo:</p>
<ul>
    <li>Invita altri giocatori</li>
    <li>Coordina le azioni</li>
    <li>Condividi le ricompense</li>
</ul>

<h3>📊 Tracciamento Progresso</h3>
<p>Monitora il tuo progresso:</p>
<ul>
    <li>Percentuale di completamento</li>
    <li>Obiettivi rimanenti</li>
    <li>Tempo stimato per il completamento</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=6,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Amministrazione (solo staff)
            self.get_or_create_page(
                slug='amministrazione',
                titolo='Area Amministrazione (Staff)',
                contenuto='''
<h2>Guida per lo Staff</h2>

<p><strong>Questa sezione è visibile solo ai membri dello staff.</strong></p>

<h3>👨‍💼 Dashboard Staff</h3>
<p>L'area amministrazione fornisce strumenti per:</p>
<ul>
    <li>Gestione giocatori e personaggi</li>
    <li>Creazione e modifica di quest</li>
    <li>Gestione eventi</li>
    <li>Monitoraggio del sistema</li>
    <li>Gestione contenuti wiki</li>
</ul>

<h3>📝 Gestione Contenuti</h3>
<p>Come staff puoi:</p>
<ul>
    <li><strong>Creare pagine wiki</strong>: Aggiungi nuove pagine al regolamento</li>
    <li><strong>Modificare contenuti</strong>: Aggiorna pagine esistenti</li>
    <li><strong>Gestire immagini</strong>: Carica immagini per le pagine wiki</li>
    <li><strong>Organizzare menu</strong>: Struttura gerarchica delle pagine</li>
</ul>

<h3>🎮 Gestione Eventi</h3>
<p>Crea e gestisci eventi:</p>
<ul>
    <li>Definisci date e orari</li>
    <li>Assegna staff responsabili</li>
    <li>Collega quest e missioni</li>
    <li>Gestisci partecipanti</li>
</ul>

<h3>⚙️ Strumenti Amministrativi</h3>
<p>Accesso a funzionalità avanzate:</p>
<ul>
    <li>Log di sistema</li>
    <li>Statistiche di utilizzo</li>
    <li>Gestione utenti</li>
    <li>Configurazioni avanzate</li>
</ul>

<h3>🔐 Permessi</h3>
<p>I permessi staff includono:</p>
<ul>
    <li>Accesso a tutte le aree pubbliche</li>
    <li>Modifica contenuti wiki</li>
    <li>Gestione eventi e quest</li>
    <li>Visualizzazione dati giocatori (rispettando la privacy)</li>
</ul>

<p><strong>Nota:</strong> Usa i poteri da staff responsabilmente e rispetta sempre la privacy dei giocatori.</p>
                ''',
                parent=pagina_istruzioni,
                ordine=7,
                public=True,
                visibile_solo_staff=True,
                force=force
            )

            # ========== PAGINE SPECIFICHE PER TAB ==========
            
            # Pagina: Inventario (per tab inventario)
            self.get_or_create_page(
                slug='inventario',
                titolo='Inventario e Zaino',
                contenuto='''
<h2>Gestione dell'Inventario</h2>
<p>La sezione <strong>Zaino</strong> ti permette di gestire tutti gli oggetti in tuo possesso.</p>

<h3>📦 Visualizzazione</h3>
<p>Nell'inventario puoi vedere:</p>
<ul>
    <li>Tutti gli oggetti posseduti, organizzati per categoria</li>
    <li>Ricerca rapida per nome o tipo</li>
    <li>Filtri per rarità, tipo, stato</li>
    <li>Visualizzazione a griglia o lista</li>
</ul>

<h3>⚔️ Equipaggiamento</h3>
<p>Per equipaggiare un oggetto:</p>
<ol>
    <li>Clicca sull'oggetto che vuoi equipaggiare</li>
    <li>Seleziona "Equipaggia"</li>
    <li>L'oggetto verrà posizionato nello slot appropriato</li>
</ol>
<p><strong>Nota:</strong> Alcuni oggetti possono essere equipaggiati solo in slot specifici (arma principale, armatura, accessori, etc.)</p>

<h3>🔧 Utilizzo Oggetti</h3>
<p>Gli oggetti consumabili possono essere usati direttamente:</p>
<ul>
    <li>Pozioni e consumabili: clicca su "Usa"</li>
    <li>Oggetti speciali: possono avere azioni specifiche</li>
    <li>Alcuni oggetti possono essere combinati o assemblati</li>
</ul>

<h3>📋 Categorie</h3>
<ul>
    <li><strong>Armi</strong>: Spade, archi, fucili, etc.</li>
    <li><strong>Armature</strong>: Elmi, corazze, scudi</li>
    <li><strong>Accessori</strong>: Anelli, amuleti, cinture</li>
    <li><strong>Consumabili</strong>: Pozioni, cibo, materiali</li>
    <li><strong>Oggetti Speciali</strong>: Chiavi, documenti, artefatti</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=10,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Abilità (per tab abilita)
            self.get_or_create_page(
                slug='abilita',
                titolo='Abilità e Competenze',
                contenuto='''
<h2>Gestione delle Abilità</h2>
<p>La sezione <strong>Abilità</strong> ti permette di visualizzare e gestire tutte le competenze del tuo personaggio.</p>

<h3>📊 Visualizzazione Abilità</h3>
<p>Puoi vedere:</p>
<ul>
    <li>Tutte le abilità disponibili organizzate per categoria</li>
    <li>Il tuo livello di competenza in ciascuna abilità</li>
    <li>Descrizioni dettagliate di ogni abilità</li>
    <li>Requisiti per sbloccare nuove abilità</li>
</ul>

<h3>📈 Miglioramento Abilità</h3>
<p>Per migliorare un'abilità:</p>
<ol>
    <li>Vai alla sezione Abilità</li>
    <li>Seleziona l'abilità che vuoi migliorare</li>
    <li>Verifica di avere i punti esperienza necessari</li>
    <li>Usa i punti per aumentare il livello</li>
</ol>

<h3>🎯 Tipi di Abilità</h3>
<ul>
    <li><strong>Abilità di Combattimento</strong>: Tecniche di attacco e difesa</li>
    <li><strong>Abilità Sociali</strong>: Persuasione, negoziazione, leadership</li>
    <li><strong>Abilità Tecniche</strong>: Hacking, riparazione, crafting</li>
    <li><strong>Abilità Magiche</strong>: Incantesimi e rituali</li>
    <li><strong>Abilità Speciali</strong>: Competenze uniche del personaggio</li>
</ul>

<h3>🔓 Sbloccare Nuove Abilità</h3>
<p>Alcune abilità possono essere sbloccate:</p>
<ul>
    <li>Completando quest specifiche</li>
    <li>Partecipando a eventi</li>
    <li>Raggiungendo determinati livelli</li>
    <li>Incontrando requisiti speciali</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=11,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Tessiture (per tab tessiture)
            self.get_or_create_page(
                slug='tessiture',
                titolo='Tessiture',
                contenuto='''
<h2>Gestione delle Tessiture</h2>
<p>La sezione <strong>Tessiture</strong> mostra le modifiche permanenti applicate al corpo del tuo personaggio.</p>

<h3>🧬 Cosa sono le Tessiture</h3>
<p>Le tessiture sono modifiche permanenti al corpo del personaggio:</p>
<ul>
    <li>Modifiche biologiche o tecnologiche</li>
    <li>Effetti permanenti (positivi o negativi)</li>
    <li>Non possono essere rimosse facilmente</li>
    <li>Possono influenzare statistiche e capacità</li>
</ul>

<h3>📋 Visualizzazione</h3>
<p>Nella sezione Tessiture puoi vedere:</p>
<ul>
    <li>Tutte le tessiture attualmente installate</li>
    <li>Effetti e modificatori applicati</li>
    <li>Slot corporei utilizzati</li>
    <li>Descrizioni dettagliate di ogni tessitura</li>
</ul>

<h3>⚙️ Installazione Tessiture</h3>
<p>Le tessiture possono essere installate:</p>
<ul>
    <li>Tramite procedure speciali durante eventi</li>
    <li>Presso strutture mediche o tecnologiche</li>
    <li>Come ricompensa per quest specifiche</li>
    <li>Richiedono spesso materiali o risorse speciali</li>
</ul>

<h3>⚠️ Considerazioni</h3>
<p>Prima di installare una tessitura:</p>
<ul>
    <li>Leggi attentamente gli effetti</li>
    <li>Verifica i requisiti e gli slot disponibili</li>
    <li>Considera gli effetti collaterali</li>
    <li>Alcune tessiture possono essere incompatibili tra loro</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=12,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Infusioni (per tab infusioni)
            self.get_or_create_page(
                slug='infusioni',
                titolo='Infusioni',
                contenuto='''
<h2>Gestione delle Infusioni</h2>
<p>La sezione <strong>Infusioni</strong> ti permette di gestire i potenziamenti temporanei del tuo personaggio.</p>

<h3>✨ Cosa sono le Infusioni</h3>
<p>Le infusioni sono potenziamenti che possono essere applicati al personaggio:</p>
<ul>
    <li>Effetti temporanei o semi-permanenti</li>
    <li>Bonus a statistiche o capacità</li>
    <li>Possono essere rimosse o sostituite</li>
    <li>Richiedono slot di infusione disponibili</li>
</ul>

<h3>📊 Visualizzazione</h3>
<p>Nella sezione Infusioni puoi vedere:</p>
<ul>
    <li>Infusioni attualmente attive</li>
    <li>Effetti e modificatori applicati</li>
    <li>Durata rimanente (se temporanee)</li>
    <li>Slot utilizzati e disponibili</li>
</ul>

<h3>🔬 Applicare Infusioni</h3>
<p>Per applicare un'infusione:</p>
<ol>
    <li>Vai alla sezione Infusioni</li>
    <li>Seleziona l'infusione che vuoi applicare</li>
    <li>Verifica di avere slot disponibili</li>
    <li>Conferma l'applicazione</li>
</ol>

<h3>⚠️ Effetti Collaterali</h3>
<p>Alcune infusioni possono avere:</p>
<ul>
    <li>Effetti collaterali negativi</li>
    <li>Incompatibilità con altre infusioni</li>
    <li>Requisiti specifici per l'applicazione</li>
    <li>Durata limitata</li>
</ul>

<h3>🔄 Rimozione</h3>
<p>Le infusioni possono essere rimosse:</p>
<ul>
    <li>Manualmente dalla sezione Infusioni</li>
    <li>Automaticamente alla scadenza (se temporanee)</li>
    <li>Tramite procedure speciali</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=13,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Cerimoniali (per tab cerimoniali)
            self.get_or_create_page(
                slug='cerimoniali',
                titolo='Cerimoniali',
                contenuto='''
<h2>Gestione dei Cerimoniali</h2>
<p>La sezione <strong>Cerimoniali</strong> ti permette di visualizzare e utilizzare riti e rituali disponibili.</p>

<h3>🕯️ Cosa sono i Cerimoniali</h3>
<p>I cerimoniali sono riti e rituali che il tuo personaggio può eseguire:</p>
<ul>
    <li>Riti magici o spirituali</li>
    <li>Cerimonie di gruppo</li>
    <li>Rituali con effetti specifici</li>
    <li>Possono richiedere materiali o partecipanti</li>
</ul>

<h3>📜 Visualizzazione</h3>
<p>Nella sezione Cerimoniali puoi vedere:</p>
<ul>
    <li>Tutti i cerimoniali disponibili</li>
    <li>Requisiti per l'esecuzione</li>
    <li>Effetti e risultati attesi</li>
    <li>Materiali necessari</li>
</ul>

<h3>🎭 Eseguire un Cerimoniale</h3>
<p>Per eseguire un cerimoniale:</p>
<ol>
    <li>Vai alla sezione Cerimoniali</li>
    <li>Seleziona il cerimoniale desiderato</li>
    <li>Verifica di soddisfare tutti i requisiti</li>
    <li>Assicurati di avere i materiali necessari</li>
    <li>Esegui il cerimoniale</li>
</ol>

<h3>👥 Cerimoniali di Gruppo</h3>
<p>Alcuni cerimoniali richiedono più partecipanti:</p>
<ul>
    <li>Invita altri giocatori a partecipare</li>
    <li>Coordina le posizioni e i ruoli</li>
    <li>Assicurati che tutti soddisfino i requisiti</li>
</ul>

<h3>⚡ Effetti</h3>
<p>I cerimoniali possono avere vari effetti:</p>
<ul>
    <li>Bonus temporanei o permanenti</li>
    <li>Trasformazioni o modifiche</li>
    <li>Creazione di oggetti o risorse</li>
    <li>Eventi narrativi speciali</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=14,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Messaggi (per tab messaggi - versione specifica)
            self.get_or_create_page(
                slug='messaggi',
                titolo='Messaggi',
                contenuto='''
<h2>Sistema di Messaggistica</h2>
<p>La sezione <strong>Messaggi</strong> ti permette di comunicare con altri giocatori.</p>

<h3>💬 Messaggi Privati</h3>
<p>Per inviare un messaggio privato:</p>
<ol>
    <li>Clicca su "Nuovo Messaggio" o "Componi"</li>
    <li>Seleziona il destinatario</li>
    <li>Scrivi il tuo messaggio</li>
    <li>Invia</li>
</ol>

<h3>👥 Conversazioni di Gruppo</h3>
<p>Partecipa a conversazioni con più giocatori:</p>
<ul>
    <li>Visualizza tutte le conversazioni attive</li>
    <li>Crea una nuova conversazione di gruppo</li>
    <li>Invita altri giocatori</li>
    <li>Gestisci le notifiche per ogni conversazione</li>
</ul>

<h3>🔔 Notifiche</h3>
<p>Ricevi notifiche per:</p>
<ul>
    <li>Nuovi messaggi</li>
    <li>Risposte alle tue conversazioni</li>
    <li>Menzioni nei messaggi</li>
</ul>

<h3>📨 Messaggi Staff</h3>
<p>Lo staff può inviare messaggi importanti a tutti i giocatori. Questi messaggi sono evidenziati e non possono essere eliminati.</p>
                ''',
                parent=pagina_istruzioni,
                ordine=15,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Scanner QR (per tab qr)
            self.get_or_create_page(
                slug='scanner-qr',
                titolo='Scanner QR',
                contenuto='''
<h2>Utilizzo dello Scanner QR</h2>
<p>La sezione <strong>Scanner</strong> ti permette di scansionare codici QR per interagire con oggetti e luoghi nel gioco.</p>

<h3>📱 Come Scansionare</h3>
<p>Per scansionare un codice QR:</p>
<ol>
    <li>Apri la sezione Scanner</li>
    <li>Permetti l'accesso alla fotocamera del dispositivo</li>
    <li>Inquadra il codice QR</li>
    <li>Attendi la lettura automatica</li>
</ol>

<h3>🎯 Cosa Puoi Scansionare</h3>
<p>Puoi scansionare:</p>
<ul>
    <li>Codici QR su oggetti fisici</li>
    <li>QR code durante eventi</li>
    <li>Codici per interagire con luoghi</li>
    <li>Codici per ottenere ricompense</li>
</ul>

<h3>⚡ Azioni Disponibili</h3>
<p>Dopo la scansione potresti:</p>
<ul>
    <li>Ottenere oggetti o ricompense</li>
    <li>Accedere a contenuti speciali</li>
    <li>Interagire con elementi del gioco</li>
    <li>Completare obiettivi di quest</li>
</ul>

<h3>⏱️ Cooldown</h3>
<p>Alcune azioni hanno un periodo di attesa (cooldown) tra una scansione e l'altra. Attendi il tempo indicato prima di scansionare nuovamente.</p>

<h3>🔒 Permessi Fotocamera</h3>
<p>Assicurati di aver concesso i permessi per la fotocamera nel browser. Su mobile potrebbe essere necessario abilitare l'accesso nelle impostazioni del dispositivo.</p>
                ''',
                parent=pagina_istruzioni,
                ordine=16,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Diario (per tab logs)
            self.get_or_create_page(
                slug='diario',
                titolo='Diario',
                contenuto='''
<h2>Il Diario del Personaggio</h2>
<p>La sezione <strong>Diario</strong> contiene un log completo di tutte le azioni e gli eventi del tuo personaggio.</p>

<h3>📖 Cosa Contiene</h3>
<p>Il diario registra:</p>
<ul>
    <li>Tutte le azioni eseguite</li>
    <li>Eventi e interazioni</li>
    <li>Modifiche a statistiche e oggetti</li>
    <li>Completamento di obiettivi</li>
    <li>Messaggi e comunicazioni importanti</li>
</ul>

<h3>🔍 Navigazione</h3>
<p>Puoi navigare il diario:</p>
<ul>
    <li>Scorri cronologicamente</li>
    <li>Cerca per parola chiave</li>
    <li>Filtra per tipo di evento</li>
    <li>Visualizza eventi recenti o passati</li>
</ul>

<h3>📅 Organizzazione</h3>
<p>Gli eventi sono organizzati:</p>
<ul>
    <li>Per data e ora</li>
    <li>Per categoria (azioni, eventi, modifiche)</li>
    <li>Per importanza</li>
</ul>

<h3>💾 Storico</h3>
<p>Il diario mantiene uno storico completo delle tue attività, utile per:</p>
<ul>
    <li>Rivedere eventi passati</li>
    <li>Verificare modifiche e cambiamenti</li>
    <li>Tracciare il progresso del personaggio</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=17,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Transazioni (per tab transazioni)
            self.get_or_create_page(
                slug='transazioni',
                titolo='Transazioni',
                contenuto='''
<h2>Gestione delle Transazioni</h2>
<p>La sezione <strong>Transazioni</strong> ti permette di visualizzare e gestire tutti gli scambi e i trasferimenti di oggetti.</p>

<h3>📋 Cosa Sono le Transazioni</h3>
<p>Le transazioni includono:</p>
<ul>
    <li>Scambi di oggetti tra giocatori</li>
    <li>Trasferimenti tra inventari</li>
    <li>Acquisti e vendite</li>
    <li>Regali e donazioni</li>
</ul>

<h3>📊 Visualizzazione</h3>
<p>Puoi vedere:</p>
<ul>
    <li>Tutte le transazioni effettuate</li>
    <li>Transazioni in attesa di conferma</li>
    <li>Storico completo</li>
    <li>Dettagli di ogni transazione</li>
</ul>

<h3>🔄 Processo di Transazione</h3>
<p>Per effettuare una transazione:</p>
<ol>
    <li>Seleziona l'oggetto da trasferire</li>
    <li>Scegli il destinatario</li>
    <li>Conferma la transazione</li>
    <li>Attendi la conferma del destinatario (se richiesta)</li>
</ol>

<h3>✅ Conferma</h3>
<p>Alcune transazioni richiedono conferma:</p>
<ul>
    <li>Il destinatario deve accettare</li>
    <li>Puoi annullare prima della conferma</li>
    <li>Le transazioni confermate sono irreversibili</li>
</ul>

<h3>📝 Storico</h3>
<p>Mantieni traccia di:</p>
<ul>
    <li>Oggetti ricevuti</li>
    <li>Oggetti inviati</li>
    <li>Data e ora delle transazioni</li>
    <li>Stato (completata, in attesa, annullata)</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=18,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Pagina: Scommesse (tab scommesse)
            self.get_or_create_page(
                slug='scommesse',
                titolo='Scommesse in-game',
                contenuto='''
<h2>Scommesse sportive in-game</h2>
<p>La sezione <strong>Scommesse</strong> ti permette di pronosticare gli esiti di tornei e competizioni organizzati dallo staff durante l'evento live. Le puntate usano i <strong>Crediti (CR)</strong> del personaggio.</p>

<h3>📅 Calendari e eventi</h3>
<p>Per ogni sport attivo lo staff pubblica un <strong>calendario</strong> con una serie di incontri (squadra casa vs squadra trasferta). Su ogni incontro puoi scommettere su:</p>
<ul>
    <li><strong>1</strong> — vittoria della squadra di casa</li>
    <li><strong>X</strong> — pareggio</li>
    <li><strong>2</strong> — vittoria della squadra ospite</li>
</ul>
<p>Accanto a ogni esito vedi la <strong>quota</strong> (moltiplicatore): se indovini, la vincita è <em>importo puntato × quota</em>.</p>

<h3>🎯 Scommessa singola e combinata</h3>
<ul>
    <li><strong>Singola</strong>: un solo incontro</li>
    <li><strong>Combinata</strong>: più incontri nello stesso calendario; le quote si moltiplicano, ma devi indovinare <em>tutti</em> gli esiti per vincere</li>
</ul>
<p>Il numero massimo di eventi in combinata è configurabile dallo staff (di default fino a 8).</p>

<h3>⏱️ Tempistiche</h3>
<ul>
    <li>Le scommesse sono aperte dalla <strong>data di apertura</strong> fino alla <strong>data di risoluzione</strong> del calendario</li>
    <li>I risultati sono calcolati al momento della creazione del calendario, ma restano <strong>nascosti</strong> fino alla data di risoluzione</li>
    <li>Dopo la pubblicazione, il calendario resta consultabile per circa <strong>24 ore</strong> (poi scompare dall'elenco)</li>
</ul>

<h3>💰 Limiti di puntata</h3>
<p>Senza codice speciale, l'importo massimo per singola scommessa è limitato (di default <strong>15 CR</strong>, salvo diversa impostazione sul calendario).</p>
<p>Con un <strong>codice allibratore</strong> valido non ci sono limiti di importo e ricevi quote più favorevoli.</p>

<h3>🔑 Allibratore e codici (statistica ALL)</h3>
<p>Se il tuo personaggio possiede la statistica <strong>Allibratore (sigla ALL &gt; 0)</strong> puoi:</p>
<ul>
    <li>Generare codici alfanumerici da <strong>5 caratteri</strong> (monouso, una scommessa ciascuno)</li>
    <li>Condividere un codice con un altro giocatore che lo inserisce al momento della puntata</li>
    <li>Ricevere una <strong>commissione</strong> sull'importo puntato (di default 8%)</li>
</ul>
<p>Quote più favorevoli: più alto è il valore ALL, minore è il margine del bookmaker applicato alla scommessa con codice.</p>

<h3>📋 Le mie scommesse</h3>
<p>Nella stessa tab trovi l'elenco delle puntate effettuate e l'esito (in attesa, vinta, persa) dopo la risoluzione del calendario.</p>

<h3>⚠️ Note importanti</h3>
<ul>
    <li>I crediti puntati vengono scalati subito; le vincite vengono accreditate alla risoluzione</li>
    <li>Un codice usato non può essere riutilizzato</li>
    <li>Le quote tengono conto della potenza delle squadre con una piccola variabilità casuale (±10%)</li>
    <li>Dopo ogni incontro risolto, la potenza delle squadre si aggiorna in modo <strong>proporzionale</strong>: se vince il favorito la variazione è piccola; se vince lo sfavorito (sorpresa) la variazione è più marcata. In pareggio nessun cambiamento.</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=19,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('✓ Generazione completata con successo!'))
        self.stdout.write('=' * 60)
        self.stdout.write(f'\n📄 Pagine create/aggiornate: 17 (1 parent + 8 generali + 8 specifiche tab)')
        self.stdout.write(f'👤 Utente di sistema: {username}')
        if password:
            self.stdout.write(self.style.WARNING(f'\n⚠️  Password utente sistema: {password}'))
            self.stdout.write(self.style.WARNING('⚠️  Salva questa password in un luogo sicuro!'))
        self.stdout.write('\n🌐 Le pagine sono ora disponibili su:')
        self.stdout.write('   - https://app.kor35.it/regolamento/guida-utilizzo-app')
        self.stdout.write('   - https://www.kor35.it/admin (per lo staff)')
        self.stdout.write('\n')
