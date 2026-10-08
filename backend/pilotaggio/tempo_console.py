"""
Secondi rimanenti sull'orologio del nodo che esegue il motore di volo.

La console pilota è un browser su un Raspberry separato (kiosk). In bosco
il mirror spesso non condivide NTP con quel device: confrontare `deadline_at`
con `Date.now()` del browser gonfia il countdown di ore o giorni.
Il client deve partire da questo intero e far scorrere solo il tempo locale
trascorso dal momento in cui ha ricevuto il payload.
"""
from __future__ import annotations

import math
from datetime import datetime
from typing import Optional


def secondi_fino_a(momento: Optional[datetime], ora: Optional[datetime] = None) -> Optional[int]:
    """Secondi interi (ceil) fino a `momento`. 0 se è già passato. None se manca."""
    if momento is None:
        return None
    if ora is None:
        from django.utils import timezone

        ora = timezone.now()
    return max(0, math.ceil((momento - ora).total_seconds()))
