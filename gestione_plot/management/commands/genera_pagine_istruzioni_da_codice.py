"""
Management command per generare pagine di istruzione basate sull'analisi del codice reale.

Questo script analizza i componenti React e i modelli Django per generare istruzioni accurate.

Uso:
    python manage.py genera_pagine_istruzioni_da_codice
    python manage.py genera_pagine_istruzioni_da_codice --force
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from gestione_plot.models import PaginaRegolamento
import os
import re

User = get_user_model()


class Command(BaseCommand):
    help = 'Genera pagine di istruzione basate sull\'analisi del codice reale'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Sovrascrive le pagine esistenti con lo stesso slug',
        )

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

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Generazione Pagine Istruzioni (da Codice)'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        with transaction.atomic():
            # Pagina parent: Istruzioni
            pagina_istruzioni = self.get_or_create_page(
                slug='istruzioni',
                titolo='Istruzioni',
                contenuto='''
<h2>Istruzioni per l'utilizzo dell'App Kor35</h2>
<p>Benvenuto nella sezione istruzioni! Qui troverai tutte le guide per utilizzare al meglio l'applicazione.</p>
                ''',
                ordine=1,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # ========== PAGINA: INVENTARIO (basata su InventoryTab.jsx) ==========
            self.get_or_create_page(
                slug='inventario',
                titolo='Inventario e Zaino',
                contenuto='''
<h2>Gestione dell'Inventario</h2>
<p>La sezione <strong>Zaino</strong> ti permette di gestire tutti gli oggetti in tuo possesso e il loro equipaggiamento sul corpo del personaggio.</p>

<h3>📦 Visualizzazione Inventario</h3>
<p>L'inventario mostra:</p>
<ul>
    <li>Tutti gli oggetti posseduti, organizzati per categoria</li>
    <li>Ricerca e filtri per trovare rapidamente gli oggetti</li>
    <li>Visualizzazione a lista con dettagli</li>
</ul>

<h3>👤 Equipaggiamento sul Corpo</h3>
<p>Il corpo del personaggio ha <strong>8 slot corporei</strong> dove puoi equipaggiare oggetti:</p>
<ul>
    <li><strong>HD1</strong> - Testa 1 (Cranio/Cervello/Occhi)</li>
    <li><strong>HD2</strong> - Testa 2 (Volto/Orecchie)</li>
    <li><strong>TR1</strong> - Tronco 1 (Torace/Cuore/Polmoni)</li>
    <li><strong>TR2</strong> - Tronco 2 (Addome/Spina Dorsale/Pelle)</li>
    <li><strong>RA</strong> - Braccio Destro</li>
    <li><strong>LA</strong> - Braccio Sinistro</li>
    <li><strong>RL</strong> - Gamba Destra</li>
    <li><strong>LL</strong> - Gamba Sinistra</li>
</ul>

<h3>⚔️ Tipi di Oggetti</h3>
<p>Gli oggetti possono essere di diversi tipi:</p>
<ul>
    <li><strong>FIS</strong> - Oggetto Fisico (armi, armature, etc.)</li>
    <li><strong>MAT</strong> - Materia (Mondana)</li>
    <li><strong>MOD</strong> - Mod (Tecnologica) - sempre visibile anche se scarico</li>
    <li><strong>INN</strong> - Innesto (Tecnologico) - sempre visibile anche se scarico</li>
    <li><strong>MUT</strong> - Mutazione (Innata)</li>
    <li><strong>AUM</strong> - Aumento (installazione corporea)</li>
    <li><strong>POT</strong> - Potenziamento (installazione su oggetti)</li>
</ul>

<h3>🔋 Cariche e Ricariche</h3>
<p>Alcuni oggetti hanno un sistema di cariche:</p>
<ul>
    <li>Visualizza le <strong>cariche attuali</strong> di ogni oggetto</li>
    <li>Gli oggetti con cariche > 0 sono mostrati come "attivi"</li>
    <li>Puoi ricaricare oggetti quando necessario</li>
    <li>MOD e INN sono sempre visibili anche se scarichi</li>
</ul>

<h3>🛒 Shop</h3>
<p>Puoi acquistare oggetti direttamente dall'inventario tramite lo shop.</p>

<h3>🔧 Assembly</h3>
<p>Alcuni oggetti possono essere assemblati o combinati per creare nuovi oggetti.</p>

<h3>✨ Aura degli Oggetti</h3>
<p>Gli oggetti possono avere un'aura associata, che determina il colore di visualizzazione nello slot corporeo.</p>
                ''',
                parent=pagina_istruzioni,
                ordine=10,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # ========== PAGINA: ABILITÀ (basata su AbilitaTab.jsx) ==========
            self.get_or_create_page(
                slug='abilita',
                titolo='Abilità e Competenze',
                contenuto='''
<h2>Gestione delle Abilità</h2>
<p>La sezione <strong>Abilità</strong> ti permette di visualizzare e acquisire nuove competenze per il tuo personaggio.</p>

<h3>📊 Visualizzazione</h3>
<p>Le abilità sono organizzate per gruppi (tier) e mostrano:</p>
<ul>
    <li>Abilità già possedute dal personaggio</li>
    <li>Abilità acquistabili disponibili</li>
    <li>Dettagli di ogni abilità (descrizione, requisiti, effetti)</li>
</ul>

<h3>💰 Costi di Acquisizione</h3>
<p>Le abilità possono costare:</p>
<ul>
    <li><strong>Punti Caratteristica (PC)</strong> - calcolati dinamicamente (costo_pc_calc)</li>
    <li><strong>Crediti</strong> - calcolati dinamicamente (costo_crediti_calc)</li>
    <li>Alcune abilità possono richiedere entrambi</li>
</ul>

<h3>🎯 Acquisire un'Abilità</h3>
<p>Per acquisire una nuova abilità:</p>
<ol>
    <li>Vai alla sezione Abilità</li>
    <li>Trova l'abilità che vuoi acquisire nella lista "Acquistabili"</li>
    <li>Clicca sul pulsante di acquisto</li>
    <li>Conferma l'acquisto (verrà mostrato il costo in PC e/o Crediti)</li>
    <li>L'abilità verrà aggiunta alle tue abilità possedute</li>
</ol>

<h3>✨ Tratti Speciali e Aure</h3>
<p>Alcune abilità sono marcate come <strong>tratti speciali</strong> (is_tratto_aura):</p>
<ul>
    <li>Questi non appaiono nella lista acquistabili standard</li>
    <li>Vengono gestiti tramite il sistema di Punteggi/Aure</li>
    <li>Visualizzati nella sezione Home/Scheda del personaggio</li>
</ul>

<h3>📈 Tier e Gruppi</h3>
<p>Le abilità sono organizzate in tier/gruppi che determinano:</p>
<ul>
    <li>L'organizzazione visiva</li>
    <li>Possibili prerequisiti</li>
    <li>Requisiti per lo sblocco</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=11,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # ========== PAGINA: INFUSIONI (basata su InfusioniTab.jsx) ==========
            self.get_or_create_page(
                slug='infusioni',
                titolo='Infusioni',
                contenuto='''
<h2>Gestione delle Infusioni</h2>
<p>La sezione <strong>Infusioni</strong> ti permette di gestire le infusioni possedute e apprendere nuove infusioni.</p>

<h3>📊 Visualizzazione</h3>
<p>Le infusioni sono organizzate in:</p>
<ul>
    <li><strong>Possedute</strong> - Infusioni già apprese dal personaggio</li>
    <li><strong>Acquistabili</strong> - Infusioni disponibili per l'apprendimento</li>
</ul>

<h3>📚 Apprendere un'Infusione</h3>
<p>Per apprendere una nuova infusione:</p>
<ol>
    <li>Vai alla sezione Infusioni</li>
    <li>Trova l'infusione nella lista "Acquistabili"</li>
    <li>Clicca sul pulsante di apprendimento</li>
    <li>Conferma il costo (in Crediti)</li>
    <li>L'infusione verrà aggiunta alle tue infusioni possedute</li>
</ol>

<h3>💰 Costi</h3>
<p>Le infusioni hanno un costo che può essere:</p>
<ul>
    <li><strong>Costo effettivo</strong> - se specificato (costo_effettivo)</li>
    <li><strong>Costo calcolato</strong> - basato sul livello (livello × 100 crediti)</li>
    <li>Il sistema usa il costo effettivo se disponibile, altrimenti calcola automaticamente</li>
</ul>

<h3>🔨 Forgiatura</h3>
<p>Le infusioni possono essere forgiate per creare oggetti:</p>
<ul>
    <li>Clicca sul pulsante "Forgia" su un'infusione posseduta</li>
    <li>Si aprirà una modale per scegliere il metodo di forgiatura</li>
    <li>Puoi scegliere tra diversi metodi (se disponibili)</li>
    <li>La forgiatura viene aggiunta alla coda e richiede tempo</li>
</ul>

<h3>⏱️ Coda di Forgiatura</h3>
<p>Le forgiatura in corso vengono mostrate in una coda:</p>
<ul>
    <li>Visualizza tutte le forgiatura attive</li>
    <li>Mostra il tempo rimanente</li>
    <li>Aggiornamento automatico dello stato</li>
</ul>

<h3>📝 Proposte</h3>
<p>Puoi creare proposte per nuove infusioni:</p>
<ul>
    <li>Accedi al sistema di proposte</li>
    <li>Crea una nuova proposta di infusione</li>
    <li>Lo staff valuterà la proposta</li>
</ul>

<h3>📈 Livelli</h3>
<p>Le infusioni hanno un livello che determina:</p>
<ul>
    <li>Il costo di apprendimento</li>
    <li>La potenza degli effetti</li>
    <li>Possibili prerequisiti</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=13,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # ========== PAGINA: TESSITURE (basata su TessitureTab.jsx) ==========
            self.get_or_create_page(
                slug='tessiture',
                titolo='Tessiture',
                contenuto='''
<h2>Gestione delle Tessiture</h2>
<p>La sezione <strong>Tessiture</strong> ti permette di gestire le tessiture possedute e acquisire nuove tessiture.</p>

<h3>📊 Visualizzazione</h3>
<p>Le tessiture sono organizzate in:</p>
<ul>
    <li><strong>Possedute</strong> - Tessiture già acquisite dal personaggio</li>
    <li><strong>Acquistabili</strong> - Tessiture disponibili per l'acquisizione</li>
</ul>

<h3>🎯 Acquisire una Tessitura</h3>
<p>Per acquisire una nuova tessitura:</p>
<ol>
    <li>Vai alla sezione Tessiture</li>
    <li>Trova la tessitura nella lista "Acquistabili"</li>
    <li>Clicca sul pulsante di acquisizione</li>
    <li>Conferma il costo (in Crediti)</li>
    <li>La tessitura verrà aggiunta alle tue tessiture possedute</li>
</ol>

<h3>💰 Costi</h3>
<p>Le tessiture hanno un costo che può essere:</p>
<ul>
    <li><strong>Costo effettivo</strong> - se specificato (costo_effettivo)</li>
    <li><strong>Costo calcolato</strong> - basato sul livello (livello × 100 crediti)</li>
</ul>

<h3>✨ Aura Richiesta</h3>
<p>Le tessiture possono richiedere un'aura specifica:</p>
<ul>
    <li>Ogni tessitura può avere un'aura_richiesta</li>
    <li>L'icona e il colore dell'aura vengono visualizzati</li>
    <li>Verifica di possedere l'aura richiesta prima di acquisire</li>
</ul>

<h3>📝 Proposte</h3>
<p>Puoi creare proposte per nuove tessiture:</p>
<ul>
    <li>Accedi al sistema di proposte</li>
    <li>Crea una nuova proposta di tessitura</li>
    <li>Lo staff valuterà la proposta</li>
</ul>

<h3>📈 Livelli</h3>
<p>Le tessiture hanno un livello che determina:</p>
<ul>
    <li>Il costo di acquisizione</li>
    <li>La potenza degli effetti</li>
    <li>Possibili prerequisiti</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=12,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # ========== PAGINA: SCHEDA PERSONAGGIO (basata su HomeTab.jsx) ==========
            self.get_or_create_page(
                slug='gestione-personaggio',
                titolo='Scheda Personaggio',
                contenuto='''
<h2>La Scheda del Personaggio</h2>
<p>La sezione <strong>Scheda</strong> (Home) mostra un riepilogo completo del tuo personaggio.</p>

<h3>💰 Risorse</h3>
<p>In alto puoi vedere:</p>
<ul>
    <li><strong>Crediti</strong> - La valuta principale del gioco</li>
    <li><strong>Punti Caratteristica (PC)</strong> - Usati per acquisire abilità</li>
</ul>

<h3>📊 Statistiche</h3>
<p>Le statistiche sono divise in:</p>
<ul>
    <li><strong>Statistiche Primarie</strong> - Le statistiche principali del personaggio (tipo: ST, is_primaria: true)</li>
    <li><strong>Statistiche Secondarie</strong> - Statistiche derivate o secondarie (tipo: ST, is_primaria: false)</li>
</ul>
<p>Ogni statistica mostra:</p>
<ul>
    <li>Il valore base</li>
    <li>I modificatori applicati</li>
    <li>Puoi cliccare per vedere i dettagli dei modificatori</li>
</ul>

<h3>✨ Caratteristiche</h3>
<p>Le caratteristiche (tipo: CA) sono tratti speciali del personaggio:</p>
<ul>
    <li>Visualizzate con la loro icona e colore</li>
    <li>Possono influenzare statistiche e capacità</li>
</ul>

<h3>🌟 Aure</h3>
<p>Le aure possedute (tipo: AU) sono poteri speciali:</p>
<ul>
    <li>Visualizzate con la loro icona e colore</li>
    <li>Possono essere richieste da tessiture o altri elementi</li>
</ul>

<h3>🎯 Abilità Possedute</h3>
<p>Vedi tutte le abilità che il tuo personaggio possiede:</p>
<ul>
    <li>Organizzate per gruppo/tier</li>
    <li>Con descrizioni e dettagli</li>
</ul>

<h3>⚔️ Oggetti Attivi</h3>
<p>Vengono mostrati gli oggetti attualmente attivi:</p>
<ul>
    <li>Oggetti con cariche attive > 0</li>
    <li>MOD e INN (sempre visibili anche se scarichi)</li>
    <li>Oggetti equipaggiati sul corpo</li>
</ul>

<h3>📝 Modificatori Statistiche</h3>
<p>Cliccando su una statistica puoi vedere:</p>
<ul>
    <li>Tutti i modificatori applicati</li>
    <li>La fonte di ogni modificatore</li>
    <li>Il valore totale calcolato</li>
</ul>
                ''',
                parent=pagina_istruzioni,
                ordine=3,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('✓ Generazione completata!'))
        self.stdout.write('=' * 60)
        self.stdout.write('\n📝 Nota: Le istruzioni sono basate sull\'analisi del codice.')
        self.stdout.write('   Puoi modificarle manualmente tramite l\'admin Django per aggiungere dettagli specifici.')
        self.stdout.write('\n')
