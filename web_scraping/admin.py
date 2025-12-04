"""
Admin para gerenciamento de sincronização de Google Forms
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count
from .models import (
    ProcessedGoogleFormSubmission,
    PatientRegistrationLog,
    GoogleFormsSync
)


@admin.register(ProcessedGoogleFormSubmission)
class ProcessedGoogleFormSubmissionAdmin(admin.ModelAdmin):
    """Admin para submissões do Google Forms processadas"""
    
    list_display = [
        'full_name',
        'cpf',
        'email',
        'status_badge',
        'patient_id_in_platform',
        'attempts',
        'processed_at'
    ]
    
    list_filter = [
        'status',
        'processed_at',
        'attempts'
    ]
    
    search_fields = [
        'cpf',
        'email',
        'full_name'
    ]
    
    readonly_fields = [
        'processed_at',
        'last_attempt_at',
        'raw_form_data_display'
    ]
    
    fieldsets = (
        ('Informações Pessoais', {
            'fields': ('full_name', 'cpf', 'email')
        }),
        ('Status de Processamento', {
            'fields': ('status', 'patient_id_in_platform', 'error_message')
        }),
        ('Rastreamento', {
            'fields': ('attempts', 'processed_at', 'last_attempt_at')
        }),
        ('Dados do Formulário', {
            'fields': ('raw_form_data_display',),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """Exibe status com cores"""
        colors = {
            'pending': '#FFA500',      # Laranja
            'processing': '#4169E1',   # Royal Blue
            'success': '#228B22',      # Forest Green
            'duplicate': '#FFD700',    # Gold
            'error': '#FF0000',        # Red
        }
        
        color = colors.get(obj.status, '#808080')
        return format_html(
            f'<span style="background-color: {color}; color: white; padding: 3px 8px; border-radius: 3px;">'
            f'{obj.get_status_display()}'
            '</span>'
        )
    
    status_badge.short_description = 'Status'
    
    def raw_form_data_display(self, obj):
        """Exibe dados do formulário de forma formatada"""
        if obj.raw_form_data:
            import json
            return format_html(
                '<pre>{}</pre>',
                json.dumps(obj.raw_form_data, indent=2, ensure_ascii=False)
            )
        return '-'
    
    raw_form_data_display.short_description = 'Dados Brutos do Formulário'


@admin.register(PatientRegistrationLog)
class PatientRegistrationLogAdmin(admin.ModelAdmin):
    """Admin para logs de registros de pacientes"""
    
    list_display = [
        'submission_name',
        'submission_cpf',
        'attempt_number',
        'step',
        'success_badge',
        'timestamp'
    ]
    
    list_filter = [
        'success',
        'step',
        'timestamp'
    ]
    
    search_fields = [
        'submission__full_name',
        'submission__cpf',
        'message'
    ]
    
    readonly_fields = [
        'timestamp',
        'message_display',
        'error_details_display'
    ]
    
    fieldsets = (
        ('Submissão', {
            'fields': ('submission',)
        }),
        ('Informações da Tentativa', {
            'fields': ('attempt_number', 'step', 'success', 'timestamp')
        }),
        ('Mensagens', {
            'fields': ('message_display', 'error_details_display')
        }),
    )
    
    def submission_name(self, obj):
        return obj.submission.full_name
    submission_name.short_description = 'Paciente'
    
    def submission_cpf(self, obj):
        return obj.submission.cpf
    submission_cpf.short_description = 'CPF'
    
    def success_badge(self, obj):
        """Exibe sucesso/erro com cores"""
        if obj.success:
            return format_html(
                '<span style="background-color: #228B22; color: white; padding: 3px 8px; border-radius: 3px;">'
                'Sucesso'
                '</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #FF0000; color: white; padding: 3px 8px; border-radius: 3px;">'
                'Erro'
                '</span>'
            )
    
    success_badge.short_description = 'Resultado'
    
    def message_display(self, obj):
        """Exibe mensagem formatada"""
        return format_html('<pre>{}</pre>', obj.message)
    
    message_display.short_description = 'Mensagem'
    
    def error_details_display(self, obj):
        """Exibe detalhes do erro"""
        if obj.error_details:
            return format_html('<pre>{}</pre>', obj.error_details)
        return '-'
    
    error_details_display.short_description = 'Detalhes do Erro'


@admin.register(GoogleFormsSync)
class GoogleFormsSyncAdmin(admin.ModelAdmin):
    """Admin para sincronizações do Google Forms"""
    
    list_display = [
        'id',
        'synced_at',
        'status_badge',
        'total_new_responses',
        'successfully_registered',
        'duplicates_found',
        'errors',
        'duration_seconds'
    ]
    
    list_filter = [
        'status',
        'synced_at'
    ]
    
    readonly_fields = [
        'synced_at',
        'error_message',
        'statistics_display'
    ]
    
    fieldsets = (
        ('Status', {
            'fields': ('status', 'synced_at')
        }),
        ('Estatísticas', {
            'fields': ('statistics_display',)
        }),
        ('Duração', {
            'fields': ('duration_seconds',)
        }),
        ('Erros', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        """Exibe status com cores"""
        colors = {
            'pending': '#FFA500',
            'running': '#4169E1',
            'completed': '#228B22',
            'failed': '#FF0000',
        }
        
        color = colors.get(obj.status, '#808080')
        return format_html(
            f'<span style="background-color: {color}; color: white; padding: 3px 8px; border-radius: 3px;">'
            f'{obj.get_status_display()}'
            '</span>'
        )
    
    status_badge.short_description = 'Status'
    
    def statistics_display(self, obj):
        """Exibe estatísticas de forma formatada"""
        return format_html(
            '<table style="border-collapse: collapse;">'
            '<tr style="background-color: #f0f0f0;">'
            '<td style="border: 1px solid #ddd; padding: 8px;"><b>Respostas Novas</b></td>'
            '<td style="border: 1px solid #ddd; padding: 8px;">{}</td>'
            '</tr>'
            '<tr>'
            '<td style="border: 1px solid #ddd; padding: 8px;"><b>Registrados com Sucesso</b></td>'
            '<td style="border: 1px solid #ddd; padding: 8px; color: #228B22;"><b>{}</b></td>'
            '</tr>'
            '<tr style="background-color: #f0f0f0;">'
            '<td style="border: 1px solid #ddd; padding: 8px;"><b>Duplicatas</b></td>'
            '<td style="border: 1px solid #ddd; padding: 8px; color: #FFD700;"><b>{}</b></td>'
            '</tr>'
            '<tr>'
            '<td style="border: 1px solid #ddd; padding: 8px;"><b>Erros</b></td>'
            '<td style="border: 1px solid #ddd; padding: 8px; color: #FF0000;"><b>{}</b></td>'
            '</tr>'
            '</table>',
            obj.total_new_responses,
            obj.successfully_registered,
            obj.duplicates_found,
            obj.errors
        )
    
    statistics_display.short_description = 'Estatísticas'
    
    def has_add_permission(self, request):
        """Não permitir adicionar sincronizações manualmente"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Permitir apenas admin deletar"""
        return request.user.is_superuser
