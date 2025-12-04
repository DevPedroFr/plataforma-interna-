"""
Gerenciador de usuários com armazenamento em JSON.
Implementa autenticação simples e segura sem banco de dados.
"""

import json
import hashlib
import os
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime


class UserManager:
    """
    Gerencia usuários armazenados em arquivo JSON.
    Implementa hashing de senhas para segurança.
    """
    
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parent.parent
        self.users_file = self.base_dir / 'data' / 'users.json'
        self._ensure_users_file()
    
    def _ensure_users_file(self):
        """Garante que o arquivo de usuários existe."""
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.users_file.exists():
            self.users_file.write_text(json.dumps([], indent=2))
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Gera hash SHA256 da senha."""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def load_users(self) -> List[Dict]:
        """Carrega todos os usuários do arquivo JSON."""
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def save_users(self, users: List[Dict]) -> None:
        """Salva usuários no arquivo JSON."""
        self.users_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """
        Autentica um usuário com username e senha.
        Retorna os dados do usuário se autenticado, None caso contrário.
        """
        users = self.load_users()
        password_hash = self.hash_password(password)
        
        for user in users:
            if user.get('username') == username and user.get('password_hash') == password_hash:
                # Retorna usuário sem a senha
                user_copy = user.copy()
                user_copy.pop('password_hash', None)
                return user_copy
        
        return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Obtém usuário pelo username."""
        users = self.load_users()
        for user in users:
            if user.get('username') == username:
                user_copy = user.copy()
                user_copy.pop('password_hash', None)
                return user_copy
        return None
    
    def user_exists(self, username: str) -> bool:
        """Verifica se um usuário já existe."""
        return self.get_user_by_username(username) is not None
    
    def create_user(self, username: str, password: str, name: str, 
                   position: str = 'Operador') -> Dict:
        """
        Cria um novo usuário.
        
        Args:
            username: Nome de usuário único
            password: Senha em texto plano (será hasheada)
            name: Nome completo
            position: Cargo/posição do usuário
        
        Returns:
            Dados do usuário criado (sem senha)
        """
        if self.user_exists(username):
            raise ValueError(f"Usuário '{username}' já existe")
        
        users = self.load_users()
        
        new_user = {
            'id': len(users) + 1,
            'username': username,
            'password_hash': self.hash_password(password),
            'name': name,
            'position': position,
            'created_at': datetime.now().isoformat(),
            'last_login': None
        }
        
        users.append(new_user)
        self.save_users(users)
        
        # Retorna sem a senha
        user_copy = new_user.copy()
        user_copy.pop('password_hash')
        return user_copy
    
    def update_last_login(self, username: str) -> None:
        """Atualiza o timestamp do último login."""
        users = self.load_users()
        for user in users:
            if user.get('username') == username:
                user['last_login'] = datetime.now().isoformat()
                break
        self.save_users(users)
    
    def update_user(self, username: str, **kwargs) -> Optional[Dict]:
        """
        Atualiza dados do usuário.
        Não permite alterar username ou password_hash diretamente.
        """
        users = self.load_users()
        
        for user in users:
            if user.get('username') == username:
                # Campos permitidos para atualização
                allowed_fields = {'name', 'position'}
                
                for key, value in kwargs.items():
                    if key in allowed_fields:
                        user[key] = value
                
                self.save_users(users)
                
                user_copy = user.copy()
                user_copy.pop('password_hash', None)
                return user_copy
        
        return None
    
    def delete_user(self, username: str) -> bool:
        """Deleta um usuário."""
        users = self.load_users()
        original_count = len(users)
        users = [u for u in users if u.get('username') != username]
        
        if len(users) < original_count:
            self.save_users(users)
            return True
        return False
    
    def list_all_users(self) -> List[Dict]:
        """Lista todos os usuários (sem senhas)."""
        users = self.load_users()
        return [
            {k: v for k, v in user.items() if k != 'password_hash'}
            for user in users
        ]
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Altera a senha de um usuário."""
        users = self.load_users()
        old_password_hash = self.hash_password(old_password)
        new_password_hash = self.hash_password(new_password)
        
        for user in users:
            if user.get('username') == username:
                if user.get('password_hash') == old_password_hash:
                    user['password_hash'] = new_password_hash
                    self.save_users(users)
                    return True
                return False
        
        return False


# Instância global do gerenciador
user_manager = UserManager()
