import os
import json
import datetime
import glob
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
except Exception:
    # The import will fail until requirements are installed. We handle it at runtime.
    service_account = None
    build = None


class Command(BaseCommand):
    help = 'Collect Google Forms responses and save as JSON locally.'

    def add_arguments(self, parser):
        parser.add_argument('form_id', help='Google Form ID (from URL).')
        parser.add_argument('--service-account', dest='service_account', help='Path to service account JSON file. If not provided, uses GOOGLE_SERVICE_ACCOUNT_FILE env var or settings.GOOGLE_SERVICE_ACCOUNT_FILE.')
        parser.add_argument('--outdir', dest='outdir', default='forms_responses', help='Output directory to save JSON (default: forms_responses).')

    def handle(self, *args, **options):
        if service_account is None or build is None:
            raise CommandError('Missing Google API libraries. Install requirements: `pip install -r requirements.txt`.')

        form_id = options['form_id']
        sa = options.get('service_account') or os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE') or getattr(settings, 'GOOGLE_SERVICE_ACCOUNT_FILE', None)
        if not sa:
            raise CommandError('Service account JSON file path not provided. Set --service-account or env GOOGLE_SERVICE_ACCOUNT_FILE or settings.GOOGLE_SERVICE_ACCOUNT_FILE.')

        if not os.path.isfile(sa):
            raise CommandError(f'Service account file not found: {sa}')

        scopes = ['https://www.googleapis.com/auth/forms.responses.readonly']
        try:
            creds = service_account.Credentials.from_service_account_file(sa, scopes=scopes)
            service = build('forms', 'v1', credentials=creds)
        except Exception as e:
            raise CommandError(f'Error creating Google Forms client: {e}')

        try:
            # The Forms API returns a dictionary; this lists responses
            results = service.forms().responses().list(formId=form_id).execute()
        except Exception as e:
            raise CommandError(f'Error fetching responses from Forms API: {e}')

        outdir = options['outdir']
        os.makedirs(outdir, exist_ok=True)
        ts = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        filename = f'{form_id}_responses_{ts}.json'
        path = os.path.join(outdir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        self.stdout.write(self.style.SUCCESS(f'Saved responses to {path}'))
        
        # Apagar arquivos JSON antigos, mantendo apenas o mais recente
        self._cleanup_old_responses(outdir, filename)
    
    def _cleanup_old_responses(self, outdir, current_filename):
        """
        Remove arquivos JSON antigos do diretório, mantendo apenas o mais recente.
        
        Args:
            outdir: Diretório contendo os arquivos JSON
            current_filename: Nome do arquivo atual (não será deletado)
        """
        try:
            # Encontrar todos os arquivos JSON no diretório
            json_files = glob.glob(os.path.join(outdir, '*.json'))
            
            # Se houver mais de um arquivo, deletar os antigos
            if len(json_files) > 1:
                # Remover o arquivo atual da lista
                json_files = [f for f in json_files if os.path.basename(f) != current_filename]
                
                # Ordenar por data de modificação (mais antigos primeiro)
                json_files.sort(key=lambda x: os.path.getmtime(x))
                
                # Deletar todos os arquivos antigos
                for old_file in json_files:
                    try:
                        os.remove(old_file)
                        self.stdout.write(self.style.WARNING(f'Arquivo antigo removido: {os.path.basename(old_file)}'))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'Erro ao remover {old_file}: {e}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Erro durante limpeza de arquivos antigos: {e}'))
