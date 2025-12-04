import os
import json
import logging
from datetime import datetime
from pathlib import Path
from celery import shared_task
from django.conf import settings

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except ImportError:
    service_account = None
    build = None

logger = logging.getLogger(__name__)


@shared_task
def collect_google_forms_responses():
    """
    ⚠️ DEPRECATED: Esta task apenas coleta dados e salva JSON localmente.
    
    Use 'core.google_forms_tasks.sync_google_forms_and_register_patients' 
    para o fluxo completo (coleta + registro no sistema legado).
    
    Esta task será removida em versões futuras.
    """
    logger.warning(
        "⚠️ DEPRECATED: collect_google_forms_responses() apenas salva JSON. "
        "Use sync_google_forms_and_register_patients() para registro automático no sistema legado."
    )
    if service_account is None or build is None:
        logger.error('Google API libraries not installed. Install: pip install -r requirements.txt')
        return {'status': 'error', 'message': 'Missing Google API libraries'}

    # Configurações vindas de settings ou env vars
    service_account_file = getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_FILE', None) or os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
    sheet_id = getattr(settings, 'GOOGLE_SHEET_ID', None) or os.environ.get('GOOGLE_SHEET_ID')
    sheet_name = getattr(settings, 'GOOGLE_SHEET_NAME', 'Respostas do formulário') or os.environ.get('GOOGLE_SHEET_NAME', 'Respostas do formulário')

    if not service_account_file:
        logger.error('GOOGLE_SERVICE_ACCOUNT_FILE not configured in settings or env')
        return {'status': 'error', 'message': 'Service account file not configured'}

    if not sheet_id:
        logger.error('GOOGLE_SHEET_ID not configured in settings or env')
        return {'status': 'error', 'message': 'Sheet ID not configured'}

    # Resolver caminho relativo (ex: se arquivo está no diretório raiz do projeto)
    if not os.path.isabs(service_account_file):
        service_account_file = os.path.join(settings.BASE_DIR, service_account_file)
    
    logger.info(f'Looking for service account file at: {service_account_file}')

    if not os.path.isfile(service_account_file):
        logger.error(f'Service account file not found: {service_account_file}')
        return {'status': 'error', 'message': f'Service account file not found: {service_account_file}'}

    try:
        logger.info(f'Starting to collect Google Forms responses from sheet: {sheet_id}')
        
        # Autenticação
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = service_account.Credentials.from_service_account_file(service_account_file, scopes=scopes)
        service = build('sheets', 'v4', credentials=creds)
        logger.info('Successfully authenticated with Google Sheets API')

        # Ler dados da planilha
        # Tentar primeiro pegar todas as abas para encontrar a correta
        spreadsheet = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets = spreadsheet.get('sheets', [])
        
        # Procurar pela aba com o nome desejado (case-insensitive)
        target_sheet = None
        for sheet in sheets:
            if sheet['properties']['title'].lower() == sheet_name.lower():
                target_sheet = sheet
                break
        
        if not target_sheet:
            logger.error(f'Sheet "{sheet_name}" not found in spreadsheet. Available sheets: {[s["properties"]["title"] for s in sheets]}')
            return {'status': 'error', 'message': f'Sheet "{sheet_name}" not found in spreadsheet'}
        
        # Usar A1 notation sem aspas para a primeira aba ou com !A:Z
        sheet_title = target_sheet['properties']['title']
        range_spec = f"{sheet_title}!A:Z"
        
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_spec
        ).execute()

        rows = result.get('values', [])
        if not rows:
            logger.warning('No data found in Google Sheet')
            return {'status': 'warning', 'message': 'No data found in sheet', 'rows_count': 0}

        # Converter para formato JSON estruturado
        headers = rows[0] if rows else []
        data = []
        for row in rows[1:]:
            # Preencher colunas faltantes com valores vazios
            while len(row) < len(headers):
                row.append('')
            record = dict(zip(headers, row))
            data.append(record)

        # Criar diretório de saída se não existir
        output_dir = getattr(settings, 'FORMS_RESPONSES_DIR', 'forms_responses')
        os.makedirs(output_dir, exist_ok=True)

        # Salvar JSON com timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'google_forms_responses_{timestamp}.json'
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f'Successfully saved {len(data)} responses to {filepath}')
        return {
            'status': 'success',
            'message': f'Collected {len(data)} responses',
            'rows_count': len(data),
            'file': filepath
        }

    except Exception as e:
        logger.exception(f'Error collecting Google Forms responses: {e}')
        return {'status': 'error', 'message': str(e)}
