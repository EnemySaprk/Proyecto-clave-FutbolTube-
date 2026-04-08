from rest_framework import serializers
from .models import Canal, Video, EnlaceVideo, Liga, Partido, BannerImagen


class LigaSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Liga
        fields = ['id', 'nombre', 'slug', 'pais', 'logo_url']

    def get_logo_url(self, obj):
        request = self.context.get('request')
        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)
        return ''


class CanalSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()

    class Meta:
        model = Canal
        fields = ['id', 'nombre', 'slug', 'descripcion', 'logo_url']

    def get_logo_url(self, obj):
        request = self.context.get('request')
        if obj.logo and request:
            return request.build_absolute_uri(obj.logo.url)
        return ''


class EnlaceVideoSerializer(serializers.ModelSerializer):
    embed_url = serializers.ReadOnlyField()

    class Meta:
        model = EnlaceVideo
        fields = ['id', 'nombre', 'tipo', 'embed_url', 'orden']


class VideoListSerializer(serializers.ModelSerializer):
    canal_nombre = serializers.CharField(source='canal.nombre', read_only=True)
    thumbnail_url = serializers.ReadOnlyField()
    ligas = LigaSerializer(many=True, read_only=True)

    class Meta:
        model = Video
        fields = [
            'id', 'titulo', 'tipo', 'canal_nombre',
            'thumbnail_url', 'ligas', 'destacado', 'fecha_publicacion',
        ]


class VideoDetailSerializer(serializers.ModelSerializer):
    canal = CanalSerializer(read_only=True)
    ligas = LigaSerializer(many=True, read_only=True)
    enlaces = EnlaceVideoSerializer(many=True, read_only=True)
    thumbnail_url = serializers.ReadOnlyField()
    embed_url = serializers.ReadOnlyField()

    class Meta:
        model = Video
        fields = [
            'id', 'titulo', 'tipo', 'canal', 'ligas', 'enlaces',
            'thumbnail_url', 'embed_url', 'descripcion',
            'destacado', 'fecha_publicacion',
        ]


class BannerSerializer(serializers.ModelSerializer):
    imagen_url = serializers.SerializerMethodField()
    canal_nombre = serializers.CharField(source='canal.nombre', read_only=True, default='')
    liga_nombre = serializers.CharField(source='liga.nombre', read_only=True, default='')

    class Meta:
        model = BannerImagen
        fields = ['id', 'titulo', 'descripcion', 'imagen_url', 'canal_nombre', 'liga_nombre', 'orden']

    def get_imagen_url(self, obj):
        request = self.context.get('request')
        if obj.imagen and request:
            return request.build_absolute_uri(obj.imagen.url)
        return ''


class PartidoSerializer(serializers.ModelSerializer):
    canales_transmision = serializers.SerializerMethodField()

    class Meta:
        model = Partido
        fields = [
            'id', 'api_id', 'liga_nombre', 'liga_logo', 'liga_api_id',
            'equipo_local', 'equipo_local_logo',
            'equipo_visitante', 'equipo_visitante_logo',
            'fecha', 'hora', 'estado',
            'goles_local', 'goles_visitante',
            'canales_transmision',
        ]

    def get_canales_transmision(self, obj):
        canales = obj.canales_transmision
        return VideoListSerializer(canales, many=True, context=self.context).data
