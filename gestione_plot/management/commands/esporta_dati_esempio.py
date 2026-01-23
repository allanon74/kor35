"""
Management command per esportare dati di esempio dal database.

Questo script esporta dati reali dal database in formato JSON per analizzare
la struttura e generare istruzioni accurate.

Uso:
    python manage.py esporta_dati_esempio
    python manage.py esporta_dati_esempio --output dati_esempio.json
    python manage.py esporta_dati_esempio --limit 5  # Limita il numero di record
"""

from django.core.management.base import BaseCommand
from django.core.serializers import serialize
from django.db.models import Q
import json
import os

# Import dei modelli
from personaggi.models import (
    Personaggio, Oggetto, Abilita, Infusione, Tessitura,
    Punteggio, Statistica, ClasseOggetto, TipologiaPersonaggio,
    PersonaggioStatisticaBase, OggettoStatisticaBase
)


class Command(BaseCommand):
    help = 'Esporta dati di esempio dal database per analisi'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='dati_esempio.json',
            help='File di output (default: dati_esempio.json)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=3,
            help='Numero massimo di record per tipo (default: 3)',
        )
        parser.add_argument(
            '--include-all-punteggi',
            action='store_true',
            help='Include tutti i punteggi disponibili (non solo quelli usati)',
        )

    def serialize_model(self, queryset, fields=None):
        """Serializza un queryset in formato dict"""
        data = []
        for obj in queryset:
            obj_dict = {}
            if fields:
                for field in fields:
                    value = getattr(obj, field, None)
                    # Gestisci ForeignKey e ManyToMany
                    if hasattr(value, 'id'):
                        obj_dict[field] = value.id
                    elif hasattr(value, 'all'):
                        obj_dict[field] = [item.id for item in value.all()[:10]]  # Limita a 10
                    else:
                        obj_dict[field] = value
            else:
                # Serializza tutti i campi
                for field in obj._meta.get_fields():
                    if field.name in ['id', 'password', 'last_login']:  # Salta campi sensibili
                        continue
                    try:
                        value = getattr(obj, field.name, None)
                        if hasattr(value, 'id'):
                            obj_dict[field.name] = value.id
                        elif hasattr(value, 'all'):
                            obj_dict[field.name] = [item.id for item in value.all()[:10]]
                        elif not callable(value):
                            obj_dict[field.name] = value
                    except:
                        pass
            data.append(obj_dict)
        return data

    def handle(self, *args, **options):
        output_file = options.get('output', 'dati_esempio.json')
        limit = options.get('limit', 3)
        include_all_punteggi = options.get('include_all_punteggi', False)

        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('Esportazione Dati di Esempio'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        dati_esportati = {}

        # 1. PUNTEGGI E STATISTICHE (tutti, sono configurazione di sistema)
        self.stdout.write('\n📊 Esportazione Punteggi e Statistiche...')
        punteggi = Punteggio.objects.all().order_by('tipo', 'ordine', 'nome')
        statistiche = Statistica.objects.all().order_by('ordine', 'nome')
        
        dati_esportati['punteggi'] = self.serialize_model(punteggi, [
            'id', 'nome', 'tipo', 'is_primaria', 'ordine', 'colore', 'icona_url'
        ])
        dati_esportati['statistiche'] = self.serialize_model(statistiche, [
            'id', 'nome', 'parametro', 'ordine', 'valore_base_predefinito'
        ])
        self.stdout.write(f'  ✓ {len(dati_esportati["punteggi"])} punteggi, {len(dati_esportati["statistiche"])} statistiche')

        # 2. CLASSI OGGETTO (tutte, sono configurazione)
        self.stdout.write('\n📦 Esportazione Classi Oggetto...')
        classi_oggetto = ClasseOggetto.objects.all().order_by('nome')
        dati_esportati['classi_oggetto'] = self.serialize_model(classi_oggetto, [
            'id', 'nome', 'descrizione', 'tipo_oggetto'
        ])
        self.stdout.write(f'  ✓ {len(dati_esportati["classi_oggetto"])} classi oggetto')

        # 3. TIPOLOGIE PERSONAGGIO
        self.stdout.write('\n👤 Esportazione Tipologie Personaggio...')
        tipologie = TipologiaPersonaggio.objects.all()
        dati_esportati['tipologie_personaggio'] = self.serialize_model(tipologie, [
            'id', 'nome', 'descrizione'
        ])
        self.stdout.write(f'  ✓ {len(dati_esportati["tipologie_personaggio"])} tipologie')

        # 4. PERSONAGGI DI ESEMPIO (con dati completi)
        self.stdout.write('\n👥 Esportazione Personaggi di Esempio...')
        personaggi = Personaggio.objects.select_related('proprietario', 'tipologia').prefetch_related(
            'abilita_possedute', 'infusioni_possedute', 'tessiture_possedute'
        )[:limit]
        
        personaggi_data = []
        for p in personaggi:
            p_data = {
                'id': p.id,
                'nome': p.nome,
                'tipologia': p.tipologia.nome if p.tipologia else None,
                'crediti': p.crediti,
                'punti_caratteristica': p.punti_caratteristica,
                'statistiche_base_dict': p.statistiche_base_dict if hasattr(p, 'statistiche_base_dict') else {},
                'punteggi_base': p.punteggi_base if hasattr(p, 'punteggi_base') else {},
                'abilita_count': p.abilita_possedute.count(),
                'infusioni_count': p.infusioni_possedute.count(),
                'tessiture_count': p.tessiture_possedute.count(),
            }
            
            # Statistiche base del personaggio
            stat_base = PersonaggioStatisticaBase.objects.filter(personaggio=p)
            p_data['statistiche_base'] = [
                {
                    'statistica': s.statistica.nome,
                    'valore_base': s.valore_base
                }
                for s in stat_base[:10]
            ]
            
            personaggi_data.append(p_data)
        
        dati_esportati['personaggi'] = personaggi_data
        self.stdout.write(f'  ✓ {len(personaggi_data)} personaggi')

        # 5. OGGETTI DI ESEMPIO
        self.stdout.write('\n🎒 Esportazione Oggetti di Esempio...')
        oggetti = Oggetto.objects.select_related('oggetto_base_generatore', 'aura', 'classe_oggetto').prefetch_related(
            'statistiche_base', 'caratteristiche'
        )[:limit * 2]  # Più oggetti per vedere varietà
        
        oggetti_data = []
        for o in oggetti:
            # Ottieni l'inventario corrente (può essere un Personaggio o altro)
            try:
                inventario_corrente = o.inventario_corrente
                personaggio_id = None
                if inventario_corrente:
                    # Se l'inventario è un Personaggio, prendi l'ID
                    if isinstance(inventario_corrente, Personaggio):
                        personaggio_id = inventario_corrente.id
            except Exception as e:
                # Se c'è un errore nell'accesso all'inventario, ignora
                personaggio_id = None
            
            o_data = {
                'id': o.id,
                'nome': o.nome,
                'tipo_oggetto': o.tipo_oggetto,
                'slot_corpo': o.slot_corpo,
                'cariche_attuali': o.cariche_attuali,
                'cariche_massime': getattr(o, 'cariche_massime', None),
                'personaggio_id': personaggio_id,
                'aura_colore': o.aura.colore if o.aura else None,
                'aura_nome': o.aura.nome if o.aura else None,
                'is_equipaggiato': o.is_equipaggiato,
                'classe_oggetto': o.classe_oggetto.nome if o.classe_oggetto else None,
                'oggetto_base_generatore': o.oggetto_base_generatore.nome if o.oggetto_base_generatore else None,
            }
            
            # Statistiche base dell'oggetto
            stat_base = OggettoStatisticaBase.objects.filter(oggetto=o)
            o_data['statistiche_base'] = [
                {
                    'statistica': s.statistica.nome,
                    'valore_base': s.valore_base
                }
                for s in stat_base[:5]
            ]
            
            oggetti_data.append(o_data)
        
        dati_esportati['oggetti'] = oggetti_data
        self.stdout.write(f'  ✓ {len(oggetti_data)} oggetti')

        # 6. ABILITÀ DI ESEMPIO
        self.stdout.write('\n⚡ Esportazione Abilità di Esempio...')
        abilita = Abilita.objects.prefetch_related(
            'punteggio_acquisito', 'tiers', 'caratteristica', 'abilitastatistica_set__statistica'
        )[:limit * 2]
        
        abilita_data = []
        for a in abilita:
            a_data = {
                'id': a.id,
                'nome': a.nome,
                'descrizione': a.descrizione[:200] if a.descrizione else None,  # Primi 200 caratteri
                'costo_pc': getattr(a, 'costo_pc', None),
                'costo_crediti': getattr(a, 'costo_crediti', None),
                'is_tratto_aura': getattr(a, 'is_tratto_aura', False),
                'caratteristica': a.caratteristica.nome if a.caratteristica else None,
            }
            
            # Tiers associati
            tiers_abilita = a.tiers.all() if hasattr(a, 'tiers') else []
            a_data['tiers'] = [t.nome for t in tiers_abilita[:3]]
            
            # Punteggi acquisiti
            punteggi_abilita = a.punteggio_acquisito.all() if hasattr(a, 'punteggio_acquisito') else []
            a_data['punteggi_acquisiti'] = [p.nome for p in punteggi_abilita[:5]]
            
            # Statistiche modificate (usando gli oggetti intermedi AbilitaStatistica)
            stats_abilita = a.abilitastatistica_set.all() if hasattr(a, 'abilitastatistica_set') else []
            a_data['statistiche'] = [
                {
                    'statistica': s.statistica.nome,
                    'tipo_modificatore': s.tipo_modificatore,
                    'valore': s.valore
                }
                for s in stats_abilita[:5]
            ]
            
            abilita_data.append(a_data)
        
        dati_esportati['abilita'] = abilita_data
        self.stdout.write(f'  ✓ {len(abilita_data)} abilità')

        # 7. INFUSIONI DI ESEMPIO
        self.stdout.write('\n🧪 Esportazione Infusioni di Esempio...')
        infusioni = Infusione.objects.prefetch_related(
            'statistiche_base', 'caratteristiche'
        )[:limit * 2]
        
        infusioni_data = []
        for i in infusioni:
            i_data = {
                'id': i.id,
                'nome': i.nome,
                'descrizione': i.descrizione[:200] if i.descrizione else None,
                'livello': getattr(i, 'livello', None),
                'costo_crediti': getattr(i, 'costo_crediti', None),
                'costo_effettivo': getattr(i, 'costo_effettivo', None),
            }
            
            # Statistiche base
            stats_base = i.statistiche_base.all() if hasattr(i, 'statistiche_base') else []
            i_data['statistiche_base'] = [
                {
                    'statistica': s.statistica.nome,
                    'valore_base': s.valore_base
                }
                for s in stats_base[:5]
            ]
            
            infusioni_data.append(i_data)
        
        dati_esportati['infusioni'] = infusioni_data
        self.stdout.write(f'  ✓ {len(infusioni_data)} infusioni')

        # 8. TESSITURE DI ESEMPIO
        self.stdout.write('\n🧬 Esportazione Tessiture di Esempio...')
        tessiture = Tessitura.objects.prefetch_related(
            'statistiche_base', 'caratteristiche', 'aura_richiesta'
        )[:limit * 2]
        
        tessiture_data = []
        for t in tessiture:
            t_data = {
                'id': t.id,
                'nome': t.nome,
                'descrizione': t.descrizione[:200] if t.descrizione else None,
                'livello': getattr(t, 'livello', None),
                'costo_crediti': getattr(t, 'costo_crediti', None),
                'costo_effettivo': getattr(t, 'costo_effettivo', None),
                'aura_richiesta': t.aura_richiesta.nome if hasattr(t, 'aura_richiesta') and t.aura_richiesta else None,
            }
            
            # Statistiche base
            stats_base = t.statistiche_base.all() if hasattr(t, 'statistiche_base') else []
            t_data['statistiche_base'] = [
                {
                    'statistica': s.statistica.nome,
                    'valore_base': s.valore_base
                }
                for s in stats_base[:5]
            ]
            
            tessiture_data.append(t_data)
        
        dati_esportati['tessiture'] = tessiture_data
        self.stdout.write(f'  ✓ {len(tessiture_data)} tessiture')

        # 9. METADATI E RIEPILOGO
        self.stdout.write('\n📋 Generazione Metadati...')
        dati_esportati['metadata'] = {
            'data_esportazione': str(self.now()),
            'limite_record': limit,
            'riepilogo': {
                'punteggi_totali': Punteggio.objects.count(),
                'statistiche_totali': Statistica.objects.count(),
                'classi_oggetto_totali': ClasseOggetto.objects.count(),
                'personaggi_totali': Personaggio.objects.count(),
                'oggetti_totali': Oggetto.objects.count(),
                'abilita_totali': Abilita.objects.count(),
                'infusioni_totali': Infusione.objects.count(),
                'tessiture_totali': Tessitura.objects.count(),
            },
            'tipi_oggetto_utilizzati': list(Oggetto.objects.values_list('tipo_oggetto', flat=True).distinct()),
            'slot_corpo_utilizzati': list(Oggetto.objects.exclude(slot_corpo__isnull=True).values_list('slot_corpo', flat=True).distinct()),
        }

        # Salva il file
        self.stdout.write(f'\n💾 Salvataggio in {output_file}...')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dati_esportati, f, indent=2, ensure_ascii=False, default=str)
        
        file_size = os.path.getsize(output_file) / 1024  # KB
        self.stdout.write(self.style.SUCCESS(f'\n✓ Esportazione completata!'))
        self.stdout.write(f'  📄 File: {output_file}')
        self.stdout.write(f'  📊 Dimensione: {file_size:.2f} KB')
        self.stdout.write(f'\n📝 Puoi condividere questo file per analizzare la struttura reale dei dati.')

    def now(self):
        from django.utils import timezone
        return timezone.now()
