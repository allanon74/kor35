"""
Management command per generare pagine di istruzione basate su dati esportati.

Questo script legge un file JSON esportato con esporta_dati_esempio.py
e genera istruzioni accurate basate sui dati reali del database.

Uso:
    python manage.py genera_istruzioni_da_dati --input dati_esempio.json
    python manage.py genera_istruzioni_da_dati --input dati_esempio.json --force
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from gestione_plot.models import PaginaRegolamento
import json
import os


class Command(BaseCommand):
    help = 'Genera pagine di istruzione basate su dati esportati'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input',
            type=str,
            required=True,
            help='File JSON con dati esportati (da esporta_dati_esempio.py)',
        )
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

    def generate_inventario_content(self, dati):
        """Genera contenuto per la pagina Inventario basato sui dati reali"""
        oggetti = dati.get('oggetti', [])
        classi = dati.get('classi_oggetto', [])
        metadata = dati.get('metadata', {})
        
        tipi_oggetto = metadata.get('tipi_oggetto_utilizzati', [])
        slot_utilizzati = metadata.get('slot_corpo_utilizzati', [])
        
        # Mappa nomi tipi oggetto
        tipo_names = {
            'FIS': 'Oggetto Fisico',
            'MAT': 'Materia (Mondana)',
            'MOD': 'Mod (Tecnologica)',
            'INN': 'Innesto (Tecnologico)',
            'MUT': 'Mutazione (Innata)',
            'AUM': 'Aumento (installazione corporea)',
            'POT': 'Potenziamento (installazione su oggetti)',
        }
        
        # Mappa nomi slot
        slot_names = {
            'HD1': 'Testa 1 (Cranio/Cervello/Occhi)',
            'HD2': 'Testa 2 (Volto/Orecchie)',
            'TR1': 'Tronco 1 (Torace/Cuore/Polmoni)',
            'TR2': 'Tronco 2 (Addome/Spina Dorsale/Pelle)',
            'RA': 'Braccio Destro',
            'LA': 'Braccio Sinistro',
            'RL': 'Gamba Destra',
            'LL': 'Gamba Sinistra',
        }
        
        content = '<h2>Gestione dell\'Inventario</h2>\n'
        content += '<p>La sezione <strong>Zaino</strong> ti permette di gestire tutti gli oggetti in tuo possesso.</p>\n\n'
        
        # Slot corporei
        if slot_utilizzati:
            content += '<h3>👤 Slot Corporei</h3>\n'
            content += '<p>Il corpo del personaggio ha <strong>8 slot corporei</strong> dove puoi equipaggiare oggetti:</p>\n<ul>\n'
            for slot in ['HD1', 'HD2', 'TR1', 'TR2', 'RA', 'LA', 'RL', 'LL']:
                if slot in slot_utilizzati or not slot_utilizzati:  # Mostra tutti se nessuno specifico
                    content += f'<li><strong>{slot}</strong> - {slot_names.get(slot, slot)}</li>\n'
            content += '</ul>\n\n'
        
        # Tipi di oggetti
        if tipi_oggetto:
            content += '<h3>⚔️ Tipi di Oggetti</h3>\n'
            content += '<p>Gli oggetti possono essere di diversi tipi:</p>\n<ul>\n'
            for tipo in tipi_oggetto:
                nome = tipo_names.get(tipo, tipo)
                content += f'<li><strong>{tipo}</strong> - {nome}</li>\n'
            content += '</ul>\n\n'
        
        # Esempi di oggetti con cariche
        oggetti_con_cariche = [o for o in oggetti if o.get('cariche_attuali', 0) > 0]
        if oggetti_con_cariche:
            content += '<h3>🔋 Sistema di Cariche</h3>\n'
            content += '<p>Alcuni oggetti hanno un sistema di cariche:</p>\n<ul>\n'
            content += '<li>Visualizza le <strong>cariche attuali</strong> di ogni oggetto</li>\n'
            content += '<li>Gli oggetti con cariche > 0 sono mostrati come "attivi"</li>\n'
            content += '<li>Puoi ricaricare oggetti quando necessario</li>\n'
            content += '<li>MOD e INN sono sempre visibili anche se scarichi</li>\n'
            content += '</ul>\n\n'
        
        return content

    def generate_abilita_content(self, dati):
        """Genera contenuto per la pagina Abilità basato sui dati reali"""
        abilita = dati.get('abilita', [])
        
        content = '<h2>Gestione delle Abilità</h2>\n'
        content += '<p>La sezione <strong>Abilità</strong> ti permette di visualizzare e acquisire nuove competenze.</p>\n\n'
        
        # Costi
        abilita_con_pc = [a for a in abilita if a.get('costo_pc')]
        abilita_con_crediti = [a for a in abilita if a.get('costo_crediti')]
        abilita_tratti = [a for a in abilita if a.get('is_tratto_aura')]
        
        if abilita_con_pc or abilita_con_crediti:
            content += '<h3>💰 Costi di Acquisizione</h3>\n'
            content += '<p>Le abilità possono costare:</p>\n<ul>\n'
            if abilita_con_pc:
                content += '<li><strong>Punti Caratteristica (PC)</strong> - calcolati dinamicamente</li>\n'
            if abilita_con_crediti:
                content += '<li><strong>Crediti</strong> - calcolati dinamicamente</li>\n'
            content += '<li>Alcune abilità possono richiedere entrambi</li>\n'
            content += '</ul>\n\n'
        
        # Tratti speciali
        if abilita_tratti:
            content += '<h3>✨ Tratti Speciali e Aure</h3>\n'
            content += '<p>Alcune abilità sono marcate come <strong>tratti speciali</strong>:</p>\n<ul>\n'
            content += '<li>Non appaiono nella lista acquistabili standard</li>\n'
            content += '<li>Vengono gestiti tramite il sistema di Punteggi/Aure</li>\n'
            content += '<li>Visualizzati nella sezione Home/Scheda del personaggio</li>\n'
            content += '</ul>\n\n'
        
        # Esempi di abilità con statistiche
        abilita_con_stats = [a for a in abilita if a.get('statistiche')]
        if abilita_con_stats:
            content += '<h3>📊 Effetti sulle Statistiche</h3>\n'
            content += '<p>Le abilità possono modificare le statistiche del personaggio:</p>\n<ul>\n'
            for a in abilita_con_stats[:3]:  # Primi 3 esempi
                stats = a.get('statistiche', [])
                if stats:
                    content += f'<li><strong>{a.get("nome")}</strong> modifica: '
                    content += ', '.join([s.get('statistica', '') for s in stats[:3]])
                    content += '</li>\n'
            content += '</ul>\n\n'
        
        return content

    def generate_infusioni_content(self, dati):
        """Genera contenuto per la pagina Infusioni basato sui dati reali"""
        infusioni = dati.get('infusioni', [])
        
        content = '<h2>Gestione delle Infusioni</h2>\n'
        content += '<p>La sezione <strong>Infusioni</strong> ti permette di gestire le infusioni possedute.</p>\n\n'
        
        # Livelli e costi
        infusioni_con_livello = [i for i in infusioni if i.get('livello')]
        if infusioni_con_livello:
            content += '<h3>📈 Livelli e Costi</h3>\n'
            content += '<p>Le infusioni hanno un livello che determina il costo:</p>\n<ul>\n'
            for i in infusioni_con_livello[:3]:
                livello = i.get('livello', 'N/A')
                costo_eff = i.get('costo_effettivo')
                costo_cred = i.get('costo_crediti')
                costo = costo_eff if costo_eff else (costo_cred if costo_cred else f'{livello} × 100')
                content += f'<li><strong>{i.get("nome")}</strong> - Livello {livello}, Costo: {costo} crediti</li>\n'
            content += '</ul>\n\n'
        
        # Statistiche base
        infusioni_con_stats = [i for i in infusioni if i.get('statistiche_base')]
        if infusioni_con_stats:
            content += '<h3>📊 Effetti sulle Statistiche</h3>\n'
            content += '<p>Le infusioni possono modificare le statistiche base:</p>\n<ul>\n'
            for i in infusioni_con_stats[:3]:
                stats = i.get('statistiche_base', [])
                if stats:
                    content += f'<li><strong>{i.get("nome")}</strong> modifica: '
                    content += ', '.join([s.get('statistica', '') for s in stats[:3]])
                    content += '</li>\n'
            content += '</ul>\n\n'
        
        return content

    def generate_tessiture_content(self, dati):
        """Genera contenuto per la pagina Tessiture basato sui dati reali"""
        tessiture = dati.get('tessiture', [])
        
        content = '<h2>Gestione delle Tessiture</h2>\n'
        content += '<p>La sezione <strong>Tessiture</strong> ti permette di gestire le tessiture possedute.</p>\n\n'
        
        # Aura richiesta
        tessiture_con_aura = [t for t in tessiture if t.get('aura_richiesta')]
        if tessiture_con_aura:
            content += '<h3>✨ Aura Richiesta</h3>\n'
            content += '<p>Alcune tessiture richiedono un\'aura specifica:</p>\n<ul>\n'
            for t in tessiture_con_aura[:3]:
                content += f'<li><strong>{t.get("nome")}</strong> richiede: {t.get("aura_richiesta")}</li>\n'
            content += '</ul>\n\n'
        
        # Livelli e costi
        tessiture_con_livello = [t for t in tessiture if t.get('livello')]
        if tessiture_con_livello:
            content += '<h3>📈 Livelli e Costi</h3>\n'
            content += '<p>Le tessiture hanno un livello che determina il costo:</p>\n<ul>\n'
            for t in tessiture_con_livello[:3]:
                livello = t.get('livello', 'N/A')
                costo_eff = t.get('costo_effettivo')
                costo_cred = t.get('costo_crediti')
                costo = costo_eff if costo_eff else (costo_cred if costo_cred else f'{livello} × 100')
                content += f'<li><strong>{t.get("nome")}</strong> - Livello {livello}, Costo: {costo} crediti</li>\n'
            content += '</ul>\n\n'
        
        return content

    def generate_scheda_content(self, dati):
        """Genera contenuto per la pagina Scheda basato sui dati reali"""
        punteggi = dati.get('punteggi', [])
        statistiche = dati.get('statistiche', [])
        personaggi = dati.get('personaggi', [])
        
        content = '<h2>La Scheda del Personaggio</h2>\n'
        content += '<p>La sezione <strong>Scheda</strong> mostra un riepilogo completo del tuo personaggio.</p>\n\n'
        
        # Statistiche primarie e secondarie
        stat_primarie = [p for p in punteggi if p.get('tipo') == 'ST' and p.get('is_primaria')]
        stat_secondarie = [p for p in punteggi if p.get('tipo') == 'ST' and not p.get('is_primaria')]
        
        if stat_primarie:
            content += '<h3>📊 Statistiche Primarie</h3>\n'
            content += '<p>Le statistiche principali del personaggio:</p>\n<ul>\n'
            for s in stat_primarie[:5]:
                content += f'<li><strong>{s.get("nome")}</strong></li>\n'
            content += '</ul>\n\n'
        
        if stat_secondarie:
            content += '<h3>📊 Statistiche Secondarie</h3>\n'
            content += '<p>Statistiche derivate o secondarie:</p>\n<ul>\n'
            for s in stat_secondarie[:5]:
                content += f'<li><strong>{s.get("nome")}</strong></li>\n'
            content += '</ul>\n\n'
        
        # Caratteristiche e Aure
        caratteristiche = [p for p in punteggi if p.get('tipo') == 'CA']
        aure = [p for p in punteggi if p.get('tipo') == 'AU']
        
        if caratteristiche:
            content += '<h3>✨ Caratteristiche</h3>\n'
            content += '<p>Tratti speciali del personaggio (tipo: CA):</p>\n<ul>\n'
            for c in caratteristiche[:5]:
                content += f'<li><strong>{c.get("nome")}</strong></li>\n'
            content += '</ul>\n\n'
        
        if aure:
            content += '<h3>🌟 Aure</h3>\n'
            content += '<p>Potenze speciali del personaggio (tipo: AU):</p>\n<ul>\n'
            for a in aure[:5]:
                content += f'<li><strong>{a.get("nome")}</strong></li>\n'
            content += '</ul>\n\n'
        
        # Risorse
        if personaggi:
            p = personaggi[0]
            content += '<h3>💰 Risorse</h3>\n'
            content += '<ul>\n'
            if p.get('crediti') is not None:
                content += '<li><strong>Crediti</strong> - La valuta principale del gioco</li>\n'
            if p.get('punti_caratteristica') is not None:
                content += '<li><strong>Punti Caratteristica (PC)</strong> - Usati per acquisire abilità</li>\n'
            content += '</ul>\n\n'
        
        return content

    def handle(self, *args, **options):
        input_file = options.get('input')
        force = options.get('force', False)

        if not os.path.exists(input_file):
            self.stdout.write(self.style.ERROR(f'File non trovato: {input_file}'))
            return

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Generazione Istruzioni da Dati Reali'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        # Carica i dati
        self.stdout.write(f'\n📂 Caricamento dati da {input_file}...')
        with open(input_file, 'r', encoding='utf-8') as f:
            dati = json.load(f)
        
        self.stdout.write(self.style.SUCCESS('✓ Dati caricati'))

        with transaction.atomic():
            # Pagina parent
            pagina_istruzioni = self.get_or_create_page(
                slug='istruzioni',
                titolo='Istruzioni',
                contenuto='<h2>Istruzioni per l\'utilizzo dell\'App Kor35</h2>',
                ordine=1,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            # Genera pagine basate sui dati
            self.stdout.write('\n📝 Generazione pagine...')
            
            self.get_or_create_page(
                slug='inventario',
                titolo='Inventario e Zaino',
                contenuto=self.generate_inventario_content(dati),
                parent=pagina_istruzioni,
                ordine=10,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            self.get_or_create_page(
                slug='abilita',
                titolo='Abilità e Competenze',
                contenuto=self.generate_abilita_content(dati),
                parent=pagina_istruzioni,
                ordine=11,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            self.get_or_create_page(
                slug='infusioni',
                titolo='Infusioni',
                contenuto=self.generate_infusioni_content(dati),
                parent=pagina_istruzioni,
                ordine=13,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            self.get_or_create_page(
                slug='tessiture',
                titolo='Tessiture',
                contenuto=self.generate_tessiture_content(dati),
                parent=pagina_istruzioni,
                ordine=12,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

            self.get_or_create_page(
                slug='gestione-personaggio',
                titolo='Scheda Personaggio',
                contenuto=self.generate_scheda_content(dati),
                parent=pagina_istruzioni,
                ordine=3,
                public=True,
                visibile_solo_staff=False,
                force=force
            )

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(self.style.SUCCESS('✓ Generazione completata!'))
        self.stdout.write('=' * 60)
        self.stdout.write('\n📝 Le istruzioni sono state generate basandosi sui dati reali del database.')
