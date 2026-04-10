from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, Avg, Q
from django.core.mail import send_mail, get_connection
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from datetime import datetime
import json
import requests
import logging
import traceback
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
import io
import os
import zipfile
from PIL import Image
from .models import (
    Checklist, Profile, AlertEmail, Condutor, Veiculo, 
    MaintenanceTruck, MaintenanceTrailer, ChecklistForklift, 
    MaintenanceSchedule, AlertTelegram, MaintenanceStatusLog, 
    EmailConfig, TelegramConfig, ChecklistPhoto, TelegramToken
)
from webpush import send_group_notification, send_user_notification
from .constants import TRUCK_MAINTENANCE_ITEMS, TRAILER_MAINTENANCE_ITEMS, PORTARIA_ITEMS, FORKLIFT_ITEMS

# --- HELPER FUNCTIONS ---

def _process_and_save_photo(obj, photo_file):
    """Resizes, compresses and saves a photo for a given object"""
    try:
        img = Image.open(photo_file)
        
        # Convert RGBA to RGB if necessary
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # Resize if too large (Max 1200px width/height)
        max_size = (1200, 1200)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Compress
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=75, optimize=True)
        output.seek(0)
        
        # Create ChecklistPhoto
        ct = ContentType.objects.get_for_model(obj)
        photo_obj = ChecklistPhoto(
            content_type=ct,
            object_id=obj.id
        )
        # Use simple name
        photo_obj.file.save('photo.jpg', ContentFile(output.read()), save=True)
        return True
    except Exception as e:
        print(f"Erro ao processar imagem: {e}")
        return False

def _get_email_connection():
    """Returns a dynamic SMTP connection based on EmailConfig from database"""
    config = EmailConfig.objects.first()
    if not config:
        return None, settings.DEFAULT_FROM_EMAIL
        
    password = config.get_decrypted_password()
    connection = get_connection(
        host=config.host,
        port=config.port,
        username=config.user,
        password=password,
        use_tls=config.use_tls,
        use_ssl=config.use_ssl,
        timeout=10
    )
    return connection, config.default_from or settings.DEFAULT_FROM_EMAIL

def _send_telegram_message(message, request=None):
    """
    Sends a message to all active contacts in the AlertTelegram model
    using the bot token from the database. Includes retries for proxy/network issues.
    """
    import time, os
    config = TelegramConfig.objects.first()
    if not config:
        print("Telegram configuration missing in database.")
        if request: messages.warning(request, "Configuração do Telegram ausente. Alerta não enviado.")
        return

    bot_token = config.get_decrypted_token()
    if not bot_token:
        print("Telegram bot token is empty.")
        if request: messages.warning(request, "Token do Telegram vazio. Alerta não enviado.")
        return

    from django.contrib.auth.models import User
    proxies = {"http": "http://proxy.server:3128", "https": "http://proxy.server:3128"} if os.environ.get('PYTHONANYWHERE_SITE') else None
    
    contacts = User.objects.exclude(profile__telegram_chat_id__isnull=True).exclude(profile__telegram_chat_id__exact='')
    
    for contact in contacts:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': contact.profile.telegram_chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        
        for attempt in range(3):
            try:
                response = requests.post(url, json=payload, timeout=10, proxies=proxies)
                if response.status_code == 200:
                    break
                elif response.status_code in [502, 503, 504]:
                    time.sleep(1)
                else:
                    print(f"Erro Telegram ({contact.profile.telegram_chat_id}): {response.status_code} - {response.text}")
                    if request: messages.warning(request, f"Erro Telegram: Código {response.status_code}")
                    break
            except Exception as e:
                name = contact.get_full_name() or contact.username
                print(f"Erro ao enviar para {name} (Tentativa {attempt+1}): {e}")
                if attempt == 2 and request: messages.warning(request, f"Falha na rede ao conectar no Telegram (Possível bloqueio de Proxy/Firewall).")
                time.sleep(1)

def _send_single_telegram_message(chat_id, message):
    """Sends a message to a specific chat_id with retry logic and detailed error return"""
    import time, os
    config = TelegramConfig.objects.first()
    if not config:
        return False, "Configuração do bot não encontrada."
    
    bot_token = config.get_decrypted_token()
    if not bot_token:
        return False, "Token do bot não configurado."
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML'
    }
    
    proxies = {"http": "http://proxy.server:3128", "https": "http://proxy.server:3128"} if os.environ.get('PYTHONANYWHERE_SITE') else None
    last_error = "Erro desconhecido"
    
    for attempt in range(3):
        try:
            response = requests.post(url, json=payload, timeout=10, proxies=proxies)
            if response.status_code == 200:
                return True, "Mensagem enviada com sucesso!"
            
            # Extract detailed error from Telegram
            try:
                error_data = response.json()
                desc = error_data.get('description', 'Erro sem descrição')
            except:
                desc = f"Servidor/Proxy retornou Erro {response.status_code}"
            
            if response.status_code == 403:
                return False, f"O bot foi bloqueado pelo usuário (Erro 403: {desc})"
            elif response.status_code == 400:
                return False, f"ID de Chat inválido ou erro no formato da mensagem (Erro 400: {desc})"
            elif response.status_code in [502, 503, 504]:
                last_error = f"Instabilidade no Servidor/Proxy (Erro {response.status_code})"
                time.sleep(1.5)
                continue
            else:
                return False, f"Erro do Telegram: {response.status_code} - {desc}"
                
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.ProxyError) as e:
            last_error = f"Erro de Conexão/Proxy (PythonAnywhere): {str(e)}"
            time.sleep(1)
        except Exception as e:
            last_error = f"Erro inesperado: {str(e)}"
            time.sleep(1)
            
    return False, f"Falha após 3 tentativas. Motivo: {last_error}"

def _send_portaria_anomaly_email(checklist, request=None):
    """Standalone function to send Portaria anomaly alerts (replaces legacy ViewSet method)"""
    emails = list(AlertEmail.objects.filter(category='PORTARIA').values_list('email', flat=True))
    if not emails:
        return

    subject = f"⚠️ ALERTA DE ANOMALIA - Veículo {checklist.placa_cavalo.placa}"
    
    # Resolve items to find NCs (Nao Conforme)
    items_nc = []
    for item in PORTARIA_ITEMS:
        val = getattr(checklist, item['id'], 'NA')
        if val == 'NAO':
            items_nc.append(item)

    # Build context for HTML email
    site_url = request.build_absolute_uri('/')[:-1] if request else 'http://localhost:8001'
    context = {
        'checklist': checklist,
        'items_nc': items_nc,
        'site_url': site_url,
        'now': datetime.now()
    }
    
    html_message = render_to_string('emails/portaria_anomaly_email.html', context)
    plain_message = strip_tags(html_message)
    
    connection, from_email = _get_email_connection()
    try:
        send_mail(subject, plain_message, from_email, emails, html_message=html_message, fail_silently=False, connection=connection)
    except Exception as e:
        print(f"Erro ao enviar e-mail Portaria: {e}")

    # Notificação Telegram
    msg = f"<b>⚠️ ALERTA DE ANOMALIA: PORTARIA</b>\n"
    msg += f"<i>Central Operacional - Intalog</i>\n\n"
    msg += f"Veículo: {checklist.placa_cavalo.placa}\n"
    msg += f"Porteiro: {checklist.porteiro.username if checklist.porteiro else 'S/N'}\n"
    msg += f"Anomalias: {checklist.anomalias}\n\n"
    msg += f"🔗 Detalhes: {site_url}/portaria/{checklist.id}/"
    _send_telegram_message(msg)

def _send_maintenance_alert(instance, veiculo_tipo, request=None):
    """Standalone function to send Maintenance alerts"""
    emails = list(AlertEmail.objects.filter(category='MANUTENCAO').values_list('email', flat=True))
    if not emails: return
    
    subject = f"🛠️ MANUTENÇÃO: ANOMALIA DETECTADA - {veiculo_tipo} {instance.veiculo.placa}"
    
    from .constants import TRUCK_MAINTENANCE_ITEMS, TRAILER_MAINTENANCE_ITEMS
    items_def = TRUCK_MAINTENANCE_ITEMS if veiculo_tipo == "CAMINHÃO" else TRAILER_MAINTENANCE_ITEMS
    items_nc = []
    for item in items_def:
        val = getattr(instance, item['id'], 'NA')
        if val == 'NAO':
            items_nc.append(item)

    site_url = request.build_absolute_uri('/')[:-1] if request else 'http://localhost:8001'
    context = {
        'instance': instance,
        'veiculo_tipo': veiculo_tipo,
        'items_nc': items_nc,
        'site_url': site_url,
        'm_type': 'truck' if veiculo_tipo == "CAMINHÃO" else 'trailer',
        'now': datetime.now()
    }
    
    html_message = render_to_string('emails/maintenance_anomaly_email.html', context)
    plain_message = strip_tags(html_message)

    connection, from_email = _get_email_connection()
    try:
        send_mail(subject, plain_message, from_email, emails, html_message=html_message, fail_silently=False, connection=connection)
    except Exception as e:
        print(f"Erro ao enviar e-mail Manutenção: {e}")
        if request: messages.warning(request, "Falha de rede ao conectar no SMTP do E-mail. Tente verificar o provedor na Configuração Global.")

    # Notificação Telegram
    msg = f"<b>🚨🛠️ ANOMALIA: MANUTENÇÃO ({veiculo_tipo})</b>\n"
    msg += f"<i>Equipe de Manutenção - Intalog</i>\n\n"
    msg += f"Veículo: {instance.veiculo.placa}\n"
    msg += f"Mecânico: {instance.responsavel.username if instance.responsavel else 'S/N'}\n"
    msg += f"Observações: {instance.observacoes}\n\n"
    msg += f"🔗 Detalhes: {site_url}/manutencao/{'truck' if veiculo_tipo == 'CAMINHÃO' else 'trailer'}/{instance.id}/"
    _send_telegram_message(msg, request=request)

def _send_forklift_anomaly_email(instance, request=None):
    """Standalone function to send Forklift anomaly alerts"""
    emails = list(AlertEmail.objects.filter(category='MANUTENCAO').values_list('email', flat=True))
    if not emails: return
    
    subject = f"🚜 EMPILHADEIRA: ANOMALIA DETECTADA - {instance.get_tipo_equipamento_display()}"
    
    items_nc = []
    for item in FORKLIFT_ITEMS:
        val = getattr(instance, item['id'], 'NA')
        if val == 'NAO':
            items_nc.append(item)

    site_url = request.build_absolute_uri('/')[:-1] if request else 'http://localhost:8001'
    
    # Format duration for email
    duration_str = "-"
    if instance.tempo_execucao:
        minutes = instance.tempo_execucao // 60
        seconds = instance.tempo_execucao % 60
        duration_str = f"{minutes:02d}:{seconds:02d}"

    context = {
        'instance': instance,
        'items_nc': items_nc,
        'site_url': site_url,
        'duration_str': duration_str,
        'now': datetime.now()
    }
    
    html_message = render_to_string('emails/forklift_anomaly_email.html', context)
    plain_message = strip_tags(html_message)

    connection, from_email = _get_email_connection()
    try:
        send_mail(subject, plain_message, from_email, emails, html_message=html_message, fail_silently=False, connection=connection)
    except Exception as e:
        print(f"Erro ao enviar e-mail Empilhadeira: {e}")

def _send_schedule_alerts(schedule, request=None):
    """Send Email and WhatsApp alerts for new maintenance schedules"""
    # 1. Email Alerts
    emails = list(AlertEmail.objects.filter(category='AGENDA').values_list('email', flat=True))
    if emails:
        subject = f"🛠️ AGENDAMENTO: MANUTENÇÃO - {schedule.veiculo.placa}"
        site_url = request.build_absolute_uri('/')[:-1] if request else 'http://localhost:8001'
        context = {
            'schedule': schedule,
            'site_url': site_url,
            'now': datetime.now()
        }
        html_message = render_to_string('emails/schedule_alert_email.html', context)
        plain_message = strip_tags(html_message)
        
        connection, from_email = _get_email_connection()
        try:
            send_mail(subject, plain_message, from_email, emails, html_message=html_message, fail_silently=False, connection=connection)
        except Exception as e:
            print(f"Erro ao enviar e-mail Agenda: {e}")
            if request: messages.warning(request, "Aviso: O agendamento foi salvo, porém a tentativa de envio de E-mail de Alerta falhou por erro de conexão SMTP.")

    # 2. Telegram Alerts
    msg = f"<b>🚛 NOVO AGENDAMENTO DE MANUTENÇÃO</b>\n"
    msg += f"<i>Central Operacional Check-up & Manutenção - Intalog</i>\n\n"
    msg += f"Placa: {schedule.veiculo.placa}\n"
    msg += f"Início: {schedule.data_paralizacao.strftime('%d/%m/%Y %H:%M')}\n"
    msg += f"Previsão: {schedule.data_previsao_liberacao.strftime('%d/%m/%Y %H:%M')}\n"
    msg += f"Descrição: {schedule.descricao}\n\n"
    msg += f"🔗 Agenda: {site_url}/manutencao/agenda/"
    
    _send_telegram_message(msg, request=request)

def _send_push_to_roles(roles, title, message, url='/'):
    """Sends a push notification to all users with specific roles"""
    from django.contrib.auth.models import User
    from webpush import send_user_notification
    users = User.objects.filter(profile__role__in=roles)
    payload = {
        "title": title,
        "body": message,
        "url": url,
        "icon": "/static/img/pwa-icon.png"
    }
    for user in users:
        try:
            send_user_notification(user=user, payload=payload, ttl=1000)
        except Exception as e:
            print(f"Erro ao enviar push para {user.username}: {e}")

def _notify_new_checklist_push(checklist, type_label):
    """Notify managers about a new checklist via PWA Push"""
    roles_to_notify = ['GESTOR', 'ADMIN', 'SUPERUSER']
    title = f"Novo Checklist: {type_label}"
    
    # Resolve vehicle and user
    veiculo_placa = "S/N"
    if hasattr(checklist, 'placa_cavalo') and checklist.placa_cavalo:
        veiculo_placa = checklist.placa_cavalo.placa
    elif hasattr(checklist, 'veiculo') and checklist.veiculo:
        veiculo_placa = checklist.veiculo.placa
        
    usuario_nome = "Sistema"
    if hasattr(checklist, 'porteiro') and checklist.porteiro:
        usuario_nome = checklist.porteiro.username
    elif hasattr(checklist, 'responsavel') and checklist.responsavel:
        usuario_nome = checklist.responsavel.username

    message = f"Veículo {veiculo_placa} registrado por {usuario_nome}."
    
    url = "/"
    if type_label == "Portaria":
        url = f"/portaria/{checklist.id}/"
    elif type_label == "Caminhão":
        url = f"/manutencao/truck/{checklist.id}/"
    elif type_label == "Carreta":
        url = f"/manutencao/trailer/{checklist.id}/"
    elif type_label == "Empilhadeira":
        url = f"/forklift/{checklist.id}/"

    from django.contrib.auth.models import User
    _send_push_to_roles(roles_to_notify, title, message, url)

@login_required
def generate_telegram_token(request):
    """Gera um token UUID para deep linking com o Telegram e redireciona o usuário."""
    # Remover tokens antigos do usuário para evitar lixo
    TelegramToken.objects.filter(user=request.user).delete()
    
    # Criar novo token
    token_obj = TelegramToken.objects.create(user=request.user)
    
    # Obter link do bot do banco de dados
    config = TelegramConfig.objects.first()
    bot_link = config.bot_link if config and config.bot_link else "https://t.me/PortariaWeb_bot"
    
    # Adicionar o parâmetro start=TOKEN (sem espaços)
    redirect_url = f"{bot_link}?start={token_obj.token}"
    
    return redirect(redirect_url)

@csrf_exempt
def telegram_webhook(request):
    """Recebe mensagens do Telegram e processa o comando /start <token>."""
    if request.method != 'POST':
        return JsonResponse({'status': 'invalid method'}, status=405)
        
    try:
        data = json.loads(request.body)
        message = data.get('message', {})
        text = message.get('text', '')
        chat_id = message.get('chat', {}).get('id')
        
        # O Deep Linking do Telegram envia "/start TOKEN"
        if text.startswith('/start ') and chat_id:
            token_str = text.split(' ')[1]
            try:
                # Buscar o token no banco
                token_obj = TelegramToken.objects.get(token=token_str, used=False)
                
                # Validar expiração (10 minutos)
                if not token_obj.is_expired():
                    # Vincular ao perfil do usuário
                    profile = token_obj.user.profile
                    profile.telegram_chat_id = str(chat_id)
                    profile.save()
                    
                    # Marcar token como usado
                    token_obj.used = True
                    token_obj.save()
                    
                    # Enviar mensagem de confirmação
                    confirmation_text = (
                        "🚀 <b>Vinculação Concluída!</b>\n\n"
                        f"Olá {token_obj.user.first_name or token_obj.user.username}, seu perfil foi vinculado com sucesso.\n"
                        "A partir de agora, você receberá alertas críticos diretamente aqui."
                    )
                    _send_single_telegram_message(chat_id, confirmation_text)
                    
                    return JsonResponse({'status': 'linked success'})
                else:
                    _send_single_telegram_message(chat_id, "⚠️ O token de ativação expirou. Por favor, gere um novo no site.")
                    return JsonResponse({'status': 'token expired'})
                    
            except (TelegramToken.DoesNotExist, ValueError):
                _send_single_telegram_message(chat_id, "❌ Token inválido ou já utilizado.")
                return JsonResponse({'status': 'invalid token'})
                
        return JsonResponse({'status': 'ignored'})
        
    except Exception as e:
        print(f"Erro no Webhook Telegram: {e}")
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

# --- DASHBOARD SERIALIZATION HELPERS ---

def _serialize_checklist(obj):
    return {
        'id': obj.id,
        'data_criacao': obj.data_criacao,
        'anomalias': obj.anomalias,
        'porteiro_name': obj.porteiro.get_full_name() or obj.porteiro.username if obj.porteiro else 'S/N',
        'placa_cavalo_detail': {'placa': obj.placa_cavalo.placa} if obj.placa_cavalo else None,
        'nome_motorista_detail': {'nome': obj.nome_motorista.nome} if obj.nome_motorista else None,
        'has_nc': obj.has_nc,
        'is_resolved': obj.is_resolved,
    }

def _serialize_maintenance(obj, is_truck=True):
    data = {
        'id': obj.id,
        'data_criacao': obj.data_criacao,
        'observacoes': obj.observacoes,
        'veiculo_detail': {'placa': obj.veiculo.placa} if obj.veiculo else None,
        'motorista_detail': {'nome': obj.motorista.nome} if obj.motorista else None,
        'responsavel_name': obj.responsavel.get_full_name() or obj.responsavel.username if obj.responsavel else 'S/N',
        'has_nc': obj.has_nc,
        'is_resolved': obj.is_resolved,
    }
    # Include all items
    items = TRUCK_MAINTENANCE_ITEMS if is_truck else TRAILER_MAINTENANCE_ITEMS
    for item in items:
        data[item['id']] = getattr(obj, item['id'], 'NA')
    return data

def _serialize_forklift(obj):
    data = {
        'id': obj.id,
        'data_criacao': obj.data_criacao,
        'observacoes': obj.observacoes,
        'tipo_equipamento': obj.tipo_equipamento,
        'tipo_equipamento_display': obj.get_tipo_equipamento_display(),
        'operador_detail': {'nome': obj.operador.nome} if obj.operador else None,
        'responsavel_name': obj.responsavel.get_full_name() or obj.responsavel.username if obj.responsavel else 'S/N',
        'tempo_execucao': obj.tempo_execucao,
        'has_nc': obj.has_nc,
        'is_resolved': obj.is_resolved,
    }
    for item in FORKLIFT_ITEMS:
        data[item['id']] = getattr(obj, item['id'], 'NA')
    return data

@login_required
def dashboard_view(request):
    if request.user.profile.role not in ['MANUTENCAO', 'GESTOR', 'ADMIN', 'SUPERUSER']:
        messages.error(request, "Acesso restrito aos Relatórios.")
        return redirect('home')
    # Fetch all data
    portaria_qs = Checklist.objects.select_related('placa_cavalo', 'nome_motorista', 'porteiro').order_by('-data_criacao')
    truck_qs = MaintenanceTruck.objects.select_related('veiculo', 'motorista', 'responsavel').order_by('-data_criacao')
    trailer_qs = MaintenanceTrailer.objects.select_related('veiculo', 'motorista', 'responsavel').order_by('-data_criacao')
    forklift_qs = ChecklistForklift.objects.select_related('operador', 'responsavel').order_by('-data_criacao')
    
    # Manual serialization for JSON consumption in dashboard.html
    portaria_data = [_serialize_checklist(c) for c in portaria_qs]
    truck_data = [_serialize_maintenance(t, True) for t in truck_qs]
    trailer_data = [_serialize_maintenance(t, False) for t in trailer_qs]
    forklift_data = [_serialize_forklift(f) for f in forklift_qs]
    
    # Calculate Averages (Seconds)
    avg_portaria = Checklist.objects.aggregate(Avg('tempo_execucao'))['tempo_execucao__avg'] or 0
    avg_truck = MaintenanceTruck.objects.aggregate(Avg('tempo_execucao'))['tempo_execucao__avg'] or 0
    avg_trailer = MaintenanceTrailer.objects.aggregate(Avg('tempo_execucao'))['tempo_execucao__avg'] or 0
    avg_forklift = ChecklistForklift.objects.aggregate(Avg('tempo_execucao'))['tempo_execucao__avg'] or 0

    context = {
        'portaria_json': json.dumps(portaria_data, cls=DjangoJSONEncoder),
        'truck_json': json.dumps(truck_data, cls=DjangoJSONEncoder),
        'trailer_json': json.dumps(trailer_data, cls=DjangoJSONEncoder),
        'forklift_json': json.dumps(forklift_data, cls=DjangoJSONEncoder),
        'averages': {
            'portaria': f"{int(avg_portaria // 60):02d}:{int(avg_portaria % 60):02d}",
            'truck': f"{int(avg_truck // 60):02d}:{int(avg_truck % 60):02d}",
            'trailer': f"{int(avg_trailer // 60):02d}:{int(avg_trailer % 60):02d}",
            'forklift': f"{int(avg_forklift // 60):02d}:{int(avg_forklift % 60):02d}",
        }
    }
    return render(request, 'dashboard.html', context)

@login_required
def portaria_create_view(request):
    if request.user.profile.role not in ['CONTROLADOR', 'ADMIN', 'SUPERUSER']:
        messages.error(request, "Acesso restrito ao Checklist de Portaria.")
        return redirect('home')
    if request.method == 'POST':
        try:
            # Capturar IDs numéricos
            placa_cavalo_id = request.POST.get('placa_cavalo')
            nome_motorista_id = request.POST.get('nome_motorista')
            placa_carreta_01_id = request.POST.get('placa_carreta_01') or None
            placa_carreta_02_id = request.POST.get('placa_carreta_02') or None
            
            # Buscar instancias
            placa_cavalo = Veiculo.objects.get(id=placa_cavalo_id)
            nome_motorista = Condutor.objects.get(id=nome_motorista_id)
            placa_carreta_01 = Veiculo.objects.get(id=placa_carreta_01_id) if placa_carreta_01_id else None
            placa_carreta_02 = Veiculo.objects.get(id=placa_carreta_02_id) if placa_carreta_02_id else None

            # Construir objeto
            checklist = Checklist(
                porteiro=request.user,
                placa_cavalo=placa_cavalo,
                nome_motorista=nome_motorista,
                placa_carreta_01=placa_carreta_01,
                placa_carreta_02=placa_carreta_02,
                doc_carreta_entregue=request.POST.get('doc_carreta_entregue') == 'on',
                
                # Eletrica
                eletrica_condicoes=request.POST.get('eletrica_condicoes', 'NA'),
                eletrica_seta=request.POST.get('eletrica_seta', 'NA'),
                eletrica_re=request.POST.get('eletrica_re', 'NA'),
                eletrica_freio=request.POST.get('eletrica_freio', 'NA'),
                eletrica_capas=request.POST.get('eletrica_capas', 'NA'),
                eletrica_placa=request.POST.get('eletrica_placa', 'NA'),

                # Mecanica
                mecanica_freios=request.POST.get('mecanica_freios', 'NA'),
                mecanica_conexoes=request.POST.get('mecanica_conexoes', 'NA'),
                mecanica_folga_quinta_roda=request.POST.get('mecanica_folga_quinta_roda', 'NA'),
                mecanica_suspensao=request.POST.get('mecanica_suspensao', 'NA'),
                mecanica_freio_estacionario=request.POST.get('mecanica_freio_estacionario', 'NA'),
                mecanica_travas_conteiner=request.POST.get('mecanica_travas_conteiner', 'NA'),
                mecanica_tampas_equipamento=request.POST.get('mecanica_tampas_equipamento', 'NA'),
                mecanica_tampas_estado=request.POST.get('mecanica_tampas_estado', 'NA'),

                # Pneus
                rodas_pneus_quantidade=request.POST.get('rodas_pneus_quantidade', 'NA'),
                rodas_pneus_reserva=request.POST.get('rodas_pneus_reserva', 'NA'),
                rodas_pneus_estado=request.POST.get('rodas_pneus_estado', 'NA'),
                rodas_pneus_cortes_bolhas=request.POST.get('rodas_pneus_cortes_bolhas', 'NA'),

                anomalias=request.POST.get('anomalias', ''),
                visto_responsavel_saida=request.POST.get('visto_responsavel_saida', ''),
                visto_motorista_saida=request.POST.get('visto_motorista_saida', ''),
                tempo_execucao=int(request.POST.get('tempo_execucao', 0)) or None,
            )
            checklist.save()

            # Handle Photos
            photos = request.FILES.getlist('photos')
            for f in photos:
                _process_and_save_photo(checklist, f)
            
            # Enviar e-mail de anomalia se existir
            if checklist.anomalias and checklist.anomalias.strip():
                _send_portaria_anomaly_email(checklist, request)
            
            # Notificação PWA Push
            _notify_new_checklist_push(checklist, "Portaria")
            
            messages.success(request, 'Checklist da Portaria salvo com sucesso!')
            return redirect('dashboard')
            
        except Exception as e:
            messages.error(request, f'Erro ao salvar: {str(e)}')
            
    context = {
        'condutores': Condutor.objects.all().order_by('nome'),
        'veiculos_cavalos': Veiculo.objects.filter(tipo='CAVALO').order_by('placa'),
        'veiculos_carretas': Veiculo.objects.filter(tipo='CARRETA').order_by('placa'),
    }
    return render(request, 'portaria_form.html', context)

from django.shortcuts import get_object_or_404

@login_required
def portaria_detail_view(request, pk):
    checklist = get_object_or_404(Checklist, pk=pk)
    return render(request, 'portaria_detail.html', {'checklist': checklist})

from .constants import TRUCK_MAINTENANCE_ITEMS, TRAILER_MAINTENANCE_ITEMS
from .models import MaintenanceTruck, MaintenanceTrailer

@login_required
def maintenance_create_view(request, m_type):
    if request.user.profile.role not in ['MANUTENCAO', 'ADMIN', 'SUPERUSER']:
        messages.error(request, "Acesso restrito à Manutenção.")
        return redirect('home')
    # m_type: 'truck' or 'trailer'
    is_truck = (m_type == 'truck')
    items = TRUCK_MAINTENANCE_ITEMS if is_truck else TRAILER_MAINTENANCE_ITEMS
    ModelClass = MaintenanceTruck if is_truck else MaintenanceTrailer
    tipo_veiculo = 'CAVALO' if is_truck else 'CARRETA'

    if request.method == 'POST':
        try:
            veiculo_id = request.POST.get('veiculo')
            motorista_id = request.POST.get('motorista')
            
            veiculo = get_object_or_404(Veiculo, id=veiculo_id)
            motorista = get_object_or_404(Condutor, id=motorista_id)
            
            # Instanciar modelo
            instance = ModelClass(
                responsavel=request.user,
                veiculo=veiculo,
                motorista=motorista,
                observacoes=request.POST.get('observacoes', ''),
                visto_responsavel=request.POST.get('visto_responsavel', ''),
                visto_motorista=request.POST.get('visto_motorista', ''),
                tempo_execucao=int(request.POST.get('tempo_execucao', 0)) or None,
            )
            
            if is_truck:
                instance.quilometragem = request.POST.get('quilometragem', '')

            # Atribuir checkboxes dinamicamente
            for item in items:
                field_value = request.POST.get(item['id'], 'NA')
                setattr(instance, item['id'], field_value)
                
            instance.save()
            
            # Send maintenance alert if NC items or observations exist
            has_nc = any(getattr(instance, item['id']) == 'NAO' for item in items)
            if has_nc or (instance.observacoes and instance.observacoes.strip()):
                alert_type = "CAMINHÃO" if is_truck else "CARRETA/BUG"
                _send_maintenance_alert(instance, alert_type, request)

            # Notificação PWA Push
            notification_type = "Caminhão" if is_truck else "Carreta"
            _notify_new_checklist_push(instance, notification_type)

            messages.success(request, f'Manutenção de {tipo_veiculo} salva com sucesso!')
            return redirect('dashboard')
            
        except Exception as e:
            messages.error(request, f'Erro ao salvar: {str(e)}')

    context = {
        'items': items,
        'm_type': m_type,
        'tipo_titulo': 'Caminhão/Cavalo' if is_truck else 'Carreta/Equipamento',
        'veiculos': Veiculo.objects.filter(tipo=tipo_veiculo).order_by('placa'),
        'condutores': Condutor.objects.all().order_by('nome'),
    }
    return render(request, 'maintenance_form.html', context)

@login_required
def maintenance_detail_view(request, m_type, pk):
    is_truck = (m_type == 'truck')
    ModelClass = MaintenanceTruck if is_truck else MaintenanceTrailer
    checklist = get_object_or_404(ModelClass, pk=pk)
    items = TRUCK_MAINTENANCE_ITEMS if is_truck else TRAILER_MAINTENANCE_ITEMS
    
    items_resolved = []
    for item in items:
        items_resolved.append({
            'label': item['label'],
            'value': getattr(checklist, item['id'], 'NA')
        })

    context = {
        'checklist': checklist,
        'm_type': m_type,
        'tipo_titulo': 'Caminhão/Cavalo' if is_truck else 'Carreta/Equipamento',
        'items_resolved': items_resolved,
    }
    return render(request, 'maintenance_detail.html', context)

@login_required
def forklift_create_view(request):
    if request.user.profile.role not in ['DEPOT', 'ADMIN', 'SUPERUSER']:
        messages.error(request, "Acesso restrito ao Checklist de Empilhadeira.")
        return redirect('home')
    items = FORKLIFT_ITEMS
    
    if request.method == 'POST':
        try:
            operador_id = request.POST.get('operador')
            operador = get_object_or_404(Condutor, id=operador_id)
            
            instance = ChecklistForklift(
                responsavel=request.user,
                operador=operador,
                tipo_equipamento=request.POST.get('tipo_equipamento'),
                observacoes=request.POST.get('observacoes', ''),
                visto_responsavel=request.POST.get('visto_responsavel', ''),
                visto_operador=request.POST.get('visto_operador', ''),
                tempo_execucao=int(request.POST.get('tempo_execucao', 0)) or None,
            )
            
            # Attributing fields
            for item in items:
                setattr(instance, item['id'], request.POST.get(item['id'], 'NA'))
                
            instance.save()

            # Handle Photos
            photos = request.FILES.getlist('photos')
            for f in photos:
                _process_and_save_photo(instance, f)
            
            # Anomaly logic
            has_nc = any(getattr(instance, item['id']) == 'NAO' for item in items)
            
            if has_nc or (instance.observacoes and instance.observacoes.strip()):
                _send_forklift_anomaly_email(instance, request)
            
            # Notificação PWA Push
            _notify_new_checklist_push(instance, "Empilhadeira")
                
            messages.success(request, 'Checklist de Empilhadeira salvo com sucesso!')
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f'Erro ao salvar: {str(e)}')
            
    context = {
        'items': items,
        'operadores': Condutor.objects.all().order_by('nome'),
    }
    return render(request, 'forklift_form.html', context)

@login_required
def forklift_detail_view(request, pk):
    checklist = get_object_or_404(ChecklistForklift, pk=pk)
    items_resolved = []
    for item in FORKLIFT_ITEMS:
        items_resolved.append({
            'label': item['label'],
            'value': getattr(checklist, item['id'], 'NA')
        })
        
    return render(request, 'forklift_detail.html', {
        'checklist': checklist,
        'items_resolved': items_resolved
    })

@login_required
def condutor_list_view(request):
    if request.user.profile.role not in ['ADMIN', 'SUPERUSER']:
        messages.error(request, "Acesso restrito à gestão de Motoristas.")
        return redirect('home')
    if request.method == 'POST':
        # Handles creation and deletion
        action = request.POST.get('action')
        if action == 'create':
            try:
                Condutor.objects.create(
                    nome=request.POST.get('nome', '').upper(),
                    cpf=request.POST.get('cpf', ''),
                    data_nascimento=request.POST.get('data_nascimento') or None
                )
                messages.success(request, 'Motorista cadastrado com sucesso!')
            except Exception as e:
                messages.error(request, 'Erro ao cadastrar motorista (CPF já existe?).')
        elif action == 'delete':
            try:
                c_id = request.POST.get('id')
                Condutor.objects.filter(id=c_id).delete()
                messages.success(request, 'Motorista excluído com sucesso!')
            except Exception as e:
                messages.error(request, 'Erro ao excluir motorista (possui vinculos).')
        return redirect('condutor_list')
        
    condutores = Condutor.objects.all().order_by('nome')
    return render(request, 'condutor_list.html', {'condutores': condutores})

@login_required
def veiculo_list_view(request):
    if request.user.profile.role not in ['ADMIN', 'SUPERUSER']:
        messages.error(request, "Acesso restrito à gestão de Veículos.")
        return redirect('home')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            try:
                Veiculo.objects.create(
                    placa=request.POST.get('placa', '').upper(),
                    tipo=request.POST.get('tipo', 'CAVALO'),
                    marca_modelo=request.POST.get('marca_modelo', '').upper(),
                    ano=request.POST.get('ano', ''),
                    renavam=request.POST.get('renavam', ''),
                    categoria=request.POST.get('categoria') if request.POST.get('tipo') == 'CARRETA' else None
                )
                messages.success(request, 'Veículo cadastrado com sucesso!')
            except Exception as e:
                messages.error(request, 'Erro ao cadastrar veículo (Placa já existe?).')
        elif action == 'delete':
            try:
                v_id = request.POST.get('id')
                Veiculo.objects.filter(id=v_id).delete()
                messages.success(request, 'Veículo excluído com sucesso!')
            except Exception as e:
                messages.error(request, 'Erro ao excluir veículo (possui vinculos).')
        return redirect('veiculo_list')
        
    veiculos = Veiculo.objects.all().order_by('tipo', 'placa')
    return render(request, 'veiculo_list.html', {'veiculos': veiculos})

@login_required
def home_view(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'test_push_single':
            payload = {
                "head": "🚀 TESTE INTALOG PWA",
                "body": f"Olá {request.user.first_name or request.user.username}, esta é uma notificação de teste enviada da sua Central de Notificações.",
                "url": f"{request.scheme}://{request.get_host()}/"
            }
            try:
                # Verify if user has webpush subscriptions
                sub_count = 0
                if hasattr(request.user, 'webpush_info'):
                    sub_count = request.user.webpush_info.count()
                
                if sub_count == 0:
                    messages.error(request, 'Erro: Seu navegador ainda não está inscrito. Clique no ícone do sino para ativar.')
                else:
                    # Looping manual para ser resiliente a erros individuais (403, 410, etc)
                    from webpush.utils import _send_notification
                    success_count = 0
                    fail_count = 0
                    for info in request.user.webpush_info.all():
                        try:
                            # O payload deve ser uma string JSON para o pywebpush
                            payload_json = json.dumps(payload)
                            _send_notification(info.subscription, payload_json, ttl=1000)
                            success_count += 1
                        except Exception:
                            fail_count += 1
                    
                    if success_count > 0:
                        messages.success(request, f'Notificação enviada com sucesso para {success_count} aparelho(s)!')
                    if fail_count > 0:
                        messages.warning(request, f'Houve falha em {fail_count} aparelho(s) (possivelmente tokens expirados).')
                
                return redirect('home')
            except Exception as e:
                messages.error(request, f'Erro ao disparar notificação: {str(e)}')
            
            return redirect('home')
    return render(request, 'home.html')

import unicodedata
import re

@login_required
def system_admin_view(request):
    # Only ADMIN and superusers
    if not request.user.is_superuser and (not hasattr(request.user, 'profile') or request.user.profile.role != 'ADMIN'):
        messages.error(request, 'Acesso negado. Apenas administradores podem acessar esta área.')
        return redirect('dashboard')

    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_email':
            email = request.POST.get('email', '').strip().lower()
            category = request.POST.get('category', 'PORTARIA')
            if email:
                try:
                    AlertEmail.objects.create(email=email, category=category)
                    messages.success(request, f'E-mail {email} adicionado aos alertas de {category}.')
                except:
                    messages.error(request, 'Erro ao adicionar e-mail (já cadastrado nesta categoria?)')
            
        elif action == 'delete_email':
            email_id = request.POST.get('id')
            AlertEmail.objects.filter(id=email_id).delete()
            messages.success(request, 'E-mail removido da lista de alertas.')
            
        elif action == 'add_telegram':
            nome = request.POST.get('nome', '').strip().upper()
            chat_id = request.POST.get('chat_id', '').strip()
            if nome and chat_id:
                AlertTelegram.objects.create(nome=nome, chat_id=chat_id)
                messages.success(request, f'Contato Telegram {nome} (ID: {chat_id}) adicionado.')
            
        elif action == 'delete_telegram':
            telegram_id = request.POST.get('id')
            AlertTelegram.objects.filter(id=telegram_id).delete()
            messages.success(request, 'Contato Telegram removido.')

        elif action == 'create_user':
            import secrets
            import string
            
            full_name = request.POST.get('full_name', '').strip().upper()
            role = request.POST.get('role', 'CONTROLADOR')
            cpf = request.POST.get('cpf', '')
            
            # Generate a secure 8-character password
            alphabet = string.ascii_uppercase + string.digits
            password = ''.join(secrets.choice(alphabet) for _ in range(8))
            
            if not full_name:
                messages.error(request, 'O nome completo é obrigatório.')
            else:
                # Logic from React: FIRST.LAST username
                name_parts = full_name.split()
                first_name = name_parts[0] if name_parts else ''
                last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ' '
                
                def clean_string(s):
                    # Remove accents and non-alpha
                    s = unicodedata.normalize('NFD', s).encode('ascii', 'ignore').decode('utf-8')
                    return re.sub(r'[^a-zA-Z]', '', s).upper()

                clean_first = clean_string(first_name)
                clean_last = clean_string(name_parts[-1]) if len(name_parts) > 1 else ''
                
                username_base = f"{clean_first}.{clean_last}" if clean_last else clean_first
                username = username_base
                
                # Check for uniqueness and append suffix if needed
                counter = 2
                while User.objects.filter(username=username).exists():
                    username = f"{username_base}.{counter}"
                    counter += 1
                
                try:
                    # Security check for SUPERUSER role
                    is_su = False
                    if role == 'SUPERUSER':
                        if request.user.is_superuser:
                            is_su = True
                        else:
                            # Fallback if a non-superuser tries to force this role
                            messages.warning(request, "Atenção: Apenas Superusuários podem criar outros Superusuários. Perfil alterado para ADMINISTRADOR.")
                            role = 'ADMIN'

                    # Create user
                    new_user = User.objects.create_user(
                        username=username,
                        password=password,
                        first_name=first_name,
                        last_name=last_name,
                        is_superuser=is_su,
                        is_staff=is_su,
                        email=f"{username.lower()}@intalog.com.br"
                    )
                    # Update profile (created by signals)
                    profile = new_user.profile
                    profile.role = role
                    profile.cpf = cpf
                    profile.save()
                    
                    messages.success(
                        request, 
                        f"{username}|{password}", 
                        extra_tags='copy_credentials'
                    )
                except Exception as e:
                    err_msg = str(e)
                    if "UNIQUE constraint failed" in err_msg:
                        messages.error(request, 'Erro: Já existe um usuário com dados similares ou este login está reservado.')
                    else:
                        messages.error(request, f'Erro ao criar usuário: {err_msg}')
                    
        elif action == 'update_smtp':
            if not request.user.is_superuser:
                messages.error(request, 'Apenas superusuários podem alterar configurações de SMTP.')
                return redirect('system_admin')
            
            host = request.POST.get('host')
            port = request.POST.get('port')
            user = request.POST.get('user')
            password = request.POST.get('password')
            use_tls = request.POST.get('use_tls') == 'on'
            use_ssl = request.POST.get('use_ssl') == 'on'
            default_from = request.POST.get('default_from')
            
            config, created = EmailConfig.objects.get_or_create(id=1)
            config.host = host
            try:
                config.port = int(port) if port else 465
            except (ValueError, TypeError):
                config.port = 465
            config.user = user
            if password: # Update only if password is provided
                config.password = password
            config.use_tls = use_tls
            config.use_ssl = use_ssl
            config.default_from = default_from
            config.save()
            messages.success(request, 'Configurações de SMTP atualizadas com sucesso!')
            
        elif action == 'update_telegram':
            if not request.user.is_superuser:
                messages.error(request, 'Apenas superusuários podem alterar configurações do Telegram.')
                return redirect('system_admin')
            
            token = request.POST.get('bot_token')
            link = request.POST.get('bot_link')
            config, created = TelegramConfig.objects.get_or_create(id=1)
            if token:
                config.bot_token = token
            if link is not None:
                config.bot_link = link
            config.save()
            messages.success(request, 'Configurações do Telegram atualizadas com sucesso!')
            
        elif action == 'test_telegram_single':
            chat_id = request.POST.get('chat_id')
            nome = request.POST.get('nome')
            msg = f"<b>🚀 TESTE DE CONEXÃO</b>\n\nOlá {nome}, esta é uma mensagem de teste da <b>Central Operacional Check-up & Manutenção - Intalog</b>.\n\n⚠️ <i>Por favor, não responda a esta mensagem.</i>"
            
            success, error_msg = _send_single_telegram_message(chat_id, msg)
            if success:
                messages.success(request, f'Mensagem de teste enviada com sucesso para {nome}!')
            else:
                messages.error(request, f'Falha ao enviar para {nome}: {error_msg}')
            
        elif action == 'unlink_telegram_user':
            user_id = request.POST.get('user_id')
            user_to_unlink = get_object_or_404(User, id=user_id)
            if hasattr(user_to_unlink, 'profile'):
                user_to_unlink.profile.telegram_chat_id = None
                user_to_unlink.profile.save()
                messages.success(request, f'Vínculo do Telegram de {user_to_unlink.username} removido.')

        elif action == 'test_push_single':
            tester_user_id = request.POST.get('user_id')
            target_user = get_object_or_404(User, id=tester_user_id)
            
            payload = {
                "head": "🚀 TESTE INTALOG PWA",
                "body": f"Olá {target_user.first_name or target_user.username}, esta é uma notificação de teste enviada do painel administrativo.",
                "url": f"{request.scheme}://{request.get_host()}/"
            }
            
            try:
                from webpush import send_user_notification
                # Verify if user has webpush subscriptions
                if not hasattr(target_user, 'webpush_info') or target_user.webpush_info.count() == 0:
                    messages.error(request, f'Erro: O usuário {target_user.username} ainda não ativou as notificações (clicou no Sininho).')
                else:
                    send_user_notification(user=target_user, payload=payload, ttl=1000)
                    messages.success(request, f'Comando de Notificação Push enviado para {target_user.username} em todos os seus aparelhos vinculados!')
            except Exception as e:
                messages.error(request, f'Erro ao disparar PWA Push: {str(e)}')

        return redirect('system_admin')

    context = {
        'emails_portaria': AlertEmail.objects.filter(category='PORTARIA').order_by('email'),
        'emails_manutencao': AlertEmail.objects.filter(category='MANUTENCAO').order_by('email'),
        'emails_agenda': AlertEmail.objects.filter(category='AGENDA').order_by('email'),
        'telegrams': AlertTelegram.objects.all().order_by('nome'),
        'telegram_users': User.objects.filter(profile__telegram_chat_id__isnull=False).select_related('profile').order_by('username'),
        'users': User.objects.all().select_related('profile').order_by('-date_joined')[:15],
        'email_config': EmailConfig.objects.first(),
        'telegram_config': TelegramConfig.objects.first(),
    }
    return render(request, 'system_admin.html', context)

@login_required
def agenda_manutencao_view(request):
    """View to display the maintenance agenda with filtering"""
    if request.user.profile.role not in ['MANUTENCAO', 'GESTOR', 'ADMIN', 'SUPERUSER']:
        messages.error(request, "Acesso restrito à Agenda de Manutenção.")
        return redirect('home')
    query = request.GET.get('q', '')
    filter_date = request.GET.get('date', '')
    
    schedules = MaintenanceSchedule.objects.all().order_by('data_paralizacao')
    
    if not query and not filter_date:
        # Default view: Only active events
        schedules = schedules.exclude(status__in=['CONCLUIDO', 'CANCELADO'])
    else:
        # When searching or filtering by date, show everything that matches
        if query:
            schedules = schedules.filter(veiculo__placa__icontains=query)
            
        if filter_date:
            try:
                # Filter schedules that overlap or start on the selected date
                date_obj = datetime.strptime(filter_date, '%Y-%m-%d').date()
                schedules = schedules.filter(
                    Q(data_paralizacao__date=date_obj) | 
                    Q(data_previsao_liberacao__date=date_obj)
                )
            except ValueError:
                pass

    veiculos = Veiculo.objects.all().order_by('placa')
    
    # Prepare events for FullCalendar
    events = []
    for s in schedules:
        # Get logs for this schedule
        logs = []
        # Add initial "Pendente" event based on creation
        logs.append({
            'action': 'Aberto como PENDENTE',
            'user': s.criado_por.username,
            'at': s.data_criacao.strftime('%d/%m/%Y %H:%M')
        })
        # Add actual status logs
        for log in s.logs.all():
            logs.append({
                'action': f"Alterado para {log.get_new_status_display()}",
                'user': log.user.username if log.user else "Sistema",
                'at': log.created_at.strftime('%d/%m/%Y %H:%M')
            })

        events.append({
            'id': s.id,
            'title': f"{s.veiculo.placa}",
            'start': s.data_paralizacao.isoformat(),
            'end': s.data_previsao_liberacao.isoformat(),
            'description': s.descricao,
            'status': s.status,
            'status_label': s.get_status_display(),
            'logs': logs,
            'className': f"status-{s.status.lower()}"
        })

    context = {
        'events_json': json.dumps(events, cls=DjangoJSONEncoder),
        'schedules': schedules,
        'veiculos': veiculos,
        'today': datetime.now()
    }
    return render(request, 'agenda_manutencao.html', context)

@login_required
def schedule_create_view(request):
    """AJAX/POST view to create a new maintenance schedule"""
    if request.user.profile.role not in ['MANUTENCAO', 'ADMIN', 'SUPERUSER']:
        messages.error(request, "Acesso restrito à criação de agendamentos.")
        return redirect('agenda_manutencao')
    if request.method == 'POST':
        try:
            veiculo_id = request.POST.get('veiculo')
            data_paralizacao = request.POST.get('data_paralizacao')
            data_previsao = request.POST.get('data_previsao_liberacao')
            descricao = request.POST.get('descricao')
            
            # Simple validation
            if not all([veiculo_id, data_paralizacao, data_previsao, descricao]):
                messages.error(request, "Todos os campos são obrigatórios.")
                return redirect('agenda_manutencao')

            veiculo = get_object_or_404(Veiculo, id=veiculo_id)
            
            # Conflict Validation (Overlap)
            conflicts = MaintenanceSchedule.objects.filter(
                veiculo=veiculo,
                status__in=['PENDENTE', 'EM_ANDAMENTO'],
                data_paralizacao__lt=data_previsao,
                data_previsao_liberacao__gt=data_paralizacao
            ).exists()

            if conflicts:
                messages.error(request, f"ERRO: O veículo {veiculo.placa} já possui um agendamento conflitante neste período.")
                return redirect('agenda_manutencao')

            schedule = MaintenanceSchedule.objects.create(
                veiculo=veiculo,
                data_paralizacao=data_paralizacao,
                data_previsao_liberacao=data_previsao,
                descricao=descricao,
                criado_por=request.user
            )
            
            # Refresh to ensure dates are datetime objects for the email template
            schedule.refresh_from_db()

            # Trigger Alerts
            _send_schedule_alerts(schedule, request)
            
            messages.success(request, f"Manutenção do veículo {veiculo.placa} agendada com sucesso!")
        except Exception as e:
            messages.error(request, f"Erro ao agendar manutenção: {str(e)}")
            
    return redirect('agenda_manutencao')

@login_required
def schedule_delete_view(request, pk):
    """Delete a maintenance schedule"""
    if request.user.profile.role not in ['MANUTENCAO', 'ADMIN', 'SUPERUSER']:
        messages.error(request, "Acesso restrito à exclusão de agendamentos.")
        return redirect('agenda_manutencao')
        
    schedule = get_object_or_404(MaintenanceSchedule, pk=pk)
    
    # Block deletion of finalized schedules
    if schedule.status in ['CONCLUIDO', 'CANCELADO']:
        messages.error(request, "Não é possível excluir um agendamento finalizado.")
        return redirect('agenda_manutencao')

    veiculo_placa = schedule.veiculo.placa
    schedule.delete()
    messages.success(request, f"Agendamento do veículo {veiculo_placa} excluído.")
    return redirect('agenda_manutencao')

def _send_status_update_alerts(schedule, request):
    """Helper to send alerts when status changes to final states"""
    # Logic for Email (only for CONCLUIDO/CANCELADO)
    if schedule.status in ['CONCLUIDO', 'CANCELADO']:
        emails = AlertEmail.objects.filter(category='AGENDA').values_list('email', flat=True)
        if emails:
            subject = f"ATUALIZAÇÃO DE MANUTENÇÃO: {schedule.veiculo.placa} - {schedule.get_status_display().upper()}"
            site_url = request.build_absolute_uri('/')[:-1]
            
            html_content = render_to_string('emails/status_update_email.html', {
                'schedule': schedule,
                'site_url': site_url,
                'user': request.user,
                'now': datetime.now(),
                'advise_checklist': schedule.status == 'CONCLUIDO'
            })
            
            connection, from_email = _get_email_connection()
            try:
                send_mail(
                    subject,
                    "",
                    from_email,
                    list(emails),
                    html_message=html_content,
                    connection=connection
                )
            except Exception as e:
                print(f"Error sending status email: {e}")

        # Telegram Logic
        msg = f"<b>🔔 ATUALIZAÇÃO DE MANUTENÇÃO</b>\n"
        msg += f"<i>Central Operacional Check-up & Manutenção - Intalog</i>\n\n"
        msg += f"Veículo: {schedule.veiculo.placa}\n"
        msg += f"Situação: {schedule.get_status_display().upper()}\n"
        msg += f"Descrição: {schedule.descricao}\n\n"
        if schedule.status == 'CONCLUIDO':
            msg += "✅ *Veículo LIBERADO para escala.*\n"
            msg += "💡 Aconselhamos a realização de um checklist completo."
        
        _send_telegram_message(msg)

@login_required
def schedule_update_status_view(request, pk):
    """Update status of a maintenance schedule"""
    if request.user.profile.role not in ['MANUTENCAO', 'ADMIN', 'SUPERUSER']:
        messages.error(request, "Acesso restrito à alteração de status.")
        return redirect('agenda_manutencao')

    schedule = get_object_or_404(MaintenanceSchedule, pk=pk)
    
    # Block updates to finalized schedules
    if schedule.status in ['CONCLUIDO', 'CANCELADO']:
        messages.error(request, "Agendamentos finalizados não podem ser alterados.")
        return redirect('agenda_manutencao')

    if request.method == 'POST':
        new_status = request.POST.get('status')
        old_status = schedule.status
        if new_status in dict(MaintenanceSchedule.STATUS_CHOICES) and new_status != old_status:
            # Workflow Validation: CONCLUIDO requires EM_ANDAMENTO
            if new_status == 'CONCLUIDO' and old_status != 'EM_ANDAMENTO':
                messages.error(request, "Uma manutenção só pode ser CONCLUÍDA se estiver EM ANDAMENTO.")
                return redirect('agenda_manutencao')

            # Save the change
            schedule.status = new_status
            schedule.save()
            
            # Create History Log
            MaintenanceStatusLog.objects.create(
                schedule=schedule,
                old_status=old_status,
                new_status=new_status,
                user=request.user
            )

            # Send alerts only for final statuses or significant changes
            _send_status_update_alerts(schedule, request)
            
            messages.success(request, f"Status do veículo {schedule.veiculo.placa} atualizado para {schedule.get_status_display()}.")
    
    return redirect('agenda_manutencao')

@login_required
def resolve_checklist_view(request, checklist_type, pk):
    # Only MANUTENCAO can resolve
    if request.user.profile.role not in ['MANUTENCAO', 'ADMIN', 'SUPERUSER']:
        messages.error(request, 'Você não tem permissão para sinalizar como resolvido (Acesso restrito à Manutenção).')
        return redirect('dashboard')

    if request.method == 'POST':
        ModelClass = None
        redirect_url = 'dashboard'
        
        if checklist_type == 'portaria':
            ModelClass = Checklist
            redirect_url = 'portaria_detail'
        elif checklist_type == 'truck':
            ModelClass = MaintenanceTruck
            redirect_url = 'maintenance_detail'
        elif checklist_type == 'trailer':
            ModelClass = MaintenanceTrailer
            redirect_url = 'maintenance_detail'
        elif checklist_type == 'forklift':
            ModelClass = ChecklistForklift
            redirect_url = 'forklift_detail'

        if ModelClass:
            checklist = get_object_or_404(ModelClass, pk=pk)
            checklist.resolvido_por = request.user
            checklist.data_resolucao = timezone.now()
            checklist.save()

            # Delete related photos as per rule
            ct = ContentType.objects.get_for_model(checklist)
            photos = ChecklistPhoto.objects.filter(content_type=ct, object_id=checklist.id)
            for p in photos:
                p.delete() # Trigger physical file deletion
                
            messages.success(request, '✅ Checklist sinalizado como RESOLVIDO com sucesso!')
            
            if checklist_type in ['truck', 'trailer']:
                return redirect(redirect_url, m_type=checklist_type, pk=pk)
            return redirect(redirect_url, pk=pk)


    return redirect('dashboard')

@login_required
def download_checklist_photos_zip(request, checklist_type, pk):
    """Generates a ZIP file containing all photos for a specific checklist"""
    ModelClass = None
    if checklist_type == 'portaria':
        ModelClass = Checklist
    elif checklist_type == 'forklift':
        ModelClass = ChecklistForklift
    
    if not ModelClass:
        messages.error(request, 'Tipo de checklist inválido.')
        return redirect('dashboard')
        
    obj = get_object_or_404(ModelClass, pk=pk)
    photos = obj.photos
    
    if not photos:
        messages.warning(request, 'Este checklist não possui fotos para baixar.')
        return redirect(f'{checklist_type}_detail', pk=pk)
        
    # Create ZIP in memory
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zip_file:
        for i, photo in enumerate(photos):
            if photo.file and os.path.exists(photo.file.path):
                # Use a friendly name for each file in the zip
                ext = photo.file.name.split('.')[-1]
                filename = f"foto_{i+1}_{obj.id}.{ext}"
                zip_file.write(photo.file.path, filename)
            
    buffer.seek(0)
    
    response = HttpResponse(buffer.read(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="fotos_checklist_{checklist_type}_{pk}.zip"'
    return response
