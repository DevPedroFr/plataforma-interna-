"""
Comando Django para criar usuários no sistema de autenticação
Uso:
  python manage.py create_user --username admin --password admin --name "Administrador" --position "Administrador"
  python manage.py create_user -u operador1 -p senha123 -n "Operador Um" -pos "Operador"
"""

from django.core.management.base import BaseCommand, CommandError
from user_auth.user_manager import user_manager


class Command(BaseCommand):
    help = 'Cria um novo usuário no sistema de autenticação'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username', '-u',
            type=str,
            required=True,
            help='Nome de usuário (deve ser único)'
        )
        parser.add_argument(
            '--password', '-p',
            type=str,
            required=True,
            help='Senha (será hasheada automaticamente)'
        )
        parser.add_argument(
            '--name', '-n',
            type=str,
            required=True,
            help='Nome completo do usuário'
        )
        parser.add_argument(
            '--position', '-pos',
            type=str,
            default='Operador',
            help='Cargo/posição (padrão: Operador)'
        )

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        name = options['name']
        position = options['position']

        try:
            user = user_manager.create_user(
                username=username,
                password=password,
                name=name,
                position=position
            )

            self.stdout.write(
                self.style.SUCCESS(f'✅ Usuário "{username}" criado com sucesso!')
            )
            self.stdout.write(f'   Nome: {user["name"]}')
            self.stdout.write(f'   Cargo: {user["position"]}')
            self.stdout.write(f'   ID: {user["id"]}')

        except ValueError as e:
            raise CommandError(f'❌ Erro: {str(e)}')
        except Exception as e:
            raise CommandError(f'❌ Erro inesperado: {str(e)}')
