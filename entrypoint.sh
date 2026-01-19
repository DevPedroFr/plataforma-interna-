#!/bin/bash

# Sair se algum comando falhar
set -e

echo "🔄 Aplicando migrations do banco de dados..."
python manage.py migrate --noinput

echo "📦 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput || true

echo "👤 Criando superusuário padrão (se não existir)..."
python manage.py shell << END
from django.contrib.auth import get_user_model
import os

User = get_user_model()
username = os.environ.get('SUPERADMIN_USERNAME', 'admin')
email = 'admin@example.com'
password = os.environ.get('DEFAULT_USER_PASSWORD', 'admin123')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password)
    print(f'✅ Superusuário "{username}" criado com sucesso!')
else:
    print(f'ℹ️  Superusuário "{username}" já existe.')
END

echo "🚀 Iniciando servidor Django..."
exec python manage.py runserver 0.0.0.0:8000