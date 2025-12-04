import os
import sys
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vacination_system.settings')

app = Celery('vacination_system')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Windows compatibility: use solo or threads pool instead of prefork
if sys.platform == 'win32':
    app.conf.update(
        worker_pool='solo',  # Use solo pool on Windows
        worker_prefetch_multiplier=1,
    )

app.autodiscover_tasks()

# Configuração do Celery Beat (tarefas agendadas)
app.conf.beat_schedule = {
    # Task principal: Coleta do Google Forms E registra no sistema legado
    'sync-google-forms-and-register-patients': {
        'task': 'core.google_forms_tasks.sync_google_forms_and_register_patients',
        'schedule': 60.0,  # A cada 1 minuto (60 segundos)
        # Opções alternativas:
        # 'schedule': 300.0,  # A cada 5 minutos
        # 'schedule': crontab(minute=0),  # A cada hora
        # 'schedule': crontab(hour=0, minute=0),  # Diariamente à meia-noite
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
