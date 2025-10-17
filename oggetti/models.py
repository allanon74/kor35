import uuid
from django.db import models

# Create your models here.
class QrCode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_creazione = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return "({codice})".format(codice=self.id)