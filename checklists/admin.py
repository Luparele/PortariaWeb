from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Checklist, Profile, Condutor, Veiculo, AlertEmail, MaintenanceTruck, MaintenanceTrailer, ChecklistForklift, MaintenanceSchedule, AlertTelegram, EmailConfig, TelegramConfig

class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'perfil'

class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)

# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

admin.site.site_header = "CHECK-UP & MANUTENÇÃO"
admin.site.site_title = "Check-up & Manutenção Admin"
admin.site.index_title = "Gestão Operacional"

@admin.register(Condutor)
class CondutorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'cpf', 'data_nascimento')
    search_fields = ('nome', 'cpf')

@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ('placa', 'tipo', 'id_frota', 'marca', 'modelo')
    list_filter = ('tipo', 'marca')
    search_fields = ('placa', 'id_frota')

@admin.register(AlertEmail)
class AlertEmailAdmin(admin.ModelAdmin):
    list_display = ('email', 'category', 'created_at')
    list_filter = ('category',)
    search_fields = ('email',)

@admin.register(Checklist)
class ChecklistAdmin(admin.ModelAdmin):
    list_display = ('placa_cavalo', 'nome_motorista', 'porteiro', 'data_criacao')
    list_filter = ('tipo_equipamento', 'data_criacao')
    search_fields = ('placa_cavalo', 'nome_motorista', 'placa_carreta_01', 'placa_carreta_02')

@admin.register(MaintenanceTruck)
class MaintenanceTruckAdmin(admin.ModelAdmin):
    list_display = ('veiculo', 'motorista', 'responsavel', 'data_criacao', 'quilometragem')
    list_filter = ('data_criacao', 'veiculo')
    search_fields = ('veiculo__placa', 'motorista__nome')

@admin.register(MaintenanceTrailer)
class MaintenanceTrailerAdmin(admin.ModelAdmin):
    list_display = ('veiculo', 'motorista', 'responsavel', 'data_criacao')
    list_filter = ('data_criacao', 'veiculo')
    search_fields = ('veiculo__placa', 'motorista__nome')
@admin.register(ChecklistForklift)
class ChecklistForkliftAdmin(admin.ModelAdmin):
    list_display = ('tipo_equipamento', 'operador', 'responsavel', 'data_criacao', 'tempo_formatado')
    list_filter = ('tipo_equipamento', 'data_criacao')
    search_fields = ('operador__nome', 'tipo_equipamento')

@admin.register(MaintenanceSchedule)
class MaintenanceScheduleAdmin(admin.ModelAdmin):
    list_display = ('veiculo', 'data_paralizacao', 'data_previsao_liberacao', 'status', 'criado_por', 'data_criacao')
    list_filter = ('status', 'data_paralizacao')
    search_fields = ('veiculo__placa', 'descricao')

@admin.register(AlertTelegram)
class AlertTelegramAdmin(admin.ModelAdmin):
    list_display = ('nome', 'chat_id', 'ativo', 'created_at')
    list_filter = ('ativo',)
    search_fields = ('nome', 'chat_id')

@admin.register(EmailConfig)
class EmailConfigAdmin(admin.ModelAdmin):
    list_display = ('user', 'host', 'port', 'updated_at')
