# core/views.py
from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import User, Appointment, Vaccine, ChatMessage
from django.db.models import Count
import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from web_scraping.services.calendar_scraper import CalendarScraper
from web_scraping.utils.browser_manager import BrowserManager
from user_auth.decorators import login_required
import calendar

@login_required
def dashboard(request):
    # Real data for dashboard
    today = timezone.now().date()
    total_appointments = Appointment.objects.count()
    total_users = User.objects.count()
    pending_chats = ChatMessage.objects.filter(needs_human=True, resolved=False).count()
    success_rate = 94  # Placeholder, calculate as needed

    # Get current user from session
    current_user = request.session.get('user', {})

    # Stock info
    vaccine_names = list(Vaccine.objects.values_list('name', flat=True))
    vaccine_stock = list(Vaccine.objects.values_list('current_stock', flat=True))
    vaccine_min_stock = list(Vaccine.objects.values_list('minimum_stock', flat=True))

    # Notifications (last 3 chat messages needing human)
    notifications = []
    for msg in ChatMessage.objects.filter(needs_human=True).order_by('-timestamp')[:3]:
        notifications.append({
            'name': msg.user.name if msg.user else 'Desconhecido',
            'type': 'Atendimento Humano',
            'time': msg.timestamp.strftime('%H:%M') if msg.timestamp else '',
            'priority': 'high',
        })

    # Recent users (last 20)
    recent_users = []
    for u in User.objects.order_by('-created_at')[:20]:
        recent_users.append({
            'name': u.name,
            'phone': u.phone,
            'vaccine': u.last_vaccine or '',
            'date': u.created_at.strftime('%d/%m/%Y') if u.created_at else '',
            'synced': u.synced,
        })

    # Appointments for calendar (next 30 days)
    appointments = Appointment.objects.filter(appointment_date__gte=today, appointment_date__lte=today+timedelta(days=30)).select_related('user', 'vaccine').order_by('appointment_date', 'appointment_time')
    appointments_list = []
    for a in appointments:
        appointments_list.append({
            'patient': a.user.name,
            'vaccine': a.vaccine.name if a.vaccine else 'Vacina não especificada',
            'date': a.appointment_date.strftime('%d/%m/%Y'),
            'time': a.appointment_time,
            'status': a.status,
        })

    # Dashboard metrics
    vaccines_applied = Appointment.objects.filter(status='completed').count()
    patients_registered = total_users
    stock_percentage = int((sum(vaccine_stock) / (sum(vaccine_min_stock) or 1)) * 100) if vaccine_min_stock else 0
    next_vaccinations = Appointment.objects.filter(appointment_date__gte=today).count()

    vaccines = Vaccine.objects.all()
    
    # Users for management - pacientes (patients)
    users_list = []
    for user in User.objects.all()[:10]:
        users_list.append({
            'name': user.name,
            'username': user.name.lower().replace(' ', '_'),  # Gera username a partir do nome
            'initials': user.name[:2].upper(),
            'role': 'Paciente'
        })

    context = {
        'total_appointments': total_appointments,
        'total_users': total_users,
        'pending_chats': pending_chats,
        'success_rate': success_rate,
        'vaccine_names': vaccine_names,
        'vaccine_stock': vaccine_stock,
        'vaccine_min_stock': vaccine_min_stock,
        'notifications': notifications,
        'recent_users': recent_users,
        'appointments': appointments_list,
        'vaccines_applied': vaccines_applied,
        'patients_registered': patients_registered,
        'stock_percentage': stock_percentage,
        'next_vaccinations': next_vaccinations,
        'vaccines': vaccines,
        'users': users_list,
        'current_user': current_user,
    }
    return render(request, 'main_dashboard.html', context)

@method_decorator(csrf_exempt, name='dispatch')
class SyncCalendarView(View):
    def post(self, request):
        try:
            browser_manager = BrowserManager()
            calendar_scraper = CalendarScraper(browser_manager)
            
            appointments = calendar_scraper.scrape_calendar()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Calendário sincronizado com sucesso. {len(appointments)} agendamentos encontrados.',
                'appointments_count': len(appointments)
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Erro ao sincronizar calendário: {str(e)}'
            }, status=500)

class CalendarAppointmentsView(View):
    def get(self, request):
        try:
            # Filtra por mês atual ou parâmetro específico
            month = request.GET.get('month')
            year = request.GET.get('year')
            
            appointments = Appointment.objects.all()
            
            if month and year:
                appointments = appointments.filter(
                    appointment_date__month=month,
                    appointment_date__year=year
                )
            else:
                # Mês atual por padrão
                today = datetime.now()
                appointments = appointments.filter(
                    appointment_date__month=today.month,
                    appointment_date__year=today.year
                )
            
            appointments_data = []
            for appointment in appointments:
                appointments_data.append({
                    'id': appointment.id,
                    'patient': appointment.user.name,
                    'vaccine': appointment.vaccine.name if appointment.vaccine else 'Vacina não especificada',
                    'date': appointment.appointment_date.strftime('%d/%m/%Y'),
                    'time': appointment.appointment_time,
                    'status': appointment.get_status_display(),
                    'status_raw': appointment.status,
                    'observations': appointment.observations
                })
            
            return JsonResponse({
                'status': 'success',
                'appointments': appointments_data
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Erro ao carregar agendamentos: {str(e)}'
            }, status=500)

def calendar_view(request):
    # Obtém o mês e ano atual
    today = timezone.now().date()
    year = request.GET.get('year', today.year)
    month = request.GET.get('month', today.month)
    
    try:
        year = int(year)
        month = int(month)
    except (ValueError, TypeError):
        year = today.year
        month = today.month
    
    # Cria o calendário
    cal = calendar.Calendar(firstweekday=6)  # Domingo como primeiro dia
    month_days = cal.monthdayscalendar(year, month)
    
    # Obtém agendamentos do mês atual
    appointments = Appointment.objects.filter(
        appointment_date__year=year,
        appointment_date__month=month
    ).select_related('user', 'vaccine')
    
    # Organiza agendamentos por dia
    appointments_by_day = {}
    for appointment in appointments:
        day = appointment.appointment_date.day
        if day not in appointments_by_day:
            appointments_by_day[day] = []
        appointments_by_day[day].append(appointment)
    
    # Agendamentos de hoje
    today_appointments = Appointment.objects.filter(
        appointment_date=today
    ).select_related('user', 'vaccine').order_by('appointment_time')
    
    # Todos os usuários e vacinas para os selects do modal
    all_users = User.objects.all()
    vaccines = Vaccine.objects.all()
    
    context = {
        'month_days': month_days,
        'current_year': year,
        'current_month': month,
        'current_month_name': calendar.month_name[month],
        'today': today,
        'appointments_by_day': appointments_by_day,
        'today_appointments': today_appointments,
        'prev_month': month - 1 if month > 1 else 12,
        'prev_year': year if month > 1 else year - 1,
        'next_month': month + 1 if month < 12 else 1,
        'next_year': year if month < 12 else year + 1,
        'all_users': all_users,
        'vaccines': vaccines,
        'appointments': appointments,
    }
    
    return render(request, 'core/calendar.html', context)

def users_view(request):
    # Dados mock para usuários
    users = [
        {
            'name': 'Maria Silva',
            'phone': '(11) 98765-4321',
            'cpf': '123.456.789-00',
            'birth_date': '15/03/1985',
            'source': 'Chatbot',
            'status': 'synced'
        },
        {
            'name': 'João Santos',
            'phone': '(11) 97654-3210',
            'cpf': '234.567.890-11',
            'birth_date': '22/07/1990',
            'source': 'Chatbot',
            'status': 'synced'
        },
        {
            'name': 'Ana Costa',
            'phone': '(11) 96543-2109',
            'cpf': '345.678.901-22',
            'birth_date': '10/11/1988',
            'source': 'Manual',
            'status': 'pending'
        },
        {
            'name': 'Carlos Oliveira',
            'phone': '(11) 95432-1098',
            'cpf': '456.789.012-33',
            'birth_date': '05/05/1992',
            'source': 'Chatbot',
            'status': 'synced'
        },
        {
            'name': 'Fernanda Lima',
            'phone': '(11) 94321-0987',
            'cpf': '567.890.123-44',
            'birth_date': '18/09/1987',
            'source': 'Chatbot',
            'status': 'synced'
        },
    ]
    
    context = {
        'users': users,
    }
    return render(request, 'users.html', context)

def whatsapp_view(request):
    # Dados mock para WhatsApp
    conversations = [
        {
            'name': 'Maria Silva',
            'time': '14:30',
            'last_message': 'Preciso de atendimento humano...',
            'priority': 'high',
            'unread': True,
            'active': True
        },
        {
            'name': 'João Santos',
            'time': '15:45',
            'last_message': 'Erro ao agendar...',
            'priority': 'medium',
            'unread': True,
            'active': False
        },
        {
            'name': 'Ana Costa',
            'time': '16:20',
            'last_message': 'Tenho uma dúvida sobre...',
            'priority': 'low',
            'unread': True,
            'active': False
        },
    ]
    
    chat_messages = [
        {'sender': 'client', 'message': 'Olá, gostaria de agendar uma vacina', 'time': '14:25'},
        {'sender': 'bot', 'message': 'Olá! Claro, posso te ajudar. Qual vacina você gostaria de agendar?', 'time': '14:25'},
        {'sender': 'client', 'message': 'COVID-19, por favor', 'time': '14:26'},
        {'sender': 'bot', 'message': 'Perfeito! Para qual data você gostaria de agendar?', 'time': '14:26'},
        {'sender': 'client', 'message': 'Amanhã, se possível', 'time': '14:27'},
        {'sender': 'bot', 'message': 'Tenho os seguintes horários disponíveis para amanhã (23/10):<br><br>• 09:00<br>• 11:00<br>• 14:30<br>• 16:00<br><br>Qual horário prefere?', 'time': '14:27'},
        {'sender': 'client', 'message': 'Na verdade, estou com dúvidas sobre o pagamento. Preciso falar com alguém', 'time': '14:30'},
        {'sender': 'bot', 'message': '⚠️ Atendimento Humano Solicitado<br><br>O cliente solicitou atendimento humano sobre dúvidas de pagamento.<br><br>Um atendente será notificado em breve.', 'time': '14:30', 'urgent': True},
    ]
    
    context = {
        'conversations': conversations,
        'chat_messages': chat_messages,
        'active_conversation': 'Maria Silva'
    }
    return render(request, 'whatsapp.html', context)

# ===================== NOVAS VIEWS PARA AGENDAMENTOS =====================

@require_http_methods(["POST"])
def create_appointment(request):
    """Cria um novo agendamento"""
    try:
        appointment_date = request.POST.get('appointment_date')
        appointment_time = request.POST.get('appointment_time')
        user_id = request.POST.get('user_id')
        vaccine_id = request.POST.get('vaccine_id')
        dose = request.POST.get('dose', '')
        status = request.POST.get('status', 'scheduled')
        observations = request.POST.get('observations', '')
        
        # Validações
        if not all([appointment_date, appointment_time, user_id, vaccine_id]):
            return JsonResponse({
                'status': 'error',
                'message': 'Campos obrigatórios não preenchidos'
            }, status=400)
        
        try:
            user = User.objects.get(id=user_id)
            vaccine = Vaccine.objects.get(id=vaccine_id)
        except (User.DoesNotExist, Vaccine.DoesNotExist):
            return JsonResponse({
                'status': 'error',
                'message': 'Paciente ou vacina não encontrados'
            }, status=404)
        
        # Cria o agendamento
        appointment = Appointment.objects.create(
            user=user,
            vaccine=vaccine,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            dose=dose,
            status=status,
            observations=observations
        )
        
        return JsonResponse({
            'status': 'success',
            'message': 'Agendamento criado com sucesso',
            'appointment_id': appointment.id
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao criar agendamento: {str(e)}'
        }, status=500)

@require_http_methods(["GET"])
def get_appointment(request, appointment_id):
    """Obtém detalhes de um agendamento específico"""
    try:
        appointment = Appointment.objects.select_related('user', 'vaccine').get(id=appointment_id)
        
        return JsonResponse({
            'status': 'success',
            'appointment': {
                'id': appointment.id,
                'user_name': appointment.user.name,
                'user_phone': appointment.user.phone,
                'vaccine_name': appointment.vaccine.name if appointment.vaccine else 'N/A',
                'appointment_date': appointment.appointment_date.strftime('%d/%m/%Y'),
                'appointment_time': appointment.appointment_time,
                'dose': appointment.dose,
                'status': appointment.status,
                'observations': appointment.observations,
            }
        })
    
    except Appointment.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Agendamento não encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao buscar agendamento: {str(e)}'
        }, status=500)

@require_http_methods(["POST"])
def update_appointment(request, appointment_id):
    """Atualiza um agendamento existente"""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        
        # Atualiza os campos fornecidos
        if 'appointment_date' in request.POST:
            appointment.appointment_date = request.POST.get('appointment_date')
        if 'appointment_time' in request.POST:
            appointment.appointment_time = request.POST.get('appointment_time')
        if 'vaccine_id' in request.POST:
            try:
                vaccine = Vaccine.objects.get(id=request.POST.get('vaccine_id'))
                appointment.vaccine = vaccine
            except Vaccine.DoesNotExist:
                pass
        if 'dose' in request.POST:
            appointment.dose = request.POST.get('dose')
        if 'status' in request.POST:
            appointment.status = request.POST.get('status')
        if 'observations' in request.POST:
            appointment.observations = request.POST.get('observations')
        
        appointment.save()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Agendamento atualizado com sucesso'
        })
    
    except Appointment.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Agendamento não encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao atualizar agendamento: {str(e)}'
        }, status=500)

@require_http_methods(["POST"])
def delete_appointment(request, appointment_id):
    """Deleta um agendamento"""
    try:
        appointment = Appointment.objects.get(id=appointment_id)
        appointment.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': 'Agendamento deletado com sucesso'
        })
    
    except Appointment.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Agendamento não encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao deletar agendamento: {str(e)}'
        }, status=500)

@require_http_methods(["GET"])
def list_appointments_by_date(request):
    """Lista agendamentos por data"""
    try:
        date = request.GET.get('date')
        
        if not date:
            return JsonResponse({
                'status': 'error',
                'message': 'Data não fornecida'
            }, status=400)
        
        appointments = Appointment.objects.filter(
            appointment_date=date
        ).select_related('user', 'vaccine').order_by('appointment_time')
        
        appointments_data = []
        for appointment in appointments:
            appointments_data.append({
                'id': appointment.id,
                'user_name': appointment.user.name,
                'vaccine_name': appointment.vaccine.name if appointment.vaccine else 'N/A',
                'appointment_time': appointment.appointment_time,
                'status': appointment.status,
            })
        
        return JsonResponse({
            'status': 'success',
            'appointments': appointments_data,
            'count': len(appointments_data)
        })
    
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Erro ao listar agendamentos: {str(e)}'
        }, status=500)