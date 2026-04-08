"""
Comando: python manage.py obtener_logos

Obtiene logos de equipos y ligas usando:
  1. TheSportsDB (gratuito, sin API key)
  2. Logos hardcodeados para CONMEBOL (Copa Libertadores, Sudamericana, etc.)

Actualiza equipo_local_logo, equipo_visitante_logo y liga_logo
en todos los Partido que los tengan vacíos.
"""
import time
import requests
from django.core.management.base import BaseCommand
from canales.models import Partido

# ── Logos de ligas hardcodeados (TheSportsDB CDN) ─────────────────────────────
LOGOS_LIGAS = {
    'copa libertadores':       'https://www.thesportsdb.com/images/media/league/badge/copa-libertadores.png',
    'copa sudamericana':       'https://www.thesportsdb.com/images/media/league/badge/copa-sudamericana.png',
    'liga betplay':            'https://www.thesportsdb.com/images/media/league/badge/liga-betplay-dimayor.png',
    'primera a':               'https://www.thesportsdb.com/images/media/league/badge/liga-betplay-dimayor.png',
    'categoria primera':       'https://www.thesportsdb.com/images/media/league/badge/liga-betplay-dimayor.png',
    'premier league':          'https://crests.football-data.org/PL.png',
    'la liga':                 'https://crests.football-data.org/PD.png',
    'primera division':        'https://crests.football-data.org/PD.png',
    'serie a':                 'https://crests.football-data.org/SA.png',
    'bundesliga':              'https://crests.football-data.org/BL1.png',
    'ligue 1':                 'https://crests.football-data.org/FL1.png',
    'champions league':        'https://crests.football-data.org/CL.png',
    'uefa champions league':   'https://crests.football-data.org/CL.png',
    'europa league':           'https://crests.football-data.org/EL.png',
    'conference league':       'https://crests.football-data.org/UECL.png',
    'fifa world cup':          'https://crests.football-data.org/WC.png',
    'world cup':               'https://crests.football-data.org/WC.png',
    'copa argentina':          'https://www.thesportsdb.com/images/media/league/badge/copa-argentina.png',
    'concacaf champions':      'https://www.thesportsdb.com/images/media/league/badge/concacaf-champions.png',
    'liga mx':                 'https://www.thesportsdb.com/images/media/league/badge/liga-mx.png',
    'nations league':          'https://www.thesportsdb.com/images/media/league/badge/nations-league.png',
}

TSDB_BASE = 'https://www.thesportsdb.com/api/v1/json/3'
TSDB_HEADERS = {'User-Agent': 'Mozilla/5.0'}


class Command(BaseCommand):
    help = 'Obtener logos de equipos y ligas para partidos sin logo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--todos', action='store_true',
            help='Actualizar todos los logos, no solo los vacíos',
        )
        parser.add_argument(
            '--solo-ligas', action='store_true',
            help='Actualizar solo logos de ligas',
        )

    def handle(self, *args, **options):
        solo_ligas = options['solo_ligas']
        actualizar_todos = options['todos']

        self.stdout.write('=== LOGOS DE LIGAS ===')
        self.actualizar_logos_ligas(actualizar_todos)

        if not solo_ligas:
            self.stdout.write('\n=== LOGOS DE EQUIPOS ===')
            self.actualizar_logos_equipos(actualizar_todos)

        self.stdout.write(self.style.SUCCESS('\nLogos actualizados.'))

    # ── Ligas ──────────────────────────────────────────────────────────────────

    def actualizar_logos_ligas(self, todos):
        if todos:
            partidos = Partido.objects.all()
        else:
            partidos = Partido.objects.filter(liga_logo='')

        ligas_sin_logo = (
            partidos
            .values_list('liga_nombre', flat=True)
            .distinct()
        )

        actualizados = 0
        for liga_nombre in ligas_sin_logo:
            logo = self._logo_liga(liga_nombre)
            if logo:
                n = Partido.objects.filter(liga_nombre=liga_nombre).update(liga_logo=logo)
                actualizados += n
                self.stdout.write(
                    self.style.SUCCESS(f'  OK {liga_nombre}: {logo[:60]}')
                )
            else:
                self.stdout.write(f'  ? {liga_nombre}: sin logo encontrado')

        self.stdout.write(f'  Partidos con liga logo actualizado: {actualizados}')

    def _logo_liga(self, liga_nombre):
        """Busca logo de liga: primero en mapa, luego en TheSportsDB."""
        nombre_lower = liga_nombre.lower()

        # 1. Mapa hardcodeado
        for keyword, url in LOGOS_LIGAS.items():
            if keyword in nombre_lower:
                return url

        # 2. TheSportsDB
        try:
            r = requests.get(
                f'{TSDB_BASE}/search_all_leagues.php',
                params={'s': 'Soccer'},
                headers=TSDB_HEADERS,
                timeout=10,
            )
            if r.status_code == 200:
                leagues = r.json().get('countrys') or []
                nombre_norm = nombre_lower.replace(' ', '')
                for league in leagues:
                    strName = (league.get('strLeague') or '').lower().replace(' ', '')
                    if strName and strName in nombre_norm or nombre_norm in strName:
                        badge = league.get('strBadge') or league.get('strLogo')
                        if badge:
                            return badge
        except Exception:
            pass

        return ''

    # ── Equipos ─────────────────────────────────────────────────────────────────

    def actualizar_logos_equipos(self, todos):
        if todos:
            partidos = Partido.objects.all()
        else:
            partidos = Partido.objects.filter(
                equipo_local_logo=''
            ) | Partido.objects.filter(
                equipo_visitante_logo=''
            )

        # Recopilar todos los equipos únicos sin logo
        equipos_sin_logo = set()
        for p in partidos:
            if not p.equipo_local_logo:
                equipos_sin_logo.add(p.equipo_local)
            if not p.equipo_visitante_logo:
                equipos_sin_logo.add(p.equipo_visitante)

        self.stdout.write(f'  {len(equipos_sin_logo)} equipos sin logo')

        # Caché de logos obtenidos
        cache = {}
        actualizados_local = 0
        actualizados_visit = 0

        for equipo in sorted(equipos_sin_logo):
            if equipo in cache:
                logo = cache[equipo]
            else:
                logo = self._logo_equipo(equipo)
                cache[equipo] = logo
                time.sleep(0.5)  # Respetar rate limit de TheSportsDB

            if logo:
                n = Partido.objects.filter(equipo_local=equipo, equipo_local_logo='').update(
                    equipo_local_logo=logo
                )
                actualizados_local += n
                n = Partido.objects.filter(equipo_visitante=equipo, equipo_visitante_logo='').update(
                    equipo_visitante_logo=logo
                )
                actualizados_visit += n
                self.stdout.write(self.style.SUCCESS(f'  OK {equipo}'))
            else:
                self.stdout.write(f'  ? {equipo}: no encontrado')

        self.stdout.write(
            f'  Logos actualizados: {actualizados_local} locales, {actualizados_visit} visitantes'
        )

    def _logo_equipo(self, nombre_equipo):
        """Busca logo de equipo en TheSportsDB."""
        # Normalizar nombre: quitar acentos y caracteres raros
        nombre_limpio = self._normalizar(nombre_equipo)
        if not nombre_limpio or nombre_limpio in ('TBD', 'Por definir', 'tbd'):
            return ''

        try:
            r = requests.get(
                f'{TSDB_BASE}/searchteams.php',
                params={'t': nombre_limpio},
                headers=TSDB_HEADERS,
                timeout=10,
            )
            if r.status_code != 200:
                return ''

            data = r.json()
            teams = data.get('teams') or []
            if not teams:
                # Intentar con nombre recortado (ej: "Real Madrid CF" → "Real Madrid")
                palabras = nombre_limpio.split()
                if len(palabras) > 1:
                    r2 = requests.get(
                        f'{TSDB_BASE}/searchteams.php',
                        params={'t': ' '.join(palabras[:2])},
                        headers=TSDB_HEADERS,
                        timeout=10,
                    )
                    if r2.status_code == 200:
                        teams = r2.json().get('teams') or []

            for team in teams:
                # Filtrar solo equipos de fútbol/soccer
                sport = (team.get('strSport') or '').lower()
                if 'soccer' in sport or 'football' in sport or not sport:
                    badge = team.get('strBadge') or team.get('strLogo') or team.get('strTeamBadge')
                    if badge:
                        return badge

        except Exception as e:
            self.stdout.write(self.style.WARNING(f'    Error {nombre_equipo}: {e}'))

        return ''

    def _normalizar(self, nombre):
        """Quita caracteres de control y normaliza el nombre."""
        if not nombre:
            return ''
        # Reemplazos comunes de nombres de equipos en TheSportsDB
        reemplazos = {
            'FC ': '', ' FC': '', ' CF': '', ' SC': '',
            'Clube ': '', ' Club': '',
            'São Paulo': 'Sao Paulo',
            'Fluminense': 'Fluminense',
            'Atlético': 'Atletico',
            'Académico': 'Academico',
        }
        nombre_limpio = nombre.strip()
        for viejo, nuevo in reemplazos.items():
            nombre_limpio = nombre_limpio.replace(viejo, nuevo)
        return nombre_limpio.strip()
