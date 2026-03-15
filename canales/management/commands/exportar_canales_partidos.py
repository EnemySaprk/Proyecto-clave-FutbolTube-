import json
from django.core.management.base import BaseCommand
from canales.models import Partido


class Command(BaseCommand):
    help = 'Exportar canales de partidos a JSON para subir al servidor'

    def handle(self, *args, **options):
        datos = {}
        for p in Partido.objects.exclude(canales_bolaloca=''):
            datos[str(p.api_id)] = p.canales_bolaloca

        with open('canales_partidos.json', 'w') as f:
            json.dump(datos, f)

        self.stdout.write(self.style.SUCCESS(f'Exportados {len(datos)} partidos con canales a canales_partidos.json'))
