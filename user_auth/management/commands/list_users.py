"""
Comando Django para listar usuários do sistema de autenticação
Uso:
  python manage.py list_users
"""

from django.core.management.base import BaseCommand
from user_auth.user_manager import user_manager
from datetime import datetime


class Command(BaseCommand):
    help = 'Lista todos os usuários do sistema de autenticação'

    def handle(self, *args, **options):
        users = user_manager.list_all_users()

        if not users:
            self.stdout.write(
                self.style.WARNING('⚠️  Nenhum usuário cadastrado')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'\n📋 Total de usuários: {len(users)}\n')
        )

        # Cabeçalho da tabela
        self.stdout.write(
            f"{'ID':<4} {'Usuário':<15} {'Nome Completo':<25} {'Cargo':<15} {'Cadastro':<19}"
        )
        self.stdout.write('-' * 80)

        # Dados dos usuários
        for user in users:
            user_id = str(user.get('id', '')).ljust(4)
            username = user.get('username', '').ljust(15)
            name = user.get('name', '')[:24].ljust(25)
            position = user.get('position', '').ljust(15)
            
            # Formata a data de criação
            created_at = user.get('created_at', 'N/A')
            if created_at != 'N/A':
                try:
                    dt = datetime.fromisoformat(created_at)
                    created_at = dt.strftime('%d/%m/%Y %H:%M:%S')
                except:
                    created_at = 'N/A'
            
            self.stdout.write(f'{user_id}{username}{name}{position}{created_at}')

        self.stdout.write('-' * 80)
        self.stdout.write('')
