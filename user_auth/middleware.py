"""
Middleware de autenticação que redireciona para login se necessário
"""

from django.shortcuts import redirect
from django.conf import settings


class AuthenticationMiddleware:
    """
    Middleware que protege as rotas exigindo autenticação.
    Rotas públicas (login, logout) são isentas.
    """
    
    # Rotas que não requerem autenticação
    PUBLIC_URLS = [
        '/auth/login/',
        '/auth/logout/',
        '/admin/',  # O Django admin cuida da própria autenticação
    ]
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Verifica se a URL atual é pública
        is_public = any(request.path.startswith(url) for url in self.PUBLIC_URLS)
        
        # Se não é pública e não está autenticado, redireciona para login
        if not is_public and not request.session.get('user_authenticated'):
            return redirect('auth:login')
        
        response = self.get_response(request)
        return response
