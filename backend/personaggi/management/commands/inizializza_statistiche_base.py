from django.core.management.base import BaseCommand
from personaggi.models import Personaggio, Statistica, PersonaggioStatisticaBase


class Command(BaseCommand):
    help = 'Inizializza le statistiche_base per tutti i personaggi esistenti con i valori predefiniti'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Sovrascrive i valori esistenti con valore_base_predefinito',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        
        personaggi = Personaggio.objects.all()
        statistiche = Statistica.objects.all()
        
        self.stdout.write(f"Trovati {personaggi.count()} personaggi e {statistiche.count()} statistiche")
        
        totale_creati = 0
        totale_aggiornati = 0
        
        for personaggio in personaggi:
            self.stdout.write(f"\nProcesso: {personaggio.nome} (ID: {personaggio.id})")
            
            for statistica in statistiche:
                # Cerca se esiste già il record
                link, created = PersonaggioStatisticaBase.objects.get_or_create(
                    personaggio=personaggio,
                    statistica=statistica,
                    defaults={'valore_base': statistica.valore_base_predefinito}
                )
                
                if created:
                    totale_creati += 1
                    if statistica.parametro:
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✓ Creato {statistica.parametro}: {statistica.valore_base_predefinito}"
                            )
                        )
                elif force:
                    # Sovrascrivi con il valore predefinito
                    link.valore_base = statistica.valore_base_predefinito
                    link.save()
                    totale_aggiornati += 1
                    if statistica.parametro:
                        self.stdout.write(
                            self.style.WARNING(
                                f"  ⟳ Aggiornato {statistica.parametro}: {statistica.valore_base_predefinito}"
                            )
                        )
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS(f"\n✅ COMPLETATO!"))
        self.stdout.write(f"   Record creati: {totale_creati}")
        if force:
            self.stdout.write(f"   Record aggiornati: {totale_aggiornati}")
        self.stdout.write("\n")
