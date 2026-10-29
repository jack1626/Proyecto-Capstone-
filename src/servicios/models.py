import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

# -----------------------------------------------------------------------------
# 1. PERFIL DE CLIENTE / EMPRESA
# -----------------------------------------------------------------------------
class Cliente(models.Model):
    TIPO_PERSONA_CHOICES = [
        ('NATURAL', 'Persona Natural'),
        ('JURIDICA', 'Persona Jurídica'),
    ]

    # Identificación Única y Datos Generales
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tipo_persona = models.CharField(max_length=10, choices=TIPO_PERSONA_CHOICES, default='JURIDICA')
    rut = models.CharField(max_length=12, unique=True, verbose_name="RUT / RUN")
    razon_social = models.CharField(max_length=200, verbose_name="Razón Social / Nombre Completo")
    nombre_fantasia = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nombre Fantasía")
    giro = models.CharField(max_length=255, blank=True, null=True, verbose_name="Giro Comercial")

    # Datos de Contacto
    email = models.EmailField(verbose_name="Correo Electrónico")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    direccion = models.CharField(max_length=255, verbose_name="Dirección Particular/Matriz")
    comuna = models.CharField(max_length=100)
    region = models.CharField(max_length=100)

    # Datos del Representante Legal (Si aplica)
    rep_legal_nombre = models.CharField(max_length=200, blank=True, null=True, verbose_name="Nombre Rep. Legal")
    rep_legal_rut = models.CharField(max_length=12, blank=True, null=True, verbose_name="RUT Rep. Legal")
    rep_legal_email = models.EmailField(blank=True, null=True, verbose_name="Email Rep. Legal")

    # Auditoría Interna CRM
    ejecutivo_responsable = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name="clientes_asignados", verbose_name="Ejecutivo Asignado"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['-fecha_registro']

    def __str__(self):
        return f"{self.razon_social} ({self.rut})"


# -----------------------------------------------------------------------------
# 2. CATÁLOGO DE PLANES / SERVICIOS
# -----------------------------------------------------------------------------
class Plan(models.Model):
    TIPO_SERVICIO_CHOICES = [
        ('DOM_TRIBUTARIO', 'Domicilio Tributario'),
        ('DOM_COMERCIAL', 'Domicilio Comercial'),
        ('OF_VIRTUAL', 'Oficina Virtual Pro'),
        ('EMP_UN_DIA', 'Constitución Empresa en un Día'),
        ('OTRO', 'Otro Servicio'),
    ]

    nombre = models.CharField(max_length=150)
    tipo_servicio = models.CharField(max_length=30, choices=TIPO_SERVICIO_CHOICES, default='DOM_TRIBUTARIO')
    descripcion = models.TextField(verbose_name="Descripción de características")
    precio_mensual = models.IntegerField(default=0, verbose_name="Precio Mensual (CLP)")
    precio_anual = models.IntegerField(default=0, verbose_name="Precio Anual (CLP)")
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Plan / Servicio"
        verbose_name_plural = "Planes / Servicios"

    def __str__(self):
        return f"{self.nombre} - ${self.precio_anual:,} CLP/año"


# -----------------------------------------------------------------------------
# 3. CONTRATACIÓN DE SERVICIOS Y VENCIMIENTOS
# -----------------------------------------------------------------------------
class Contratacion(models.Model):
    ESTADO_CHOICES = [
        ('PENDIENTE_PAGO', 'Pendiente de Pago'),
        ('PENDIENTE_FIRMA', 'Pendiente de Firma'),
        ('ACTIVO', 'Activo'),
        ('POR_VENCER', 'Próximo a Vencer (Alerta)'),
        ('VENCIDO', 'Vencido'),
        ('CANCELADO', 'Cancelado'),
    ]

    folio = models.CharField(max_length=20, unique=True, editable=False, verbose_name="Folio Contrato")
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="contrataciones")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="contrataciones")
    
    # Fechas
    fecha_contratacion = models.DateTimeField(default=timezone.now)
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio del Servicio")
    fecha_vencimiento = models.DateField(verbose_name="Fecha de Vencimiento")
    
    # Estado y Transacciones
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PENDIENTE_PAGO')
    monto_pagado = models.IntegerField(default=0)
    transaccion_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID Pasarela de Pago")

    # Auditoría y Observaciones
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Contratación"
        verbose_name_plural = "Contrataciones"
        ordering = ['-fecha_contratacion']

    def save(self, *args, **kwargs):
        if not self.folio:
            # Genera un folio único automático (ej. EO-202609-001)
            count = Contratacion.objects.count() + 1
            self.folio = f"EO-{timezone.now().strftime('%Y%m')}-{count:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Folio {self.folio} - {self.cliente.razon_social} ({self.plan.nombre})"


# -----------------------------------------------------------------------------
# 4. GESTIÓN DOCUMENTAL Y FIRMA ELECTRÓNICA
# -----------------------------------------------------------------------------
class DocumentoContrato(models.Model):
    ESTADO_FIRMA_CHOICES = [
        ('GENERADO', 'Documento Generado'),
        ('ENVIADO_FIRMA', 'Enviado a Firma Electrónica'),
        ('FIRMADO', 'Firmado Exitosamente'),
        ('RECHAZADO', 'Firma Rechazada/Error'),
    ]

    contratacion = models.OneToOneField(Contratacion, on_delete=models.CASCADE, related_name="documento")
    tipo_documento = models.CharField(max_length=100, default="Contrato Domicilio Tributario")
    
    # Archivos PDF
    archivo_borrador = models.FileField(upload_to="contratos/borradores/", null=True, blank=True)
    archivo_firmado = models.FileField(upload_to="contratos/firmados/", null=True, blank=True)
    
    # Integración con API de Firma Electrónica
    id_proceso_firma = models.CharField(max_length=100, blank=True, null=True, verbose_name="ID API Firma")
    estado_firma = models.CharField(max_length=20, choices=ESTADO_FIRMA_CHOICES, default='GENERADO')
    fecha_firma = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Documento / Contrato"
        verbose_name_plural = "Documentos / Contratos"

    def __str__(self):
        return f"{self.tipo_documento} - Folio {self.contratacion.folio}"
    
import uuid

class DocumentoLegalTech(models.Model):
    TIPO_CHOICES = [
        ('poder_simple', 'Poder Simple SII'),
        ('acuerdo_accionistas', 'Acuerdo de Accionistas'),
        ('arriendo_vehiculo', 'Contrato Arriendo Vehículo'),
        ('arriendo_estacionamiento', 'Contrato Arriendo Estacionamiento'),
    ]

    folio = models.CharField(max_length=20, unique=True, editable=False)
    usuario = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='documentos_legaltech')
    tipo_documento = models.CharField(max_length=30, choices=TIPO_CHOICES)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    datos_json = models.JSONField(help_text="Parámetros ingresados al generar el PDF")

    def save(self, *args, **kwargs):
        if not self.folio:
            # Genera un folio único corto como "LT-2026-A1B2C3"
            self.folio = f"LT-{timezone.now().year}-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.folio} - {self.get_tipo_documento_display()} ({self.usuario.username})"