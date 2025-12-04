import requests
import json
from django.conf import settings
import os

class WahaService:
    def __init__(self):
        self.base_url = getattr(settings, 'WAHA_URL', 'http://localhost:3000')
        self.session = getattr(settings, 'WAHA_SESSION', 'default')
    
    def enviar_mensagem(self, chat_id, mensagem):
        """Envia mensagem de texto via WAHA"""
        try:
            url = f"{self.base_url}/api/sendText"
            payload = {
                "session": self.session,
                "chatId": chat_id,
                "text": mensagem
            }
            
            print(f"Enviando mensagem para {chat_id}: {mensagem}")
            
            response = requests.post(
                url, 
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                print("Mensagem enviada com sucesso!")
                return response.json()
            else:
                print(f"Erro ao enviar mensagem: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Erro no WahaService: {e}")
            return None
    
    def enviar_botoes(self, chat_id, titulo, corpo, botoes):
        """Envia mensagem com botões (se o engine suportar)"""
        try:
            url = f"{self.base_url}/api/sendButtons"
            payload = {
                "session": self.session,
                "chatId": chat_id,
                "title": titulo,
                "body": corpo,
                "buttons": botoes
            }
            
            response = requests.post(url, json=payload, timeout=30)
            return response.json()
            
        except Exception as e:
            print(f"Erro ao enviar botões: {e}")
            # Fallback para mensagem normal
            mensagem = f"{titulo}\n\n{corpo}\n\nOpções: {', '.join([btn['text'] for btn in botoes])}"
            return self.enviar_mensagem(chat_id, mensagem)