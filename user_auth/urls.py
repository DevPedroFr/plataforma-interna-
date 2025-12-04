"""
URLs de autenticação
"""

from django.urls import path
from . import views

app_name = 'auth'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('delete_user/', views.delete_user_view, name='delete_user'),
]
