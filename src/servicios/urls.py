from django.urls import path
from .views import (
    home_view,
    pasarela_view,
    procesar_pago_view,
    perfil_view,
    login_view,
    logout_view,
    registro_view,
    validar_folio_view,
    generar_documento_legaltech_pdf,
    descargar_comprobante_pdf,
    cambiar_estado_contratacion,
)

urlpatterns = [
    path('', home_view, name='home'),
    path('planes/', pasarela_view, name='pasarela'),
    path('procesar-pago-ajax/', procesar_pago_view, name='procesar_pago'),
    path('perfil/', perfil_view, name='perfil'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('registro/', registro_view, name='registro'),
    path('validar/<str:folio>/', validar_folio_view, name='validar_folio'),
    path('documentos/legaltech/<str:tipo_doc>/', generar_documento_legaltech_pdf, name='documento_legaltech_pdf'),
    path('comprobante/<int:contratacion_id>/pdf/', descargar_comprobante_pdf, name='descargar_comprobante_pdf'),
    path('contratacion/<int:contratacion_id>/estado/', cambiar_estado_contratacion, name='cambiar_estado_contratacion'),
]