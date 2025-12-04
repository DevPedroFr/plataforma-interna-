"""
Modelos para rastreamento de sincronização de web scraping
"""

from django.db import models
from core.models import User


class ProcessedGoogleFormSubmission(models.Model):
    """
    Rastreia submissões do Google Forms que foram processadas para evitar duplicatas
    """
    
    cpf = models.CharField(max_length=14, unique=True, db_index=True)
    email = models.EmailField(blank=True, null=True)
    full_name = models.CharField(max_length=255)
    
    # Informações de processamento
    processed_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pendente'),
            ('processing', 'Processando'),
            ('success', 'Sucesso'),
            ('duplicate', 'Duplicado'),
            ('error', 'Erro'),
        ],
        default='pending'
    )
    
    # Rastreamento
    patient_id_in_platform = models.CharField(max_length=50, blank=True, null=True, help_text="ID do paciente na plataforma GoC")
    error_message = models.TextField(blank=True, null=True)
    attempts = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(blank=True, null=True)
    
    # Referência a User do sistema (se aplicável)
    local_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Dados brutos do formulário
    raw_form_data = models.JSONField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Submissão de Google Form Processada"
        verbose_name_plural = "Submissões de Google Forms Processadas"
        ordering = ['-processed_at']
    
    def __str__(self):
        return f"{self.full_name} ({self.cpf}) - {self.get_status_display()}"


class PatientRegistrationLog(models.Model):
    """
    Log detalhado de tentativas de registro de pacientes
    """
    
    submission = models.ForeignKey(ProcessedGoogleFormSubmission, on_delete=models.CASCADE, related_name='logs')
    
    attempt_number = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    success = models.BooleanField(default=False)
    message = models.TextField()
    error_details = models.TextField(blank=True, null=True)
    
    # Etapas do processo
    step = models.CharField(
        max_length=50,
        choices=[
            ('validation', 'Validação'),
            ('cpf_check', 'Verificação de CPF'),
            ('login', 'Login'),
            ('navigation', 'Navegação'),
            ('form_fill', 'Preenchimento de Formulário'),
            ('form_submit', 'Envio de Formulário'),
            ('confirmation', 'Confirmação'),
        ]
    )
    
    class Meta:
        verbose_name = "Log de Registro de Paciente"
        verbose_name_plural = "Logs de Registros de Pacientes"
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"Tentativa {self.attempt_number} - {self.submission.full_name}"


class GoogleFormsSync(models.Model):
    """
    Rastreia sincronizações do Google Forms
    """
    
    synced_at = models.DateTimeField(auto_now_add=True)
    
    # Totais
    total_new_responses = models.IntegerField(default=0)
    successfully_registered = models.IntegerField(default=0)
    duplicates_found = models.IntegerField(default=0)
    errors = models.IntegerField(default=0)
    
    # Status geral
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pendente'),
            ('running', 'Executando'),
            ('completed', 'Concluída'),
            ('failed', 'Falhou'),
        ],
        default='pending'
    )
    
    error_message = models.TextField(blank=True, null=True)
    duration_seconds = models.IntegerField(blank=True, null=True)
    
    class Meta:
        verbose_name = "Sincronização de Google Forms"
        verbose_name_plural = "Sincronizações de Google Forms"
        ordering = ['-synced_at']
    
    def __str__(self):
        return f"Sincronização {self.synced_at.strftime('%d/%m/%Y %H:%M:%S')} - {self.get_status_display()}"
