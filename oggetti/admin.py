from django.contrib import admin
from .models import QrCode

# Register your models here.
@admin.register(QrCode)
class QrCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'data_creazione',)
    readonly_fields = ('id', 'data_creazione',) 
    