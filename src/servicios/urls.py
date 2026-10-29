from django.urls import path
from .views import (
    home_view,
    pasarela_view,
    procesar_pago_view,   
    perfil_view,
    login_view,
    logout_view,
    registro_view,
)

urlpatterns = [
    path('', home_view, name='home'),
    path('planes/', pasarela_view, name='pasarela'),
    path('procesar-pago-ajax/', procesar_pago_view, name='procesar_pago'),
    path('perfil/', perfil_view, name='perfil'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('registro/', registro_view, name='registro'),
]