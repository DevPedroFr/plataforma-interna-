"""
Script para criar pacientes de exemplo no banco de dados
Executar com: python manage.py shell < create_sample_patients.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vacination_system.settings')
django.setup()

from core.models import User

# Cria pacientes de exemplo
pacientes = [
    {"name": "Luigi", "phone": "(11) 98765-4321", "cpf": "123.456.789-00"},
    {"name": "Yasmin Silva Ribeiro", "phone": "(11) 97654-3210", "cpf": "234.567.890-11"},
    {"name": "Falta os dados", "phone": "(11) 96543-2109", "cpf": "345.678.901-22"},
    {"name": "Julia Beltrame Julio de Souza", "phone": "(11) 95432-1098", "cpf": "456.789.012-33"},
    {"name": "Laura Vieira Cavalcanti", "phone": "(11) 94321-0987", "cpf": "567.890.123-44"},
    {"name": "Davi 13 anos", "phone": "(11) 93210-9876", "cpf": "678.901.234-55"},
    {"name": "Maria Valentim Putim", "phone": "(11) 92109-8765", "cpf": "789.012.345-66"},
    {"name": "Nome: Liz Durski Sales", "phone": "(11) 91098-7654", "cpf": "890.123.456-77"},
]

for paciente in pacientes:
    user, created = User.objects.get_or_create(
        name=paciente["name"],
        defaults={
            "phone": paciente["phone"],
            "cpf": paciente["cpf"],
            "via_chatbot": True,
            "synced": True
        }
    )
    if created:
        print(f"✓ Criado: {paciente['name']}")
    else:
        print(f"- Já existe: {paciente['name']}")

print(f"\nTotal de pacientes: {User.objects.count()}")
