import google.generativeai as genai
from django.conf import settings
import os

class GeminiService:
    def __init__(self):
        # Configurar API Key - pega do settings ou variável de ambiente
        api_key = getattr(settings, 'GEMINI_API_KEY', os.getenv('GEMINI_API_KEY'))
        if not api_key:
            raise ValueError("GEMINI_API_KEY não configurada")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
    
    def gerar_resposta(self, mensagem, contexto=None):
        try:
            prompt = f"""
            Você é um assistente de uma clínica de vacinação chamada "VaccineSafe". 
            
            CONTEXTO ATUAL: {contexto or 'Conversa inicial'}
            
            SUAS INSTRUÇÕES:
            1. Se o usuário quer AGENDAMENTO (palavras: agendar, marcar, vacina, tomar vacina, agendamento), 
               responda EXATAMENTE: **FLUXO_AGENDAMENTO**
            
            2. Para outras dúvidas, responda de forma útil sobre:
               - Tipos de vacinas disponíveis
               - Horários de funcionamento
               - Documentos necessários
               - Pré-requisitos para vacinação
               - Falar com atendente humano
            
            3. Seja sempre educado, objetivo e prestativo
            
            4. Sua identidade: "Assistente VaccineSafe"
            
            MENSAGEM DO USUÁRIO: {mensagem}
            
            SUA RESPOSTA (seja direto):
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            print(f"Erro no Gemini: {e}")
            return "Desculpe, estou com problemas técnicos. Por favor, tente novamente."