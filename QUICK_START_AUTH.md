# Guia Rápido - Sistema de Autenticação

## 🚀 Primeiros Passos

### 1. Acessar a Plataforma

```
URL: http://localhost:8000
```

Você será automaticamente redirecionado para a tela de login.

### 2. Login com Usuário de Teste

```
Usuário: admin
Senha: admin
```

OU

```
Usuário: cesario
Senha: admin
```

### 3. Dashboard

Após fazer login, você verá o dashboard com:
- Informações do usuário logado no header
- Dropdown com opções de perfil e logout
- Todas as funcionalidades da plataforma

---

## 👤 Gerenciar Usuários

### Listar Usuários

```bash
# Via terminal dentro do container
python manage.py list_users
```

Exemplo de saída:
```
📋 Total de usuários: 3

ID   Usuário        Nome Completo         Cargo           Cadastro           
---  admin          Administrador         Administrador   02/12/2024 10:00:00
     cesario        Cesário Silva         Gerente         02/12/2024 10:00:00
     operador1      Operador Teste        Operador        02/12/2024 10:00:00
```

### Criar Novo Usuário

```bash
# Sintaxe: python manage.py create_user -u <username> -p <password> -n <name> -pos <position>

python manage.py create_user \
  -u joao_silva \
  -p senha_segura_123 \
  -n "João Silva" \
  -pos "Operador"
```

Saída esperada:
```
✅ Usuário "joao_silva" criado com sucesso!
   Nome: João Silva
   Cargo: Operador
   ID: 4
```

### Deletar Usuário

```bash
# Com confirmação
python manage.py delete_user -u joao_silva

# Sem confirmação (forçado)
python manage.py delete_user -u joao_silva --force
```

---

## 🐳 Usando no Docker

### Executar Comando no Container

```bash
# Entrar no container web
docker exec -it plataforma-jm-web bash

# Executar comando dentro do container
python manage.py list_users
python manage.py create_user -u novo_user -p senha -n "Novo Usuário"
```

### Ou via docker-compose

```bash
# Listar usuários
docker-compose exec web python manage.py list_users

# Criar usuário
docker-compose exec web python manage.py create_user \
  -u novo_user \
  -p senha123 \
  -n "Novo Usuário"
```

---

## 📝 Editar Usuários Manualmente

Se preferir editar diretamente no JSON:

1. **Abra**: `data/users.json`

2. **Gere a senha hasheada** (em Python):
```python
from auth.user_manager import UserManager
hash = UserManager.hash_password('sua_senha_aqui')
print(hash)
```

3. **Adicione um novo usuário**:
```json
{
  "id": 4,
  "username": "novo_user",
  "password_hash": "hash_gerado_acima",
  "name": "Novo Usuário",
  "position": "Operador",
  "created_at": "2024-12-02T10:00:00",
  "last_login": null
}
```

4. **Salve o arquivo**
5. **Reinicie o container** (o arquivo é sincronizado via volume)

---

## 🔐 Segurança

- ✅ Senhas hasheadas com SHA256
- ✅ Sessões Django protegidas
- ✅ CSRF tokens em formulários
- ✅ Middleware de proteção automática
- ✅ Registro de último acesso

---

## 🔧 Troubleshooting

### "Usuário ou senha inválidos"
- Verifique se o username está correto
- Verifique se a senha está correta
- Certifique-se de que o usuário existe em `data/users.json`

### "Arquivo users.json não encontrado"
- Verifique se a pasta `data/` existe
- Verifique se o arquivo `data/users.json` existe
- Crie manualmente se necessário

### Redirecionado para login ao acessar dashboard
- Sua sessão expirou
- Faça login novamente
- Se persistir, verifique o middleware em `settings.py`

---

## 📋 Cargos Disponíveis

- **Administrador**: Acesso completo
- **Gerente**: Acesso a relatórios e gerenciamento
- **Operador**: Acesso limitado (padrão)

Você pode usar qualquer cargo, pois o campo está pronto para implementar regras de negócio futuras.

---

## 💡 Dicas

1. **Mudar Senha**: Utilize o arquivo JSON ou implemente a view de mudança de senha
2. **Backup**: Faça backup de `data/users.json` regularmente
3. **Adicionar Campos**: Edite `auth/user_manager.py` para adicionar novos campos
4. **Regras por Cargo**: Use decoradores em views para controlar acesso por cargo

---

## 📞 Contato

Para dúvidas ou problemas:
1. Verifique o `AUTH_README.md` para documentação detalhada
2. Verifique os logs do Django
3. Certifique-se de que a pasta `data/` está com permissões corretas

---

**Último atualizado**: 02/12/2024
