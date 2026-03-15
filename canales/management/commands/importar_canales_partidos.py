import json
from django.core.management.base import BaseCommand
from canales.models import Partido


class Command(BaseCommand):
    help = 'Importar canales de partidos desde JSON'

    def handle(self, *args, **options):
        try:
            with open('canales_partidos.json', 'r') as f:
                datos = json.load(f)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('No se encontro canales_partidos.json'))
            return

        actualizados = 0
        for api_id, canales in datos.items():
            updated = Partido.objects.filter(api_id=int(api_id)).update(canales_bolaloca=canales)
            if updated:
                actualizados += 1

        self.stdout.write(self.style.SUCCESS(f'Canales asignados a {actualizados} partidos'))
