"""
Decoradores para proteção de views que requerem autenticação
"""

from functools import wraps
from django.shortcuts import redirect
from django.http import JsonResponse


def login_required(view_func):
    """
    Decorador que protege uma view exigindo autenticação.
    Redireciona para login se não estiver autenticado.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_authenticated'):
            # Se for requisição AJAX, retorna JSON
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Não autenticado'
                }, status=401)
            return redirect('auth:login')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def position_required(required_positions):
    """
    Decorador que protege uma view exigindo um cargo específico.
    
    Uso:
        @position_required(['Administrador', 'Gerente'])
        def my_view(request):
            ...
    """
    if isinstance(required_positions, str):
        required_positions = [required_positions]
    
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.session.get('user_authenticated'):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Não autenticado'
                    }, status=401)
                return redirect('auth:login')
            
            user = request.session.get('user', {})
            user_position = user.get('position', '')
            
            if user_position not in required_positions:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Permissão insuficiente'
                    }, status=403)
                return render(request, 'auth/permission_denied.html', {
                    'user': user
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    
    return decorator
