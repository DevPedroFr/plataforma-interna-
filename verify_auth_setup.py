#!/usr/bin/env python
"""
Script de verificação do sistema de autenticação
Executa validações para garantir que tudo está funcionando corretamente
"""

import json
import os
import sys
from pathlib import Path

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_ok(text):
    print(f"  ✅ {text}")

def print_error(text):
    print(f"  ❌ {text}")

def print_warning(text):
    print(f"  ⚠️  {text}")

def main():
    print_header("VERIFICAÇÃO DO SISTEMA DE AUTENTICAÇÃO")
    
    base_dir = Path(__file__).parent
    errors = []
    warnings = []
    
    # Verificar estrutura de pastas
    print("\n📁 Verificando estrutura de pastas...")
    
    folders_to_check = [
        'auth',
        'auth/management',
        'auth/management/commands',
        'data',
        'templates/auth',
    ]
    
    for folder in folders_to_check:
        folder_path = base_dir / folder
        if folder_path.exists():
            print_ok(f"Pasta: {folder}")
        else:
            print_error(f"Pasta não encontrada: {folder}")
            errors.append(f"Pasta {folder} não existe")
    
    # Verificar arquivos
    print("\n📄 Verificando arquivos...")
    
    files_to_check = {
        'auth/__init__.py': 'Módulo auth',
        'auth/views.py': 'Views de autenticação',
        'auth/urls.py': 'URLs de autenticação',
        'auth/decorators.py': 'Decoradores de proteção',
        'auth/middleware.py': 'Middleware de autenticação',
        'auth/user_manager.py': 'Gerenciador de usuários',
        'auth/management/commands/create_user.py': 'Comando create_user',
        'auth/management/commands/list_users.py': 'Comando list_users',
        'auth/management/commands/delete_user.py': 'Comando delete_user',
        'data/users.json': 'Arquivo de usuários',
        'templates/auth/login.html': 'Template de login',
        'templates/auth/profile.html': 'Template de perfil',
    }
    
    for file_path, description in files_to_check.items():
        full_path = base_dir / file_path
        if full_path.exists():
            print_ok(f"{description}: {file_path}")
        else:
            print_error(f"{description} não encontrado: {file_path}")
            errors.append(f"Arquivo {file_path} não existe")
    
    # Verificar conteúdo do users.json
    print("\n👥 Verificando arquivo de usuários...")
    
    users_file = base_dir / 'data' / 'users.json'
    if users_file.exists():
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                users = json.load(f)
            
            if isinstance(users, list):
                print_ok(f"users.json é um JSON válido com {len(users)} usuários")
                
                required_fields = ['id', 'username', 'password_hash', 'name', 'position', 'created_at']
                
                for i, user in enumerate(users):
                    missing_fields = [field for field in required_fields if field not in user]
                    if missing_fields:
                        print_warning(f"Usuário #{i+1} ({user.get('username', 'desconhecido')}) está faltando campos: {missing_fields}")
                        warnings.append(f"Usuário {user.get('username')} faltando: {missing_fields}")
                    else:
                        print_ok(f"Usuário #{i+1}: {user['username']} ({user['name']})")
            else:
                print_error("users.json não é uma lista JSON")
                errors.append("users.json deve ser uma lista")
        
        except json.JSONDecodeError as e:
            print_error(f"users.json não é um JSON válido: {e}")
            errors.append(f"JSON inválido em users.json: {e}")
        except Exception as e:
            print_error(f"Erro ao ler users.json: {e}")
            errors.append(f"Erro ao ler users.json: {e}")
    else:
        print_error("Arquivo users.json não encontrado")
        errors.append("users.json não existe")
    
    # Verificar settings.py
    print("\n⚙️  Verificando configurações Django...")
    
    settings_file = base_dir / 'vacination_system' / 'settings.py'
    if settings_file.exists():
        try:
            content = settings_file.read_text(encoding='utf-8')
            
            checks = [
                ("'auth' in INSTALLED_APPS", "'auth'" in content and "INSTALLED_APPS" in content),
                ("Middleware de autenticação", "auth.middleware.AuthenticationMiddleware" in content),
            ]
            
            for check_name, result in checks:
                if result:
                    print_ok(f"Configuração: {check_name}")
                else:
                    print_warning(f"Configuração possivelmente não feita: {check_name}")
                    warnings.append(f"Verifique: {check_name}")
        
        except Exception as e:
            print_error(f"Erro ao ler settings.py: {e}")
            errors.append(f"Erro em settings.py: {e}")
    else:
        print_error("settings.py não encontrado")
        errors.append("settings.py não existe")
    
    # Verificar urls.py
    print("\n🔗 Verificando URLs...")
    
    urls_file = base_dir / 'vacination_system' / 'urls.py'
    if urls_file.exists():
        try:
            content = urls_file.read_text(encoding='utf-8')
            
            if "include('auth.urls')" in content or 'include("auth.urls")' in content:
                print_ok("URLs de autenticação incluídas")
            else:
                print_warning("URLs de autenticação podem não estar incluídas")
                warnings.append("Verifique se auth.urls está incluído em urlpatterns")
        
        except Exception as e:
            print_error(f"Erro ao ler urls.py: {e}")
            errors.append(f"Erro em urls.py: {e}")
    
    # Verificar docker-compose
    print("\n🐳 Verificando Docker Compose...")
    
    docker_file = base_dir / 'docker-compose.yml'
    if docker_file.exists():
        try:
            content = docker_file.read_text(encoding='utf-8')
            
            if "./data:/app/data" in content:
                print_ok("Volume ./data está configurado no docker-compose.yml")
            else:
                print_warning("Volume ./data pode não estar configurado")
                warnings.append("Adicione volume ./data ao docker-compose.yml")
        
        except Exception as e:
            print_error(f"Erro ao ler docker-compose.yml: {e}")
    
    # Resumo
    print_header("RESUMO DA VERIFICAÇÃO")
    
    if not errors and not warnings:
        print_ok("TUDO OK! Sistema de autenticação está configurado corretamente.")
    elif not errors:
        print_ok("Sistema está funcionando, mas com alguns avisos.")
        print("\n⚠️  Avisos:")
        for warning in warnings:
            print_warning(warning)
    else:
        print_error("Sistema possui erros que precisam ser corrigidos.")
        print("\n❌ Erros encontrados:")
        for error in errors:
            print_error(error)
    
    print("\n")
    return 0 if not errors else 1

if __name__ == '__main__':
    sys.exit(main())
