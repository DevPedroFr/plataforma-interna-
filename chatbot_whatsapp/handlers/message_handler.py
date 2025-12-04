import json
import os
from datetime import datetime
from ..services.gemini_service import GeminiService

class MessageHandler:
    def __init__(self):
        self.gemini = GeminiService()
        self.estados = {}  # {chat_id: estado_atual}
    
    def processar_mensagem(self, chat_id, mensagem):
        """Processa a mensagem e decide a resposta"""
        print(f"Processando mensagem: {chat_id} - {mensagem}")
        
        estado_atual = self.estados.get(chat_id, 'inicio')
        mensagem_lower = mensagem.lower()
        
        print(f"Estado atual: {estado_atual}")
        
        # Fluxo: Aguardando formulário de cadastro
        if estado_atual == 'aguardando_cadastro':
            return self.processar_formulario_cadastro(chat_id, mensagem)
        
        # Fluxo: Perguntou sobre vacinação anterior
        elif estado_atual == 'perguntou_vacinacao':
            return self.processar_resposta_vacinacao(chat_id, mensagem_lower)
        
        # Mensagem normal - usa IA
        else:
            return self.processar_mensagem_normal(chat_id, mensagem)
    
    def processar_mensagem_normal(self, chat_id, mensagem):
        """Processa mensagem usando Gemini"""
        resposta_ia = self.gemini.gerar_resposta(mensagem)
        print(f"Resposta do Gemini: {resposta_ia}")
        
        # Se detectou agendamento
        if "FLUXO_AGENDAMENTO" in resposta_ia:
            self.estados[chat_id] = 'perguntou_vacinacao'
            return {
                "acao": "enviar_mensagem",
                "mensagem": "Para agendar sua vacina, preciso verificar: você já se vacinou conosco antes? (responda 'sim' ou 'não')"
            }
        
        # Resposta normal da IA
        return {
            "acao": "enviar_mensagem",
            "mensagem": resposta_ia
        }
    
    def processar_resposta_vacinacao(self, chat_id, resposta):
        """Processa resposta sobre vacinação anterior"""
        if 'não' in resposta or 'nao' in resposta or 'n' in resposta:
            self.estados[chat_id] = 'aguardando_cadastro'
            formulario = """
*📝 CADASTRO RÁPIDO*

Por favor, envie seus dados em *UMA ÚNICA MENSAGEM* no formato abaixo:

*Nome Completo:* Seu nome aqui
*CPF:* 123.456.789-00
*Telefone:* (11) 99999-9999
*Email:* seu@email.com
*Data Nascimento:* 01/01/1990
*Endereço:* Rua Exemplo, 123 - Cidade - Estado

*Envie tudo em uma única mensagem!* 📱
            """
            return {
                "acao": "solicitar_cadastro",
                "mensagem": formulario
            }
        
        elif 'sim' in resposta or 's' in resposta:
            self.estados[chat_id] = 'inicio'
            return {
                "acao": "enviar_mensagem",
                "mensagem": "Perfeito! Vamos ao agendamento... \n\nEm breve implementaremos a funcionalidade completa de agendamento! 📅"
            }
        
        else:
            return {
                "acao": "enviar_mensagem",
                "mensagem": "Não entendi. Você já se vacinou conosco antes? (responda 'sim' ou 'não')"
            }
    
    def processar_formulario_cadastro(self, chat_id, mensagem):
        """Processa formulário de cadastro"""
        dados = self.extrair_dados_formulario(mensagem)
        
        if dados and len(dados) >= 3:  # Pelo menos 3 campos
            # Salvar dados
            self.salvar_dados_localmente(chat_id, dados)
            
            # Limpar estado
            self.estados[chat_id] = 'inicio'
            
            return {
                "acao": "enviar_mensagem",
                "mensagem": f"""✅ *CADASTRO REALIZADO COM SUCESSO!*

*Resumo dos dados:*
*Nome:* {dados.get('nome', 'N/A')}
*CPF:* {dados.get('cpf', 'N/A')}
*Telefone:* {dados.get('telefone', 'N/A')}

Agora podemos prosseguir com o agendamento! Em breve esta funcionalidade estará completa. 📅

Obrigado por escolher a VaccineSafe! ❤️"""
            }
        else:
            return {
                "acao": "enviar_mensagem",
                "mensagem": "❌ *Dados incompletos ou formato incorreto.*\n\nPor favor, envie novamente no formato solicitado, com pelo menos Nome, CPF e Telefone.\n\nExemplo:\n*Nome Completo:* Maria Silva\n*CPF:* 123.456.789-00\n*Telefone:* (11) 99999-9999\n*Email:* maria@email.com\n*Data Nascimento:* 15/05/1990\n*Endereço:* Rua das Flores, 123"
            }
    
    def extrair_dados_formulario(self, texto):
        """Extrai dados do formulário usando regex"""
        import re
        
        padroes = {
            'nome': r'\*?Nome Completo:\*?\s*([^\n]+)',
            'cpf': r'\*?CPF:\*?\s*([^\n]+)',
            'telefone': r'\*?Telefone:\*?\s*([^\n]+)',
            'email': r'\*?Email:\*?\s*([^\n]+)',
            'data_nascimento': r'\*?Data Nascimento:\*?\s*([^\n]+)',
            'endereco': r'\*?Endereço:\*?\s*([^\n]+)',
        }
        
        dados = {}
        for campo, padrao in padroes.items():
            match = re.search(padrao, texto, re.IGNORECASE | re.MULTILINE)
            if match:
                dados[campo] = match.group(1).strip()
        
        print(f"Dados extraídos: {dados}")
        return dados
    
    def salvar_dados_localmente(self, chat_id, dados):
        """Salva dados em arquivo JSON local"""
        try:
            os.makedirs('cadastros', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            arquivo = f"cadastros/cliente_{chat_id}_{timestamp}.json"
            
            # Adicionar metadata
            dados_com_meta = {
                **dados,
                'chat_id': chat_id,
                'data_cadastro': datetime.now().isoformat(),
                'timestamp': timestamp
            }
            
            with open(arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados_com_meta, f, ensure_ascii=False, indent=2)
            
            print(f"Dados salvos em: {arquivo}")
            
        except Exception as e:
            print(f"Erro ao salvar dados: {e}")