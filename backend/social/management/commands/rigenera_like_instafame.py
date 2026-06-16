from django.core.management.base import BaseCommand
from django.db import transaction

from personaggi.models import Personaggio
from social.influencer import RigeneraLikeInfluencerError, rigenera_like_personaggio, rigenera_tutti_like_instafame


class Command(BaseCommand):
    help = (
        "Ricalcola i peso_like InstaFame con la formula attuale "
        "(random peso liker + random peso autore post/commento)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Esegue la rigenerazione. Senza flag: solo anteprima conteggi.",
        )
        parser.add_argument(
            "--personaggio-id",
            type=int,
            default=None,
            help="Limita la rigenerazione ai like messi da un singolo personaggio.",
        )

    def handle(self, *args, **options):
        personaggio_id = options.get("personaggio_id")
        apply = bool(options.get("apply"))

        if personaggio_id:
            personaggio = Personaggio.objects.filter(pk=personaggio_id).first()
            if not personaggio:
                self.stderr.write(self.style.ERROR(f"Personaggio {personaggio_id} non trovato."))
                return
            scope = f"like messi da «{personaggio.nome}» (id={personaggio.id})"
        else:
            scope = "tutti i like InstaFame (post + commenti)"

        if not apply:
            from social.models import SocialCommentLike, SocialLike

            if personaggio_id:
                post_n = SocialLike.objects.filter(autore_id=personaggio_id).count()
                comment_n = SocialCommentLike.objects.filter(autore_id=personaggio_id).count()
            else:
                post_n = SocialLike.objects.count()
                comment_n = SocialCommentLike.objects.count()
            self.stdout.write(
                f"Dry-run: verrebbero rigenerati {post_n} like post e {comment_n} like commento ({scope})."
            )
            self.stdout.write("Aggiungi --apply per eseguire.")
            return

        try:
            with transaction.atomic():
                if personaggio_id:
                    post_n, comment_n = rigenera_like_personaggio(personaggio)
                else:
                    post_n, comment_n = rigenera_tutti_like_instafame()
        except RigeneraLikeInfluencerError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Rigenerati {post_n} like post e {comment_n} like commento ({scope})."
            )
        )
