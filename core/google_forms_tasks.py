"""
Tarefa Celery para sincronização de Google Forms com cadastro automático de pacientes
"""

import os
import json
import logging
import time
import glob
from datetime import datetime, timedelta
from pathlib import Path
from celery import shared_task
from django.conf import settings
from django.utils import timezone

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    service_account = None
    build = None

from web_scraping.utils.browser_manager import BrowserManager
from web_scraping.services.patient_registration_scraper import PatientRegistrationScraper
from web_scraping.models import (
    ProcessedGoogleFormSubmission,
    PatientRegistrationLog,
    GoogleFormsSync
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_google_forms_and_register_patients(self):
    """
    Sincroniza respostas do Google Forms e registra automaticamente os pacientes
    na plataforma GoC Franquias.
    
    Flow:
    1. Coleta respostas do Google Forms
    2. Para cada resposta nova:
       - Valida dados
       - Verifica duplicata por CPF
       - Faz login e preenche formulário automaticamente
       - Registra resultado
    
    Retorno:
        dict com estatísticas da sincronização
    """
    
    sync_record = None
    browser = None
    start_time = datetime.now()
    
    try:
        # Criar registro de sincronização
        sync_record = GoogleFormsSync.objects.create(
            status='running'
        )
        logger.info(f"Iniciando sincronização #{sync_record.id}")
        
        # 1. Coletar respostas do Google Forms
        forms_responses = _collect_google_forms_responses()
        if not forms_responses:
            logger.warning("Nenhuma resposta encontrada no Google Forms")
            sync_record.status = 'completed'
            sync_record.total_new_responses = 0
            sync_record.save()
            return {
                'status': 'completed',
                'message': 'Nenhuma resposta encontrada',
                'sync_id': sync_record.id
            }
        
        logger.info(f"Encontradas {len(forms_responses)} respostas no Google Forms")
        
        # 2. Inicializar browser
        browser = BrowserManager()
        browser.start_browser(headless=True)
        
        if not browser.driver:
            raise Exception("Falha ao inicializar navegador após 3 tentativas")
        
        # 3. Processar cada resposta
        scraper = PatientRegistrationScraper(browser)
        
        successfully_registered = 0
        duplicates_found = 0
        errors = 0
        
        for form_data in forms_responses:
            try:
                cpf = form_data.get('CPF', '').strip()
                email = form_data.get('E-mail', '').strip()
                full_name = form_data.get('Nome completo', '').strip()
                
                if not cpf:
                    logger.warning(f"Resposta sem CPF - pulando")
                    continue
                
                # Verificar se já foi processada
                submission, created = ProcessedGoogleFormSubmission.objects.get_or_create(
                    cpf=cpf,
                    defaults={
                        'email': email,
                        'full_name': full_name,
                        'raw_form_data': form_data,
                        'status': 'pending'
                    }
                )
                
                if not created and submission.status in ['success', 'duplicate']:
                    logger.info(f"CPF {cpf} já foi processado - pulando")
                    duplicates_found += 1
                    continue
                
                # Atualizar status para processando
                submission.status = 'processing'
                submission.attempts += 1
                submission.last_attempt_at = timezone.now()
                submission.save()
                
                logger.info(f"Processando: {full_name} (CPF: {cpf})")
                
                # Registrar paciente
                result = scraper.register_patient_from_google_forms(form_data)
                
                # Registrar tentativa
                PatientRegistrationLog.objects.create(
                    submission=submission,
                    attempt_number=submission.attempts,
                    success=result['success'],
                    message=result['message'],
                    step='form_submit'
                )
                
                if result['success']:
                    submission.status = 'success'
                    submission.patient_id_in_platform = result.get('patient_id')
                    successfully_registered += 1
                    logger.info(f"✅ Paciente {full_name} registrado com sucesso (ID: {result.get('patient_id')})")
                else:
                    # Verificar se é duplicata
                    if 'duplicado' in result['message'].lower() or 'já existe' in result['message'].lower():
                        submission.status = 'duplicate'
                        duplicates_found += 1
                        logger.warning(f"⚠️ Paciente {full_name} - Duplicata detectada")
                    else:
                        submission.status = 'error'
                        submission.error_message = result['message']
                        errors += 1
                        logger.error(f"❌ Erro ao registrar {full_name}: {result['message']}")
                
                submission.save()
                
                # Pequeno delay entre registros
                time.sleep(2)
                
            except Exception as e:
                logger.exception(f"Erro ao processar CPF {cpf}: {str(e)}")
                errors += 1
                
                try:
                    submission.status = 'error'
                    submission.error_message = str(e)
                    submission.save()
                    
                    PatientRegistrationLog.objects.create(
                        submission=submission,
                        attempt_number=submission.attempts,
                        success=False,
                        message=f"Erro durante processamento",
                        error_details=str(e),
                        step='form_submit'
                    )
                except:
                    pass
        
        # Atualizar registro de sincronização
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        sync_record.status = 'completed'
        sync_record.total_new_responses = len(forms_responses)
        sync_record.successfully_registered = successfully_registered
        sync_record.duplicates_found = duplicates_found
        sync_record.errors = errors
        sync_record.duration_seconds = int(duration)
        sync_record.save()
        
        logger.info(
            f"Sincronização concluída: "
            f"{successfully_registered} registrados, "
            f"{duplicates_found} duplicatas, "
            f"{errors} erros em {duration:.1f}s"
        )
        
        # Limpar arquivos JSON antigos
        _cleanup_old_json_responses()
        
        return {
            'status': 'completed',
            'sync_id': sync_record.id,
            'total_processed': len(forms_responses),
            'successfully_registered': successfully_registered,
            'duplicates_found': duplicates_found,
            'errors': errors,
            'duration_seconds': int(duration)
        }
        
    except Exception as e:
        logger.exception(f"Erro geral na sincronização: {str(e)}")
        
        if sync_record:
            sync_record.status = 'failed'
            sync_record.error_message = str(e)
            sync_record.save()
        
        # Retry com backoff
        raise self.retry(exc=e, countdown=60)
    
    finally:
        if browser:
            try:
                browser.quit_browser()
            except:
                pass


def _collect_google_forms_responses():
    """
    Coleta respostas do Google Forms via Google Sheets API
    
    Returns:
        list: Lista de dicionários com dados das respostas
    """
    
    if service_account is None or build is None:
        logger.error('Google API libraries not installed')
        return []
    
    try:
        service_account_file = getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_FILE', None) or os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
        sheet_id = getattr(settings, 'GOOGLE_SHEET_ID', None) or os.environ.get('GOOGLE_SHEET_ID')
        sheet_name = getattr(settings, 'GOOGLE_SHEET_NAME', 'Respostas do formulário') or os.environ.get('GOOGLE_SHEET_NAME', 'Respostas do formulário')
        
        if not service_account_file or not sheet_id:
            logger.error('Google Forms configuration missing')
            return []
        
        # Resolver caminho
        if not os.path.isabs(service_account_file):
            service_account_file = os.path.join(settings.BASE_DIR, service_account_file)
        
        if not os.path.isfile(service_account_file):
            logger.error(f'Service account file not found: {service_account_file}')
            return []
        
        # Autenticar
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = service_account.Credentials.from_service_account_file(service_account_file, scopes=scopes)
        service = build('sheets', 'v4', credentials=creds)
        
        # Encontrar aba correta
        spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets = spreadsheet.get('sheets', [])
        
        target_sheet = None
        for sheet in sheets:
            if sheet['properties']['title'].lower() == sheet_name.lower():
                target_sheet = sheet
                break
        
        if not target_sheet:
            logger.error(f'Sheet "{sheet_name}" not found')
            return []
        
        # Ler dados
        sheet_title = target_sheet['properties']['title']
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=f"{sheet_title}!A:Z"
        ).execute()
        
        rows = result.get('values', [])
        if not rows:
            return []
        
        # Converter para dicionários
        headers = rows[0]
        data = []
        for row in rows[1:]:
            while len(row) < len(headers):
                row.append('')
            data.append(dict(zip(headers, row)))
        
        # Remover duplicatas por CPF, mantendo a resposta mais recente
        data = _deduplicate_by_cpf(data)
        
        logger.info(f"Coletadas {len(data)} respostas únicas do Google Forms")
        return data
        
    except Exception as e:
        logger.exception(f"Erro ao coletar respostas do Google Forms: {str(e)}")
        return []


def _deduplicate_by_cpf(responses):
    """
    Remove duplicatas por CPF, mantendo apenas a resposta mais recente.
    
    Args:
        responses: Lista de dicionários com dados das respostas
        
    Returns:
        list: Lista sem duplicatas (apenas a última resposta de cada CPF)
    """
    if not responses:
        return []
    
    # Dicionário para armazenar a última resposta de cada CPF
    unique_by_cpf = {}
    skipped_empty_cpf = 0
    duplicates_removed = 0
    
    for response in responses:
        cpf = response.get('CPF', '').strip()
        
        # Se não tem CPF, pula (será tratado no processamento)
        if not cpf:
            skipped_empty_cpf += 1
            continue
        
        # Normalizar CPF (remover pontos, traços, espaços)
        cpf_normalized = ''.join(filter(str.isdigit, cpf))
        
        if cpf_normalized in unique_by_cpf:
            duplicates_removed += 1
            logger.debug(f"Duplicata removida: CPF {cpf_normalized}")
        
        # Sempre sobrescreve com a última resposta (mais recente)
        unique_by_cpf[cpf_normalized] = response
    
    result = list(unique_by_cpf.values())
    
    if duplicates_removed > 0:
        logger.info(f"Duplicatas removidas: {duplicates_removed} (mantidas {len(result)} respostas únicas)")
    
    if skipped_empty_cpf > 0:
        logger.warning(f"Respostas sem CPF ignoradas: {skipped_empty_cpf}")
    
    return result


@shared_task
def cleanup_old_sync_logs():
    """
    Remove registros de sincronização antigos (> 30 dias)
    Executar periodicamente para manter banco de dados limpo
    """
    
    cutoff_date = timezone.now() - timedelta(days=30)
    
    old_logs = PatientRegistrationLog.objects.filter(timestamp__lt=cutoff_date)
    count, _ = old_logs.delete()
    
    logger.info(f"Limpeza: {count} logs antigos removidos")
    
    return {'deleted_count': count}


def _cleanup_old_json_responses(forms_responses_dir='forms_responses'):
    """
    Remove arquivos JSON antigos do diretório de respostas do formulário,
    mantendo apenas o mais recente.
    
    Args:
        forms_responses_dir: Diretório contendo os arquivos JSON (relativo a BASE_DIR)
    """
    try:
        # Resolver caminho absoluto
        if not os.path.isabs(forms_responses_dir):
            forms_responses_dir = os.path.join(settings.BASE_DIR, forms_responses_dir)
        
        if not os.path.isdir(forms_responses_dir):
            logger.warning(f"Diretório não encontrado: {forms_responses_dir}")
            return
        
        # Encontrar todos os arquivos JSON no diretório
        json_files = glob.glob(os.path.join(forms_responses_dir, '*.json'))
        
        # Se houver mais de um arquivo, deletar os antigos
        if len(json_files) > 1:
            # Ordenar por data de modificação (mais antigos primeiro)
            json_files.sort(key=lambda x: os.path.getmtime(x))
            
            # Deletar todos os arquivos antigos, exceto o mais recente
            for old_file in json_files[:-1]:
                try:
                    os.remove(old_file)
                    logger.info(f"Arquivo antigo removido: {os.path.basename(old_file)}")
                except Exception as e:
                    logger.error(f"Erro ao remover {old_file}: {e}")
    except Exception as e:
        logger.exception(f"Erro durante limpeza de arquivos JSON antigos: {str(e)}")
