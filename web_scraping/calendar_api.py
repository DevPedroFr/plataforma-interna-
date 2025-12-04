from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .utils.browser_manager import BrowserManager
from .services.calendar_scraper import CalendarScraper
from core.models import Appointment
from datetime import timedelta
from django.utils import timezone

@require_http_methods(["POST"])
@csrf_exempt
def sync_calendar(request):
    """Sincroniza agendamentos do calendário externo."""
    try:
        browser = BrowserManager()
        browser.start_browser(headless=True)
        scraper = CalendarScraper(browser)
        scraper.scrape_calendar()
        browser.quit_browser()
        # Retorna os agendamentos mais recentes para exibir na tela
        today = timezone.now().date()
        appointments = Appointment.objects.filter(appointment_date__gte=today, appointment_date__lte=today+timedelta(days=30)).select_related('user', 'vaccine').order_by('appointment_date', 'appointment_time')
        appointments_list = []
        for a in appointments:
            appointments_list.append({
                'patient': a.user.name,
                'vaccine': a.vaccine.name if a.vaccine else '',
                'date': a.appointment_date.strftime('%d/%m/%Y'),
                'time': a.appointment_time,
                'status': a.status,
            })
        return JsonResponse({
            'status': 'success',
            'message': 'Agendamentos sincronizados com sucesso',
            'appointments': appointments_list
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro na sincronização: {str(e)}'
        }, status=500)
