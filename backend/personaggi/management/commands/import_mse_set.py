"""Import singolo package `.mse-set` in EspansioneCarte + carte."""
from django.core.management.base import BaseCommand

from gestione_plot.models import Campagna
from personaggi.carte_platform_models import CarteGiocoDefinizione
from personaggi.mse_set_import import import_mse_set_package


class Command(BaseCommand):
    help = "Importa un file .mse-set o .zip in EspansioneCarte + catalogo carte."

    def add_arguments(self, parser):
        parser.add_argument("--campagna-slug", required=True)
        parser.add_argument("--gioco-slug", default="", help="Slug CarteGiocoDefinizione (default: unico gioco campagna)")
        parser.add_argument("--file", required=True, help="Path al .mse-set o .zip")
        parser.add_argument("--espansione-slug", default="")
        parser.add_argument("--espansione-nome", default="")
        parser.add_argument("--no-cards", action="store_true", help="Importa solo espansione/package, senza carte")

    def handle(self, *args, **options):
        campagna = Campagna.objects.filter(slug=options["campagna_slug"]).first()
        if not campagna:
            self.stderr.write(f"Campagna non trovata: {options['campagna_slug']}")
            return

        gioco_qs = CarteGiocoDefinizione.objects.filter(campagna=campagna)
        if options["gioco_slug"]:
            gioco = gioco_qs.filter(slug=options["gioco_slug"]).first()
        else:
            gioco = gioco_qs.first() if gioco_qs.count() == 1 else None
        if not gioco:
            self.stderr.write("Gioco non trovato: specificare --gioco-slug")
            return

        path = options["file"]
        with open(path, "rb") as fh:
            class _Up:
                name = path.split("/")[-1]

                def read(self_inner):
                    return fh.read()

            up = _Up()
            fh.seek(0)
            result = import_mse_set_package(
                campagna=campagna,
                gioco=gioco,
                upload_file=up,
                espansione_slug=options["espansione_slug"],
                espansione_nome=options["espansione_nome"],
                create_cards=not options["no_cards"],
            )
        self.stdout.write(self.style.SUCCESS(str(result)))
