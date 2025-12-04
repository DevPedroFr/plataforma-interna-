from django.db import models

class Conversa(models.Model):
    chat_id = models.CharField(max_length=255)
    ultima_mensagem = models.TextField()
    estado = models.CharField(max_length=100, default='inicio')
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'chatbot_conversas'

class ClienteCadastrado(models.Model):
    chat_id = models.CharField(max_length=255)
    nome = models.CharField(max_length=255)
    cpf = models.CharField(max_length=14)
    telefone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    data_nascimento = models.DateField(blank=True, null=True)
    endereco = models.TextField(blank=True, null=True)
    data_cadastro = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'chatbot_clientes'