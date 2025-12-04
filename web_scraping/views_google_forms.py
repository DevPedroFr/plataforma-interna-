"""
Vistas para gerenciar sincronização de Google Forms e registros de pacientes
"""

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views import View
import json
from django.utils import timezone

from .utils.browser_manager import BrowserManager
from .services.patient_registration_scraper import PatientRegistrationScraper
from .models import (
    ProcessedGoogleFormSubmission,
    GoogleFormsSync,
    PatientRegistrationLog
)
from core.google_forms_tasks import sync_google_forms_and_register_patients


@require_http_methods(["POST"])
@csrf_exempt
def trigger_google_forms_sync(request):
    """
    Dispara sincronização do Google Forms via API
    
    POST /api/web_scraping/sync-google-forms/
    """
    try:
        # Iniciar tarefa Celery
        task = sync_google_forms_and_register_patients.delay()
        
        return JsonResponse({
            'status': 'triggered',
            'message': 'Sincronização iniciada',
            'task_id': task.id
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao iniciar sincronização: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def sync_status(request):
    """
    Retorna status da última sincronização
    
    GET /api/web_scraping/sync-status/
    """
    try:
        last_sync = GoogleFormsSync.objects.order_by('-synced_at').first()
        
        if not last_sync:
            return JsonResponse({
                'status': 'no_sync',
                'message': 'Nenhuma sincronização realizada ainda'
            })
        
        return JsonResponse({
            'status': last_sync.status,
            'synced_at': last_sync.synced_at.isoformat(),
            'duration_seconds': last_sync.duration_seconds,
            'total_new_responses': last_sync.total_new_responses,
            'successfully_registered': last_sync.successfully_registered,
            'duplicates_found': last_sync.duplicates_found,
            'errors': last_sync.errors,
            'sync_id': last_sync.id
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao buscar status: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def processed_patients_list(request):
    """
    Lista os pacientes processados com filtros
    
    GET /api/web_scraping/processed-patients/
    Query params:
        - status: pending|processing|success|duplicate|error
        - limit: número de registros (padrão 50)
        - offset: para paginação
    """
    try:
        status_filter = request.GET.get('status', None)
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        query = ProcessedGoogleFormSubmission.objects.all()
        
        if status_filter:
            query = query.filter(status=status_filter)
        
        total_count = query.count()
        
        patients = query.order_by('-processed_at')[offset:offset+limit]
        
        data = []
        for patient in patients:
            data.append({
                'id': patient.id,
                'full_name': patient.full_name,
                'cpf': patient.cpf,
                'email': patient.email,
                'status': patient.status,
                'patient_id_in_platform': patient.patient_id_in_platform,
                'attempts': patient.attempts,
                'processed_at': patient.processed_at.isoformat(),
                'error_message': patient.error_message
            })
        
        return JsonResponse({
            'status': 'success',
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'patients': data
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao buscar pacientes: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def patient_detail(request, patient_id):
    """
    Retorna detalhes de um paciente processado
    
    GET /api/web_scraping/processed-patients/<id>/
    """
    try:
        patient = ProcessedGoogleFormSubmission.objects.get(id=patient_id)
        
        # Buscar logs
        logs = PatientRegistrationLog.objects.filter(
            submission=patient
        ).order_by('-timestamp')
        
        logs_data = []
        for log in logs:
            logs_data.append({
                'attempt': log.attempt_number,
                'step': log.step,
                'success': log.success,
                'message': log.message,
                'error_details': log.error_details,
                'timestamp': log.timestamp.isoformat()
            })
        
        return JsonResponse({
            'status': 'success',
            'patient': {
                'id': patient.id,
                'full_name': patient.full_name,
                'cpf': patient.cpf,
                'email': patient.email,
                'status': patient.status,
                'patient_id_in_platform': patient.patient_id_in_platform,
                'attempts': patient.attempts,
                'processed_at': patient.processed_at.isoformat(),
                'last_attempt_at': patient.last_attempt_at.isoformat() if patient.last_attempt_at else None,
                'error_message': patient.error_message,
                'raw_form_data': patient.raw_form_data,
            },
            'logs': logs_data
        })
    
    except ProcessedGoogleFormSubmission.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Paciente não encontrado'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao buscar detalhes: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@csrf_exempt
def retry_patient_registration(request, patient_id):
    """
    Retenta registrar um paciente que falhou
    
    POST /api/web_scraping/processed-patients/<id>/retry/
    """
    try:
        patient = ProcessedGoogleFormSubmission.objects.get(id=patient_id)
        
        if not patient.raw_form_data:
            return JsonResponse({
                'status': 'error',
                'message': 'Dados do formulário não disponíveis para retry'
            }, status=400)
        
        # Inicializar scraper
        browser = BrowserManager()
        browser.start_browser(headless=True)
        
        if not browser.driver:
            return JsonResponse({
                'status': 'error',
                'message': 'Falha ao inicializar navegador'
            }, status=500)
        
        try:
            scraper = PatientRegistrationScraper(browser)
            result = scraper.register_patient_from_google_forms(patient.raw_form_data)
            
            # Atualizar submission
            patient.attempts += 1
            patient.last_attempt_at = timezone.now()
            
            if result['success']:
                patient.status = 'success'
                patient.patient_id_in_platform = result.get('patient_id')
            else:
                if 'duplicado' in result['message'].lower() or 'já existe' in result['message'].lower():
                    patient.status = 'duplicate'
                else:
                    patient.status = 'error'
                    patient.error_message = result['message']
            
            patient.save()
            
            # Registrar tentativa
            PatientRegistrationLog.objects.create(
                submission=patient,
                attempt_number=patient.attempts,
                success=result['success'],
                message=result['message'],
                step='form_submit'
            )
            
            return JsonResponse({
                'status': 'success',
                'message': result['message'],
                'patient_status': patient.status
            })
        
        finally:
            browser.quit_browser()
    
    except ProcessedGoogleFormSubmission.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Paciente não encontrado'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao retenta registro: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
@staff_member_required
def dashboard(request):
    """
    Dashboard com estatísticas da sincronização
    
    GET /admin/web_scraping/dashboard/
    """
    try:
        # Estatísticas gerais
        total_submissions = ProcessedGoogleFormSubmission.objects.count()
        successful = ProcessedGoogleFormSubmission.objects.filter(status='success').count()
        duplicates = ProcessedGoogleFormSubmission.objects.filter(status='duplicate').count()
        errors = ProcessedGoogleFormSubmission.objects.filter(status='error').count()
        pending = ProcessedGoogleFormSubmission.objects.filter(status='pending').count()
        
        # Últimas sincronizações
        recent_syncs = GoogleFormsSync.objects.order_by('-synced_at')[:10]
        
        syncs_data = []
        for sync in recent_syncs:
            syncs_data.append({
                'id': sync.id,
                'synced_at': sync.synced_at.isoformat(),
                'status': sync.status,
                'total_new_responses': sync.total_new_responses,
                'successfully_registered': sync.successfully_registered,
                'duplicates_found': sync.duplicates_found,
                'errors': sync.errors,
                'duration_seconds': sync.duration_seconds
            })
        
        return JsonResponse({
            'status': 'success',
            'statistics': {
                'total_submissions': total_submissions,
                'successful': successful,
                'duplicates': duplicates,
                'errors': errors,
                'pending': pending,
            },
            'recent_syncs': syncs_data
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao carregar dashboard: {str(e)}'
        }, status=500)
