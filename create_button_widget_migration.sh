#!/bin/bash
# Script per creare la migration del widget pulsanti

cd /home/django/progetti/kor35
source venv/bin/activate
python manage.py makemigrations gestione_plot
