import json
import io
from datetime import date


from django.contrib.auth.models import User, Group
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout as django_logout, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, FileResponse, Http404
from django.utils import timezone
from django.db.models import Q
from django.urls import reverse

# Para la generación del PDF
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_RIGHT
from .forms import RegistroClienteForm
from .models import Plan, Contratacion, Cliente


# ==========================================
# 1. LANDING PAGE & PASARELA DE VENTAS
# ==========================================

def home_view(request):
    """
    Página de Inicio / Landing Page principal.
    """
    planes = Plan.objects.filter(activo=True) if hasattr(Plan, 'activo') else Plan.objects.all()
    return render(request, 'servicios/home.html', {'planes': planes})


def pasarela_view(request):
    """
    Vista de la pasarela para contratación de planes.
    """
    planes = Plan.objects.filter(activo=True).order_by('precio_mensual') if hasattr(Plan, 'activo') else Plan.objects.all()
    return render(request, 'servicios/pasarela.html', {'planes': planes})


@login_required
@require_POST
def procesar_pago_view(request):
    """
    Procesa la transacción de contratación vía AJAX/Fetch.
    """
    try:
        data = json.loads(request.body)
        plan_nombre = data.get('plan_nombre')
        
        plan = Plan.objects.get(nombre=plan_nombre, activo=True)
        
        cliente, _ = Cliente.objects.get_or_create(
            email=request.user.email,
            defaults={
                'rut': request.user.username,
                'razon_social': request.user.get_full_name() or request.user.username,
                'email': request.user.email,
            }
        )
        
        monto = getattr(plan, 'precio_anual', None)
        if not monto or monto <= 0:
            monto = getattr(plan, 'precio_mensual', getattr(plan, 'precio', 0))

        contratacion = Contratacion.objects.create(
            cliente=cliente,
            plan=plan,
            fecha_inicio=timezone.now().date(),
            fecha_vencimiento=timezone.now().date() + timezone.timedelta(days=365),
            monto_pagado=monto,
            estado='ACTIVO'
        )
        
        folio = getattr(contratacion, 'folio', contratacion.id)

        return JsonResponse({
            'status': 'success',
            'mensaje': f'¡Contratación del plan "{plan.nombre}" realizada exitosamente!',
            'contratacion_id': contratacion.id,
            'folio': folio
        })
        
    except Plan.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'El plan seleccionado no existe o no se encuentra activo.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


# ==========================================
# 2. PERFIL DE USUARIO Y GESTIÓN DE ROLES
# ==========================================

@login_required
def perfil_view(request):
    """
    Perfil dinámico con vista de Cliente o Panel de Ejecutivo.
    Incluye búsqueda por texto y filtro por estado.
    """
    hoy = date.today()
    es_trabajador = request.user.is_staff

    if es_trabajador:
        query = request.GET.get('q', '').strip()
        filtro_estado = request.GET.get('estado', '').strip()

        contrataciones = Contratacion.objects.all().select_related('cliente', 'plan').order_by('-fecha_inicio')

        if query:
            contrataciones = contrataciones.filter(
                Q(cliente__rut__icontains=query) |
                Q(cliente__razon_social__icontains=query) |
                Q(cliente__email__icontains=query)
            )

        if filtro_estado:
            contrataciones = contrataciones.filter(estado=filtro_estado)

        for c in contrataciones:
            c.dias_restantes = (c.fecha_vencimiento - hoy).days if c.fecha_vencimiento else 0

        documentos_legaltech = DocumentoLegalTech.objects.all().select_related('usuario').order_by('-fecha_emision')[:20]

        context = {
            'es_trabajador': True,
            'contrataciones': contrataciones,
            'clientes': Cliente.objects.all(),
            'documentos_legaltech': documentos_legaltech,
            'query': query,
            'filtro_estado': filtro_estado,
            'hoy': hoy
        }
        
    else:

        cliente = Cliente.objects.filter(email=request.user.email).first()
        mis_contrataciones = Contratacion.objects.filter(
            cliente__email=request.user.email
        ).select_related('plan').order_by('-fecha_inicio')
        
        mis_contrataciones = Contratacion.objects.filter(
            cliente__email=request.user.email
        ).select_related('plan').order_by('-fecha_inicio')

        for c in mis_contrataciones:
            c.dias_restantes = (c.fecha_vencimiento - hoy).days if c.fecha_vencimiento else 0

        documentos_legaltech = DocumentoLegalTech.objects.filter(
            usuario=request.user
        ).order_by('-fecha_emision')

        context = {
            'es_trabajador': False,
            'cliente': cliente,
            'contrataciones': mis_contrataciones,
            'documentos_legaltech': documentos_legaltech,
            'hoy': hoy
        }

    return render(request, 'servicios/perfil.html', context)


# ==========================================
# 3. AUTENTICACIÓN Y REGISTRO
# ==========================================

def registro_view(request):
    if request.user.is_authenticated:
        return redirect('perfil')

    if request.method == 'POST':
        form = RegistroClienteForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data['username'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['razon_social'][:30],
                    is_staff=False
                )
                grupo_cliente, _ = Group.objects.get_or_create(name='Cliente')
                user.groups.add(grupo_cliente)

                cliente = form.save(commit=False)
                cliente.comuna = cliente.comuna or 'Santiago'
                cliente.region = cliente.region or 'Metropolitana'
                cliente.save()

            login(request, user)
            return redirect('perfil')
    else:
        form = RegistroClienteForm()
    return render(request, 'servicios/registro.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('perfil')

    error_message = None
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('perfil')
        else:
            error_message = "Usuario o contraseña incorrectos."
    else:
        form = AuthenticationForm()

    return render(request, 'servicios/login.html', {'form': form, 'error_message': error_message})


def logout_view(request):
    django_logout(request)
    return redirect('home')


# ==========================================
# 4. CRM Y ADMINISTRACIÓN STAFF
# ==========================================

@staff_member_required
def crm_dashboard_view(request):
    query = request.GET.get('q', '').strip()
    estado_filtro = request.GET.get('estado', '')

    contrataciones = Contratacion.objects.all().select_related('cliente', 'plan').order_by('-fecha_inicio')

    if query:
        contrataciones = contrataciones.filter(
            Q(cliente__rut__icontains=query) |
            Q(cliente__razon_social__icontains=query) |
            Q(cliente__email__icontains=query)
        )

    if estado_filtro:
        contrataciones = contrataciones.filter(estado=estado_filtro)

    hoy = date.today()
    for c in contrataciones:
        c.dias_restantes = (c.fecha_vencimiento - hoy).days if c.fecha_vencimiento else 0

    context = {
        'contrataciones': contrataciones,
        'query': query,
        'estado_filtro': estado_filtro,
        'total_clientes': Cliente.objects.count(),
        'total_activas': Contratacion.objects.filter(estado='ACTIVO').count(),
    }

    return render(request, 'servicios/crm_dashboard.html', context)


@staff_member_required
@require_POST
def cambiar_estado_contratacion(request, contratacion_id):
    try:
        data = json.loads(request.body)
        nuevo_estado = data.get('estado')

        contratacion = Contratacion.objects.get(id=contratacion_id)
        contratacion.estado = nuevo_estado
        contratacion.save()

        return JsonResponse({'status': 'success', 'mensaje': f'Estado actualizado a {nuevo_estado}'})
    except Contratacion.DoesNotExist:
        return JsonResponse({'status': 'error', 'mensaje': 'Contratación no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'status': 'error', 'mensaje': str(e)}, status=500)


# ==========================================
# 5. GENERACIÓN Y DESCARGA DE COMPROBANTE PDF
# ==========================================

@login_required
def descargar_comprobante_pdf(request, contratacion_id):
    try:
        if request.user.is_staff:
            contratacion = Contratacion.objects.get(id=contratacion_id)
        else:
            contratacion = Contratacion.objects.get(id=contratacion_id, cliente__email=request.user.email)
    except Contratacion.DoesNotExist:
        raise Http404("El comprobante solicitado no existe o no tienes permiso para verlo.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )

    story = []
    styles = getSampleStyleSheet()

    titulo_style = ParagraphStyle(
        'TituloPDF',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A")
    )
    subtitulo_style = ParagraphStyle(
        'SubtituloPDF',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor("#64748B")
    )
    seccion_style = ParagraphStyle(
        'SeccionPDF',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#059669"),
        spaceBefore=15,
        spaceAfter=5
    )

    story.append(Paragraph("EASY OFFICE", titulo_style))
    story.append(Paragraph("Comprobante Oficial de Contratación de Servicios", subtitulo_style))
    story.append(Spacer(1, 15))

    datos_resumen = [
        [
            Paragraph(f"<b>Folio Contrato:</b> #{contratacion.id}", styles['Normal']),
            Paragraph(f"<b>Fecha de Emisión:</b> {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal'])
        ],
        [
            Paragraph(f"<b>Estado:</b> <font color='#059669'><b>{contratacion.estado}</b></font>", styles['Normal']),
            Paragraph("<b>Vigencia:</b> 1 Año", styles['Normal'])
        ]
    ]
    t_resumen = Table(datos_resumen, colWidths=[260, 260])
    t_resumen.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_resumen)
    story.append(Spacer(1, 15))

    story.append(Paragraph("Detalles del Cliente", seccion_style))
    cliente = contratacion.cliente
    datos_cliente = [
        [Paragraph("<b>Razón Social / Nombre:</b>", styles['Normal']), Paragraph(str(cliente.razon_social), styles['Normal'])],
        [Paragraph("<b>RUT:</b>", styles['Normal']), Paragraph(str(cliente.rut), styles['Normal'])],
        [Paragraph("<b>Email de Contacto:</b>", styles['Normal']), Paragraph(str(cliente.email), styles['Normal'])],
    ]
    t_cliente = Table(datos_cliente, colWidths=[150, 370])
    t_cliente.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_cliente)
    story.append(Spacer(1, 15))

    story.append(Paragraph("Detalles del Plan y Pago", seccion_style))
    plan = contratacion.plan
    monto_fmt = f"${contratacion.monto_pagado:,.0f} CLP" if contratacion.monto_pagado else "$0 CLP"
    
    datos_plan = [
        [Paragraph("<b>Plan</b>", styles['Normal']), Paragraph("<b>Periodo</b>", styles['Normal']), Paragraph("<b>Monto Pagado</b>", styles['Normal'])],
        [
            Paragraph(str(plan.nombre), styles['Normal']),
            Paragraph(f"{contratacion.fecha_inicio.strftime('%d/%m/%Y')} al {contratacion.fecha_vencimiento.strftime('%d/%m/%Y')}", styles['Normal']),
            Paragraph(monto_fmt, styles['Normal'])
        ]
    ]
    t_plan = Table(datos_plan, colWidths=[200, 200, 120])
    t_plan.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0F172A")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
    ]))
    story.append(t_plan)
    story.append(Spacer(1, 25))

    nota_legal = Paragraph(
        "Este documento sirve como comprobante oficial de la recepción de solicitud de contratación en la plataforma Easy Office.",
        ParagraphStyle('NotaPDF', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor("#94A3B8"))
    )
    story.append(nota_legal)

    doc.build(story)
    buffer.seek(0)

    filename = f"Comprobante_EasyOffice_Folio_{contratacion.id}.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename)

# ==========================================
# 6. GENERADOR DE DOCUMENTOS LEGALTECH
# ==========================================

# Asegúrate de importar el modelo al inicio del views.py:
from .models import Plan, Contratacion, Cliente, DocumentoLegalTech

@login_required
def generar_documento_legaltech_pdf(request, tipo_doc):
    # 1. Registrar la generación en BD y obtener folio único
    params = request.GET.dict()
    doc_registro = DocumentoLegalTech.objects.create(
        usuario=request.user,
        tipo_documento=tipo_doc,
        datos_json=params
    )

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    
    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        alignment=TA_CENTER,
        spaceAfter=15
    )
    
    style_body = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        alignment=TA_JUSTIFY,
        spaceAfter=10
    )

    style_folio = ParagraphStyle(
        'DocFolio',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#4B5563'),
        alignment=TA_CENTER
    )

    story = []

    # --- PLANTILLAS ---
    if tipo_doc == 'poder_simple':
        empresa_nombre = params.get('empresa_nombre', request.user.username)
        empresa_rut = params.get('empresa_rut', '77.123.456-7')
        rep_nombre = params.get('rep_nombre', request.user.get_full_name() or request.user.username)
        rep_rut = params.get('rep_rut', '12.345.678-9')
        apoderado_nombre = params.get('apoderado_nombre', 'PEDRO SOTO MENDOZA')
        apoderado_rut = params.get('apoderado_rut', '15.987.654-3')
        fecha_str = timezone.now().strftime('%d DE %B DE %Y').upper()

        story.append(Paragraph("PODER SIMPLE - REPRESENTACIÓN SII", style_title))
        story.append(Spacer(1, 15))
        
        texto_comparecencia = f"""
        En Santiago, a {fecha_str}, don/doña <b>{rep_nombre}</b>, cédula nacional de identidad 
        N.º <b>{rep_rut}</b>, en representación legal de la sociedad <b>{empresa_nombre}</b>, 
        R.U.T. N.º <b>{empresa_rut}</b>, otorga poder amplio y suficiente a don/doña 
        <b>{apoderado_nombre}</b>, cédula nacional de identidad N.º <b>{apoderado_rut}</b>, 
        para que actúe en nombre y representación de la empresa ante el <b>Servicio de Impuestos Internos (SII)</b>.
        """
        story.append(Paragraph(texto_comparecencia, style_body))
        
        texto_facultades = """
        El apoderado queda facultado para realizar trámites de inicio de actividades, verificación de actividad económica, 
        peticiones administrativas, obtención de e-RUT, retiro de documentación y cualquier otra gestión requerida por la representación.
        """
        story.append(Paragraph(texto_facultades, style_body))
        story.append(Spacer(1, 30))
        
        data_firma = [
            ["_____________________________________"],
            [f"<b>{rep_nombre}</b>"],
            [f"R.U.T. {rep_rut}"],
            [f"p.p. {empresa_nombre}"]
        ]
        table_firma = Table([[Paragraph(cell[0], style_title)] for cell in data_firma], colWidths=[400])
        table_firma.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
        story.append(table_firma)

    elif tipo_doc == 'acuerdo_accionistas':
        empresa_nombre = params.get('empresa_nombre', request.user.username)
        empresa_rut = params.get('empresa_rut', '77.123.456-7')
        accionista_1 = params.get('accionista_1', request.user.get_full_name() or request.user.username)
        accionista_1_rut = params.get('accionista_1_rut', '12.345.678-9')
        accionista_2 = params.get('accionista_2', 'CARLOS GÓMEZ SILVA')
        accionista_2_rut = params.get('accionista_2_rut', '14.567.890-1')
        materia_acuerdo = params.get('materia', 'Aumento de Capital y Modificación de Representación Legal')
        fecha_str = timezone.now().strftime('%d DE %B DE %Y').upper()

        story.append(Paragraph("ACTA DE ACUERDO EXTRAORDINARIO DE ACCIONISTAS", style_title))
        story.append(Spacer(1, 10))

        cuerpo = f"""
        En Santiago, a {fecha_str}, con la asistencia de los accionistas de la sociedad <b>{empresa_nombre}</b>, 
        R.U.T. N.º <b>{empresa_rut}</b>: don/doña <b>{accionista_1}</b>, C.I. N.º <b>{accionista_1_rut}</b>; 
        y don/doña <b>{accionista_2}</b>, C.I. N.º <b>{accionista_2_rut}</b>, constituyendo el 100% del capital social suscrito y pagado, 
        se acuerda por unanimidad lo siguiente:
        <br/><br/>
        <b>PRIMERO: MATERIA DEL ACUERDO.</b> Los accionistas convienen en aprobar: <b>{materia_acuerdo}</b>.
        <br/><br/>
        <b>SEGUNDO: FACULTADES AL PORTADOR.</b> Se faculta al portador de una copia autorizada del presente documento 
        para requerir las anotaciones, inscripciones y legalizaciones notariales a que hubiere lugar.
        """
        story.append(Paragraph(cuerpo, style_body))
        story.append(Spacer(1, 30))

        data_firmas = [
            ["_______________________", "_______________________"],
            [f"<b>{accionista_1}</b>", f"<b>{accionista_2}</b>"],
            [f"R.U.T. {accionista_1_rut}", f"R.U.T. {accionista_2_rut}"]
        ]
        table_firmas = Table([[Paragraph(cell[0], style_body), Paragraph(cell[1], style_body)] for cell in data_firmas], colWidths=[220, 220])
        table_firmas.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER')]))
        story.append(table_firmas)

    elif tipo_doc == 'arriendo_vehiculo':
        arrendador = params.get('arrendador', 'EASY OFFICE RENTALS SpA')
        arrendador_rut = params.get('arrendador_rut', '77.999.888-1')
        arrendatario = params.get('arrendatario', request.user.username)
        arrendatario_rut = params.get('arrendatario_rut', '76.543.210-K')
        marca = params.get('marca', 'TOYOTA')
        modelo = params.get('modelo', 'YARIS')
        patente = params.get('patente', 'ABCD-12')
        monto = params.get('monto', '350.000')

        story.append(Paragraph("CONTRATO DE ARRENDAMIENTO DE VEHÍCULO", style_title))
        story.append(Spacer(1, 10))
        
        cuerpo = f"""
        En Santiago, comparecen: por una parte, <b>{arrendador}</b>, RUT N.º <b>{arrendador_rut}</b>, en adelante el "Arrendador"; 
        y por otra parte, <b>{arrendatario}</b>, RUT N.º <b>{arrendatario_rut}</b>, en adelante la "Arrendataria", quienes acuerdan:
        <br/><br/>
        <b>PRIMERO: VEHÍCULO.</b> El Arrendador entrega en arrendamiento el vehículo Marca <b>{marca}</b>, Modelo <b>{modelo}</b>, Patente <b>{patente}</b>.
        <br/><br/>
        <b>SEGUNDO: RENTA.</b> La renta mensual de arrendamiento será de <b>${monto}</b> pesos chilenos, pagaderos dentro de los primeros 5 días de cada mes.
        """
        story.append(Paragraph(cuerpo, style_body))

    elif tipo_doc == 'arriendo_estacionamiento':
        arrendador = params.get('arrendador', 'EDIFICIO EASY OFFICE')
        arrendador_rut = params.get('arrendador_rut', '77.888.999-0')
        arrendatario = params.get('arrendatario', request.user.username)
        arrendatario_rut = params.get('arrendatario_rut', '76.543.210-K')
        nro_estacionamiento = params.get('nro_estacionamiento', 'E-12')
        direccion = params.get('direccion', 'Av. Apoquindo 4500, Las Condes, Santiago')
        monto = params.get('monto', '80.000')

        story.append(Paragraph("CONTRATO DE ARRIENDO DE ESTACIONAMIENTO", style_title))
        story.append(Spacer(1, 10))

        cuerpo = f"""
        En Santiago, comparecen: <b>{arrendador}</b>, RUT N.º <b>{arrendador_rut}</b> (el "Arrendador"); 
        y <b>{arrendatario}</b>, RUT N.º <b>{arrendatario_rut}</b> (el "Arrendatario"), conviniendo lo siguiente:
        <br/><br/>
        <b>PRIMERO: INMUEBLE.</b> El Arrendador cede el uso del estacionamiento N.º <b>{nro_estacionamiento}</b>, ubicado en el subterráneo de <b>{direccion}</b>.
        <br/><br/>
        <b>SEGUNDO: CANON DE ARRIENDO.</b> El precio del arriendo mensual es de <b>${monto}</b> pesos chilenos.
        <br/><br/>
        <b>TERCERO: USO.</b> El sitio se destinará exclusivamente al estacionamiento de un vehículo motorizado particular, respetando el reglamento interno del inmueble.
        """
        story.append(Paragraph(cuerpo, style_body))

    else:
        raise Http404("Tipo de documento no válido")

  # --- SELLO Y CERTIFICACIÓN FEA + NOTARÍA (PIE DE PÁGINA) ---
    story.append(Spacer(1, 20))
    url_validacion = request.build_absolute_uri(reverse('validar_folio', args=[doc_registro.folio]))

    sello_fea_html = f"""
    <hr/>
    <br/>
    <b>DOCUMENTO FIRMADO MEDIANTE FIRMA ELECTRÓNICA AVANZADA (FEA)</b><br/>
    <b>Folio Único:</b> {doc_registro.folio} | <b>Estado:</b> {doc_registro.get_estado_firma_display().upper()}<br/>
    <b>Hash FEA (SHA-256):</b> <font face="Courier">{doc_registro.hash_firma}</font><br/>
    <b>Coordinación Notarial:</b> {doc_registro.notaria_asignada}<br/>
    <b>Firmante:</b> {request.user.get_full_name() or request.user.username} ({request.user.email})<br/>
    <b>Verificación en Línea:</b> {url_validacion}
    """
    story.append(Paragraph(sello_fea_html, style_folio))