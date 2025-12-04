# vaccination_system/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

def home_redirect(request):
    """Redireciona para dashboard se autenticado, senão para login"""
    if request.session.get('user_authenticated'):
        return RedirectView.as_view(url='/')(request)
    return RedirectView.as_view(url='auth/login/')(request)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('user_auth.urls')),
    path('', include('core.urls')),
    path('scraping/', include('web_scraping.urls')),
]