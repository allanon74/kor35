"""
Campo qr_stampato su QrCode.

Su produzione la colonna può esistere già (aggiunta manualmente) senza modello Django:
allineiamo schema, backfill NULL → false e stato migrazioni.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0184_qrcode_stl_creato"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="qrcode",
                    name="qr_stampato",
                    field=models.BooleanField(
                        default=False,
                        help_text="Indica se il codice QR fisico è stato stampato.",
                        verbose_name="QR stampato",
                    ),
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql="""
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_schema = current_schema()
                              AND table_name = 'personaggi_qrcode'
                              AND column_name = 'qr_stampato'
                        ) THEN
                            ALTER TABLE personaggi_qrcode
                            ADD COLUMN qr_stampato boolean NOT NULL DEFAULT false;
                        ELSE
                            UPDATE personaggi_qrcode
                            SET qr_stampato = false
                            WHERE qr_stampato IS NULL;
                            ALTER TABLE personaggi_qrcode
                            ALTER COLUMN qr_stampato SET DEFAULT false;
                            ALTER TABLE personaggi_qrcode
                            ALTER COLUMN qr_stampato SET NOT NULL;
                        END IF;
                    END $$;
                    """,
                    reverse_sql="""
                    ALTER TABLE personaggi_qrcode
                    DROP COLUMN IF EXISTS qr_stampato;
                    """,
                ),
            ],
        ),
    ]
