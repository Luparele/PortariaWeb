"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required
from checklists.views import (
    dashboard_view, portaria_create_view, portaria_detail_view, 
    maintenance_create_view, condutor_list_view, veiculo_list_view, 
    maintenance_detail_view, system_admin_view, forklift_create_view, forklift_detail_view,
    agenda_manutencao_view, schedule_create_view, schedule_update_status_view, resolve_checklist_view,
    download_checklist_photos_zip, generate_telegram_token, telegram_webhook
)

urlpatterns = [
    path('', login_required(TemplateView.as_view(template_name='home.html')), name='home'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('portaria/nova/', portaria_create_view, name='portaria_create'),
    path('portaria/<int:pk>/', portaria_detail_view, name='portaria_detail'),
    path('checklist/resolver/<str:checklist_type>/<int:pk>/', resolve_checklist_view, name='resolve_checklist'),
    path('checklist/download-zip/<str:checklist_type>/<int:pk>/', download_checklist_photos_zip, name='download_photos_zip'),
    path('manutencao/agenda/', agenda_manutencao_view, name='agenda_manutencao'),
    path('manutencao/agenda/nova/', schedule_create_view, name='schedule_create'),
    path('manutencao/agenda/status/<int:pk>/', schedule_update_status_view, name='schedule_status'),
    path('manutencao/<str:m_type>/nova/', maintenance_create_view, name='maintenance_create'),
    path('manutencao/<str:m_type>/<int:pk>/', maintenance_detail_view, name='maintenance_detail'),
    path('forklift/novo/', forklift_create_view, name='forklift_create'),
    path('forklift/<int:pk>/', forklift_detail_view, name='forklift_detail'),
    path('admin/motoristas/', condutor_list_view, name='condutor_list'),
    path('admin/veiculos/', veiculo_list_view, name='veiculo_list'),
    path('admin-sistema/', system_admin_view, name='system_admin'),
    path('', include('django.contrib.auth.urls')),
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change_form.html'), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done.html'), name='password_change_done'),
    
    # Rotas PWA
    path('sw.js', TemplateView.as_view(template_name='sw.js', content_type='application/javascript'), name='sw_js'),
    path('manifest.json', TemplateView.as_view(template_name='manifest.json', content_type='application/json'), name='manifest_json'),
    path('webpush/', include('webpush.urls')),
    
    # Telegram Deep Linking
    path('telegram/ativar/', generate_telegram_token, name='telegram_activate'),
    path('telegram/webhook/', telegram_webhook, name='telegram_webhook'),

    path('admin/', admin.site.urls),
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
