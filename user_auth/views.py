"""
Views de autenticação - Login e Logout
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from .user_manager import user_manager


@csrf_protect
@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    Tela de login.
    GET: Renderiza o formulário de login
    POST: Processa o login
    """
    # Se já está autenticado, redireciona para dashboard
    if request.session.get('user_authenticated'):
        return redirect('core:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        if not username or not password:
            return render(request, 'auth/login.html', {
                'error': 'Por favor, preencha todos os campos.'
            })
        
        # Tenta autenticar
        user = user_manager.authenticate(username, password)
        
        if user:
            # Login bem-sucedido
            user_manager.update_last_login(username)
            request.session['user_authenticated'] = True
            request.session['user'] = user
            request.session['username'] = username
            return redirect('core:dashboard')
        else:
            # Falha na autenticação
            return render(request, 'user_auth/login.html', {
                'error': 'Usuário ou senha inválidos.',
                'username': username
            })
    
    return render(request, 'user_auth/login.html')


def logout_view(request):
    """
    Logout - limpa a sessão e redireciona para o login
    """
    request.session.flush()
    return redirect('auth:login')


def profile_view(request):
    """
    Exibe o perfil do usuário logado
    """
    if not request.session.get('user_authenticated'):
        return redirect('auth:login')
    
    user = request.session.get('user', {})
    
    context = {
        'user': user,
    }
    
    return render(request, 'user_auth/profile.html', context)


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

@csrf_exempt
@require_POST
def delete_user_view(request):
    """
    Exclui um usuário (paciente ou admin) se o logado for administrador
    """
    if not request.session.get('user_authenticated'):
        return JsonResponse({'success': False, 'message': 'Usuário não autenticado.'}, status=403)

    user = request.session.get('user', {})
    # Verifica se o usuário é administrador
    if user.get('position') != 'Administrador' and user.get('role') != 'Administrador':
        return JsonResponse({'success': False, 'message': 'Apenas adms podem fazer isso.', 'is_admin': False}, status=403)

    # Tenta obter username/identificador de várias fontes
    username_to_delete = None
    
    # Primeiro tenta POST
    username_to_delete = request.POST.get('username')
    
    # Se não encontrou, tenta JSON no body
    if not username_to_delete:
        try:
            import json
            data = json.loads(request.body.decode('utf-8'))
            username_to_delete = data.get('username')
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            pass
    
    # Se ainda não encontrou, tenta GET
    if not username_to_delete:
        username_to_delete = request.GET.get('username')
    
    if not username_to_delete:
        return JsonResponse({'success': False, 'message': 'Usuário para exclusão não informado.'}, status=400)

    if username_to_delete == user.get('username'):
        return JsonResponse({'success': False, 'message': 'Você não pode excluir a si mesmo.'}, status=400)

    # Tenta deletar como paciente (User do banco de dados) primeiro
    from core.models import User as PatientUser
    from django.db.models import Q
    
    try:
        # Tenta encontrar por nome exato ou similar
        patient = PatientUser.objects.get(Q(name=username_to_delete) | Q(name__iexact=username_to_delete))
        patient.delete()
        return JsonResponse({'success': True, 'message': 'Paciente excluído com sucesso.'})
    except PatientUser.DoesNotExist:
        pass
    except PatientUser.MultipleObjectsReturned:
        return JsonResponse({'success': False, 'message': 'Múltiplos pacientes encontrados com esse nome.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao excluir paciente: {str(e)}'}, status=500)

    # Se não encontrou como paciente, tenta deletar como usuário admin
    deleted = user_manager.delete_user(username_to_delete)
    if deleted:
        return JsonResponse({'success': True, 'message': 'Usuário excluído com sucesso.'})
    else:
        return JsonResponse({'success': False, 'message': 'Usuário não encontrado.'}, status=404)
