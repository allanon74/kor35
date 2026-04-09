"""
Management command per popolare la configurazione del sito e i link social con dati iniziali
"""
from django.core.management.base import BaseCommand
from gestione_plot.models import ConfigurazioneSito, LinkSocial


class Command(BaseCommand):
    help = 'Popola la configurazione del sito e i link social con dati iniziali'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('\n=== Popolamento Configurazione Sito ===\n'))
        
        # Crea o aggiorna la configurazione del sito
        config, created = ConfigurazioneSito.objects.get_or_create(pk=1)
        
        if created:
            self.stdout.write(self.style.SUCCESS('✓ Configurazione sito creata con dati di default'))
        else:
            self.stdout.write(self.style.WARNING('→ Configurazione sito già esistente, non modificata'))
        
        # Visualizza i dati attuali
        self.stdout.write(f'\nDati attuali:')
        self.stdout.write(f'  - Nome associazione: {config.nome_associazione}')
        self.stdout.write(f'  - Email: {config.email}')
        self.stdout.write(f'  - Sede: {config.indirizzo}, {config.citta}')
        self.stdout.write(f'  - Anno fondazione: {config.anno_fondazione}')
        
        # Link social di esempio
        self.stdout.write(self.style.SUCCESS('\n=== Popolamento Link Social ===\n'))
        
        social_defaults = [
            {
                'tipo': 'whatsapp',
                'nome_visualizzato': 'Gruppo WhatsApp',
                'url': 'https://wa.me/393471234567',
                'descrizione': 'Gruppo WhatsApp KOR35',
                'ordine': 1,
            },
            {
                'tipo': 'instagram',
                'nome_visualizzato': '@kor35official',
                'url': 'https://instagram.com/kor35official',
                'descrizione': 'Seguici su Instagram',
                'ordine': 2,
            },
            {
                'tipo': 'facebook',
                'nome_visualizzato': 'KOR35 Official',
                'url': 'https://facebook.com/kor35',
                'descrizione': 'Pagina Facebook ufficiale',
                'ordine': 3,
            },
            {
                'tipo': 'youtube',
                'nome_visualizzato': 'KOR35 Channel',
                'url': 'https://youtube.com/@kor35',
                'descrizione': 'Video e highlights',
                'ordine': 4,
            },
            {
                'tipo': 'email',
                'nome_visualizzato': 'Scrivici',
                'url': 'mailto:info@kor35.it',
                'descrizione': 'Email di contatto',
                'ordine': 5,
            },
        ]
        
        for social_data in social_defaults:
            social, created = LinkSocial.objects.get_or_create(
                tipo=social_data['tipo'],
                defaults=social_data
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS(f'✓ Creato link {social.get_tipo_display()}: {social.nome_visualizzato}'))
            else:
                self.stdout.write(self.style.WARNING(f'→ Link {social.get_tipo_display()} già esistente'))
        
        # Riepilogo
        total_links = LinkSocial.objects.filter(attivo=True).count()
        self.stdout.write(self.style.SUCCESS(f'\n✓ Totale link social attivi: {total_links}'))
        
        self.stdout.write(self.style.SUCCESS('\n=== Popolamento completato ==='))
        self.stdout.write(self.style.WARNING('\n⚠ IMPORTANTE: Modifica questi dati tramite l\'admin Django:'))
        self.stdout.write('  - Configurazione Sito: /admin/gestione_plot/configurazionesito/')
        self.stdout.write('  - Link Social: /admin/gestione_plot/linksocial/')
