from django.urls import path
from . import views
from . import api_views

app_name = 'canales'

urlpatterns = [
    # Web
    path('', views.home, name='home'),
    path('video/<int:pk>/', views.detalle_video, name='detalle_video'),
    path('canal/<slug:slug>/', views.lista_canal, name='canal'),
    path('liga/<slug:slug>/', views.lista_liga, name='liga'),
    path('agenda/', views.agenda, name='agenda'),
    path('mundial/', views.mundial, name='mundial'),

    # API REST
    path('api/banners/', api_views.banners, name='api_banners'),
    path('api/videos/', api_views.videos_list, name='api_videos'),
    path('api/videos/<int:pk>/', api_views.video_detail, name='api_video_detail'),
    path('api/canales/', api_views.canales_list, name='api_canales'),
    path('api/ligas/', api_views.ligas_list, name='api_ligas'),
    path('api/partidos/', api_views.partidos_list, name='api_partidos'),
    path('api/partidos/hoy/', api_views.partidos_hoy, name='api_partidos_hoy'),
    path('api/partidos/live/', api_views.partidos_live, name='api_partidos_live'),
]
