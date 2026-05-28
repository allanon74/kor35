"""
Campo stl_creato su QrCode.

Su alcuni DB di produzione la colonna esisteva già senza modello Django: allineiamo schema e stato.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("personaggi", "0183_carriera_carica_bonus_crediti_evento"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="qrcode",
                    name="stl_creato",
                    field=models.BooleanField(
                        default=False,
                        help_text="Indica se il file STL associato al QR è stato generato.",
                        verbose_name="STL creato",
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
                              AND column_name = 'stl_creato'
                        ) THEN
                            ALTER TABLE personaggi_qrcode
                            ADD COLUMN stl_creato boolean NOT NULL DEFAULT false;
                        ELSE
                            UPDATE personaggi_qrcode
                            SET stl_creato = false
                            WHERE stl_creato IS NULL;
                            ALTER TABLE personaggi_qrcode
                            ALTER COLUMN stl_creato SET DEFAULT false;
                            ALTER TABLE personaggi_qrcode
                            ALTER COLUMN stl_creato SET NOT NULL;
                        END IF;
                    END $$;
                    """,
                    reverse_sql="""
                    ALTER TABLE personaggi_qrcode
                    DROP COLUMN IF EXISTS stl_creato;
                    """,
                ),
            ],
        ),
    ]
