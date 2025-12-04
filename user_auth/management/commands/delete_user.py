"""
Comando Django para deletar usuários do sistema de autenticação
Uso:
  python manage.py delete_user --username operador1
  python manage.py delete_user -u operador1
"""

from django.core.management.base import BaseCommand, CommandError
from user_auth.user_manager import user_manager


class Command(BaseCommand):
    help = 'Deleta um usuário do sistema de autenticação'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username', '-u',
            type=str,
            required=True,
            help='Nome de usuário a deletar'
        )
        parser.add_argument(
            '--force', '-f',
            action='store_true',
            help='Confirma a deleção sem pedir confirmação'
        )

    def handle(self, *args, **options):
        username = options['username']
        force = options.get('force', False)

        # Verifica se o usuário existe
        user = user_manager.get_user_by_username(username)
        
        if not user:
            raise CommandError(f'❌ Usuário "{username}" não encontrado')

        # Pede confirmação (a menos que --force seja usado)
        if not force:
            self.stdout.write(
                self.style.WARNING(
                    f'\n⚠️  Você está prestes a deletar o usuário:\n'
                    f'   Nome: {user["name"]}\n'
                    f'   Usuário: {user["username"]}\n'
                    f'   Cargo: {user["position"]}\n'
                )
            )
            
            resposta = input('\nDeseja confirmar? (s/n): ').lower().strip()
            
            if resposta not in ['s', 'sim', 'y', 'yes']:
                self.stdout.write(self.style.WARNING('❌ Operação cancelada'))
                return

        # Deleta o usuário
        if user_manager.delete_user(username):
            self.stdout.write(
                self.style.SUCCESS(f'✅ Usuário "{username}" deletado com sucesso!')
            )
        else:
            raise CommandError(f'❌ Erro ao deletar o usuário "{username}"')
