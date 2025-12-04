# Sistema de Autenticação - Documentação

## Visão Geral

O sistema de autenticação foi implementado com armazenamento seguro de usuários em JSON, sem necessidade de banco de dados adicional. As senhas são armazenadas com hash SHA256 para garantir segurança.

## Características

✅ **Armazenamento em JSON**: Usuários armazenados em `data/users.json`
✅ **Senhas com Hash SHA256**: Segurança garantida
✅ **Sessões Django**: Controle de autenticação robusto
✅ **Middleware de Proteção**: Redireciona para login automaticamente
✅ **Decoradores Customizados**: Proteção granular de views
✅ **Campo de Cargo**: Pronto para implementar regras de negócio
✅ **Rastreamento de Login**: Registra data/hora do último acesso

## Estrutura de Usuário no JSON

```json
{
  "id": 1,
  "username": "admin",
  "password_hash": "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918",
  "name": "Administrador",
  "position": "Administrador",
  "created_at": "2024-12-02T10:00:00",
  "last_login": null
}
```

### Campos:
- **id**: Identificador único
- **username**: Nome de usuário (único)
- **password_hash**: Senha com hash SHA256
- **name**: Nome completo
- **position**: Cargo/posição (para implementar regras futuras)
- **created_at**: Data de criação da conta
- **last_login**: Timestamp do último login

## Usuários de Teste

### Credenciais Pré-configuradas

Todos os usuários de teste usam a mesma senha:

```
Senha padrão: admin
```

#### Usuários:

1. **Administrador**
   - Username: `admin`
   - Senha: `admin`
   - Posição: Administrador
   - Acesso completo

2. **Gerente**
   - Username: `cesario`
   - Senha: `admin`
   - Posição: Gerente
   - Acesso a relatórios e gerenciamento

3. **Operador**
   - Username: `operador1`
   - Senha: `admin`
   - Posição: Operador
   - Acesso limitado

## Fluxo de Autenticação

```
1. Usuário acessa a plataforma
2. Middleware verifica autenticação
3. Se não autenticado → Redireciona para login
4. Usuário entra credenciais
5. Sistema valida contra users.json
6. Se válido → Cria sessão e redireciona para dashboard
7. Se inválido → Exibe mensagem de erro
```

## Como Usar

### Login

```python
# Requisição POST para /auth/login/
username: admin
password: admin
```

### Logout

```python
# Acessa /auth/logout/
# Limpa a sessão e redireciona para login
```

### Acessar Perfil

```
# GET /auth/profile/
# Exibe dados do usuário logado
```

## API de Usuários

### UserManager

Classe localizada em `auth/user_manager.py` que gerencia todas as operações com usuários.

```python
from auth.user_manager import user_manager

# Autenticar
user = user_manager.authenticate('admin', 'admin')

# Criar novo usuário
new_user = user_manager.create_user(
    username='novo_user',
    password='senha123',
    name='Novo Usuário',
    position='Operador'
)

# Obter usuário
user = user_manager.get_user_by_username('admin')

# Listar todos
users = user_manager.list_all_users()

# Atualizar
user_manager.update_user('admin', name='Novo Nome')

# Deletar
user_manager.delete_user('admin')

# Mudar senha
user_manager.change_password('admin', 'senha_antiga', 'senha_nova')
```

## Proteção de Views

### Usando Decorador

```python
from auth.decorators import login_required

@login_required
def minha_view(request):
    current_user = request.session.get('user')
    # seu código aqui
```

### Proteção por Cargo

```python
from auth.decorators import position_required

@position_required(['Administrador', 'Gerente'])
def view_gerencial(request):
    # apenas admins e gerentes podem acessar
    pass
```

## Acessar Dados do Usuário Logado

Em qualquer view protegida:

```python
def dashboard(request):
    current_user = request.session.get('user')
    
    print(current_user['name'])           # Nome completo
    print(current_user['username'])       # Usuário
    print(current_user['position'])       # Cargo
    print(current_user['created_at'])     # Data de criação
    print(current_user['last_login'])     # Último login
```

Em templates Django:

```html
<span>Olá, {{ current_user.name }}</span>
<span>Cargo: {{ current_user.position }}</span>
```

## Adicionar Novo Usuário

### Via Código

```python
from auth.user_manager import user_manager

try:
    user = user_manager.create_user(
        username='joao_silva',
        password='senha_segura_123',
        name='João Silva',
        position='Operador'
    )
    print(f"Usuário {user['name']} criado com sucesso!")
except ValueError as e:
    print(f"Erro: {e}")
```

### Editar users.json Manualmente

1. Abra `data/users.json`
2. Adicione um novo objeto (copie e adapte a estrutura)
3. Gere o hash da senha:

```python
from auth.user_manager import UserManager
hash = UserManager.hash_password('sua_senha')
print(hash)  # Use esse valor no JSON
```

## Configuração do Docker

O sistema está pronto para rodar no Docker:

```bash
# Build
docker-compose build

# Run
docker-compose up -d
```

### Volumes

A pasta `data/` é compartilhada entre o host e o container, permitindo:
- Editar usuários sem reiniciar o container
- Fazer backup do arquivo users.json
- Adicionar novos usuários facilmente

## Segurança

✅ **Senhas com Hash**: SHA256 (uma via)
✅ **Sessões Django**: Protegidas por CSRF token
✅ **Middleware de Proteção**: Redireciona automaticamente
✅ **Dados Sensíveis Exclusos**: Senhas nunca são exibidas
✅ **Rastreamento de Acesso**: Registra último login

## Estrutura de Arquivos

```
auth/
├── __init__.py
├── urls.py                 # Rotas de autenticação
├── views.py               # Views de login/logout/perfil
├── decorators.py          # Decoradores de proteção
├── middleware.py          # Middleware de autenticação
└── user_manager.py        # Gerenciador de usuários

templates/auth/
├── login.html             # Tela de login
└── profile.html           # Perfil do usuário

data/
└── users.json             # Arquivo de usuários
```

## Próximos Passos

Quando for necessário implementar regras de negócio baseadas em cargo:

```python
@position_required('Administrador')
def delete_user_view(request, user_id):
    # Apenas administrador pode deletar
    pass

# Ou verificar em views
def some_view(request):
    user = request.session.get('user')
    
    if user['position'] == 'Administrador':
        # Mostrar opções de admin
    elif user['position'] == 'Gerente':
        # Mostrar opções de gerente
```

## Suporte

Para dúvidas ou problemas:
1. Verifique se `data/users.json` existe e é válido
2. Verifique se o middleware está ativado no settings.py
3. Verifique os logs do Django para mensagens de erro
4. Certifique-se de que as senhas estão com hash SHA256

---

**Última atualização**: 02/12/2024
