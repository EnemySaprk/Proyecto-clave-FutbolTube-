from datetime import date, timedelta
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import Video, Canal, Liga, Partido, BannerImagen
from .serializers import (
    VideoListSerializer, VideoDetailSerializer,
    CanalSerializer, LigaSerializer,
    PartidoSerializer, BannerSerializer,
)


@api_view(['GET'])
def banners(request):
    qs = BannerImagen.objects.filter(activo=True).select_related('canal', 'liga')
    return Response(BannerSerializer(qs, many=True, context={'request': request}).data)


@api_view(['GET'])
def videos_list(request):
    qs = Video.objects.filter(activo=True).select_related('canal').prefetch_related('ligas')

    canal_slug = request.query_params.get('canal')
    liga_slug = request.query_params.get('liga')
    destacados = request.query_params.get('destacados')

    if canal_slug:
        qs = qs.filter(canal__slug=canal_slug)
    if liga_slug:
        qs = qs.filter(ligas__slug=liga_slug)
    if destacados == '1':
        qs = qs.filter(destacado=True)

    return Response(VideoListSerializer(qs, many=True, context={'request': request}).data)


@api_view(['GET'])
def video_detail(request, pk):
    try:
        video = Video.objects.select_related('canal').prefetch_related('ligas', 'enlaces').get(pk=pk, activo=True)
    except Video.DoesNotExist:
        return Response({'error': 'No encontrado'}, status=status.HTTP_404_NOT_FOUND)
    return Response(VideoDetailSerializer(video, context={'request': request}).data)


@api_view(['GET'])
def canales_list(request):
    qs = Canal.objects.filter(activo=True)
    return Response(CanalSerializer(qs, many=True, context={'request': request}).data)


@api_view(['GET'])
def ligas_list(request):
    qs = Liga.objects.filter(activa=True)
    return Response(LigaSerializer(qs, many=True, context={'request': request}).data)


@api_view(['GET'])
def partidos_list(request):
    fecha_str = request.query_params.get('fecha')
    rango = request.query_params.get('rango', '1')  # días a mostrar

    if fecha_str:
        try:
            fecha_inicio = date.fromisoformat(fecha_str)
        except ValueError:
            return Response({'error': 'Fecha inválida. Usa YYYY-MM-DD'}, status=400)
    else:
        fecha_inicio = date.today()

    try:
        dias = int(rango)
    except ValueError:
        dias = 1

    fecha_fin = fecha_inicio + timedelta(days=dias - 1)

    qs = Partido.objects.filter(
        fecha__gte=fecha_inicio,
        fecha__lte=fecha_fin,
    ).order_by('fecha', 'hora')

    return Response(PartidoSerializer(qs, many=True, context={'request': request}).data)


@api_view(['GET'])
def partidos_hoy(request):
    hoy = date.today()
    qs = Partido.objects.filter(fecha=hoy).order_by('hora')
    return Response(PartidoSerializer(qs, many=True, context={'request': request}).data)


@api_view(['GET'])
def partidos_live(request):
    """Endpoint ultraligero para polling en tiempo real. Solo estado y marcador."""
    hoy = date.today()
    data = list(
        Partido.objects.filter(fecha=hoy)
        .values('api_id', 'estado', 'goles_local', 'goles_visitante', 'minuto')
    )
    return Response(data)
