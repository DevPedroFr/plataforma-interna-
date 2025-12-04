from django.urls import path
from . import views

urlpatterns = [
    path('webhook/whatsapp/', views.webhook_whatsapp, name='webhook_whatsapp'),
    path('dashboard/', views.dashboard, name='chatbot_dashboard'),
]