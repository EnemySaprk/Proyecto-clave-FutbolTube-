import re
import unicodedata
import requests
from bs4 import BeautifulSoup
from datetime import date
from zoneinfo import ZoneInfo
from django.core.management.base import BaseCommand
from canales.models import Partido, Video


SPAIN_TZ = ZoneInfo('Europe/Madrid')
COL_TZ   = ZoneInfo('America/Bogota')

# Mapeo nombre canal tv-libre → titulo de Video en DB
CANAL_MAP = {
    'espn':             'ESPN 1',
    'espn 1':           'ESPN 1',
    'espn 2':           'ESPN 2',
    'espn 3':           'ESPN 3',
    'espn 4':           'ESPN 4',
    'espn premium':     'ESPN Premium',
    'espn deportes':    'ESPN Deportes',
    'dsports':          'DSports',
    'dsports 2':        'DSports 2',
    'dsports+':         'DSports Plus',
    'dsports plus':     'DSports Plus',
    'win sports+':      'Win Sports+',
    'win sports':       'Win Sports+',
    'tnt sports':       'TNT Sports',
    'tnt sports premium': 'TNT Sports',
    'dazn':             'DAZN 1',
    'dazn 1':           'DAZN 1',
    'dazn 2':           'DAZN 2',
    'dazn laliga':      'DAZN LaLiga',
    'dazn f1':          'DAZN F1',
    'movistar laliga':  'Movistar LaLiga',
    'm+ laliga':        'M+ LaLiga TV',
    'liga de campeones':   'Liga de Campeones 1',
    'liga de campeones 1': 'Liga de Campeones 1',
    'liga de campeones 2': 'Liga de Campeones 2',
    'fox sports':       'Fox Sports',
    'fox sports 2':     'Fox Sports 2',
    'fox sports 3':     'Fox Sports 3',
    'star+':            'Star+',
    'disney+':          'Disney+',
    'max':              'MAX',
    'paramount+':       'Paramount+',
    'fanatiz':          'Fanatiz',
    'directv sports':   'DirecTV Sports',
    'directv sports 2': 'DirecTV Sports 2',
}

_RE_CALIDAD = re.compile(r'calidad\s*\d+p', re.IGNORECASE)
_RE_EXTRA   = re.compile(r'\s{2,}')


def _limpiar_canal(nombre):
    """Quita 'Calidad 720p/1080p' y espacios extra."""
    nombre = _RE_CALIDAD.sub('', nombre)
    nombre = _RE_EXTRA.sub(' ', nombre).strip()
    return nombre


def _canal_a_video(nombre_raw, videos_por_titulo):
    """Devuelve Video o None según CANAL_MAP."""
    nombre = _limpiar_canal(nombre_raw).lower()
    titulo_db = CANAL_MAP.get(nombre)
    if titulo_db:
        return videos_por_titulo.get(titulo_db.lower())
    # Búsqueda parcial si no hay match exacto
    for key, titulo_db in CANAL_MAP.items():
        if key in nombre or nombre in key:
            return videos_por_titulo.get(titulo_db.lower())
    return None


def _scrape_tvlibre():
    """Scrapea tv-libre.net/agenda/ y devuelve lista de dicts."""
    url = 'https://tv-libre.net/agenda/'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    res = requests.get(url, headers=headers, timeout=15)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')

    partidos = []
    for item in soup.select('.menu > li'):
        a = item.select_one('a')
        if not a:
            continue
        texto = a.get_text(strip=True)
        hora_el = item.select_one('span.t')
        hora_str = hora_el.get_text(strip=True) if hora_el else ''

        # Limpiar nombre del partido
        nombre = texto.replace(hora_str, '').strip()

        # Separar liga del partido (ej: "Serie A: Atalanta vs. Juventus")
        if ':' in nombre:
            _, nombre = nombre.split(':', 1)
            nombre = nombre.strip()

        canales = [
            {'canal': c.get_text(strip=True), 'url': c.get('href', '')}
            for c in item.select('.subitem1 a')
        ]

        partidos.append({
            'nombre':  nombre,
            'hora':    hora_str,
            'canales': canales,
        })
    return partidos


def _hora_spain_a_col(hora_str):
    """Convierte 'HH:MM' de España (CEST/CET) a hora Colombia."""
    try:
        h, m = map(int, hora_str.split(':'))
        from datetime import datetime
        dt_spain = datetime.now(SPAIN_TZ).replace(hour=h, minute=m, second=0, microsecond=0)
        dt_col = dt_spain.astimezone(COL_TZ)
        return dt_col.time().replace(second=0, microsecond=0)
    except Exception:
        return None


def _normalizar(texto):
    """Minúsculas, sin acentos, sin caracteres especiales."""
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9 ]', '', texto.lower()).strip()


def _palabras_clave(nombre):
    """Palabras significativas (>3 chars) del nombre de equipo."""
    stopwords = {'the', 'club', 'fc', 'cf', 'sc', 'ac', 'de', 'del', 'la', 'el',
                 'los', 'las', 'and', 'afc', 'fk', 'sk', 'bk', 'if', 'vs'}
    return {p for p in _normalizar(nombre).split() if len(p) > 3 and p not in stopwords}


def _buscar_partido(nombre, hora_col, partidos_hoy):
    """
    Busca el Partido en DB por nombre de equipos con matching flexible.
    Divide por ' vs. ' o ' - ', normaliza acentos y usa palabras clave.
    """
    separadores = [' vs. ', ' vs ', ' - ', ' x ']
    local_raw = visitante_raw = None
    for sep in separadores:
        if sep in nombre:
            partes = nombre.split(sep, 1)
            local_raw, visitante_raw = partes[0].strip(), partes[1].strip()
            break

    if not local_raw:
        return None

    kw_local    = _palabras_clave(local_raw)
    kw_visitante = _palabras_clave(visitante_raw)

    mejor = None
    mejor_score = 0

    for p in partidos_hoy:
        kw_db_local  = _palabras_clave(p.equipo_local)
        kw_db_visit  = _palabras_clave(p.equipo_visitante)

        score_local  = len(kw_local & kw_db_local)
        score_visit  = len(kw_visitante & kw_db_visit)
        score = score_local + score_visit

        if score >= 2 and score > mejor_score:
            mejor_score = score
            mejor = p
        elif score == 1:
            # Match mínimo: al menos 1 palabra en cada equipo
            n_local  = _normalizar(local_raw)
            n_visit  = _normalizar(visitante_raw)
            db_local = _normalizar(p.equipo_local)
            db_visit = _normalizar(p.equipo_visitante)
            if (n_local[:5] in db_local or db_local[:5] in n_local) and \
               (n_visit[:5] in db_visit or db_visit[:5] in n_visit):
                if score > mejor_score:
                    mejor_score = score
                    mejor = p

    return mejor


class Command(BaseCommand):
    help = 'Asignar canales a partidos de hoy scrapeando tv-libre.net/agenda/'

    def handle(self, *args, **options):
        self.stdout.write('Scrapeando tv-libre.net/agenda/ ...')

        try:
            agenda = _scrape_tvlibre()
        except Exception as e:
            self.stderr.write(f'Error al scrapear: {e}')
            return

        self.stdout.write(f'  {len(agenda)} partidos encontrados en tv-libre')

        # Cargar partidos de hoy desde DB
        hoy = date.today()
        partidos_hoy = list(Partido.objects.filter(fecha=hoy))
        self.stdout.write(f'  {len(partidos_hoy)} partidos en DB para hoy')

        # Construir lookup de videos por título (lowercase)
        videos_por_titulo = {
            v.titulo.lower(): v
            for v in Video.objects.filter(activo=True)
        }

        actualizados = 0
        sin_partido  = 0
        sin_canal    = 0

        for item in agenda:
            hora_col = _hora_spain_a_col(item['hora'])
            partido  = _buscar_partido(item['nombre'], hora_col, partidos_hoy)

            if not partido:
                sin_partido += 1
                self.stdout.write(f'  [?] Sin match en DB: {item["nombre"]} ({item["hora"]})')
                continue

            # Mapear canales scrapeados → títulos de Video en DB
            titulos = []
            for c in item['canales']:
                video = _canal_a_video(c['canal'], videos_por_titulo)
                if video and video.titulo not in titulos:
                    titulos.append(video.titulo)
                else:
                    nombre_limpio = _limpiar_canal(c['canal'])
                    if nombre_limpio not in titulos:
                        titulos.append(nombre_limpio)

            if not titulos:
                sin_canal += 1
                continue

            nuevo = ', '.join(titulos)
            if partido.canales_bolaloca != nuevo:
                partido.canales_bolaloca = nuevo
                partido.save(update_fields=['canales_bolaloca'])
                actualizados += 1
                self.stdout.write(
                    self.style.SUCCESS(f'  OK {partido.equipo_local} vs {partido.equipo_visitante}: {nuevo}')
                )

        self.stdout.write(self.style.SUCCESS(
            f'\nListo: {actualizados} actualizados | {sin_partido} sin match DB | {sin_canal} sin canal mapeado'
        ))
