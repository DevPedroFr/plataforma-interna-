import json
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from .handlers.message_handler import MessageHandler
from .services.waha_service import WahaService

# Instâncias globais
handler = MessageHandler()
waha = WahaService()

@csrf_exempt
def webhook_whatsapp(request):
    """
    Webhook que recebe mensagens do WAHA
    URL: http://your-domain.com/chatbot/webhook/whatsapp/
    """
    if request.method == 'POST':
        try:
            # Log para debug
            print("=== WEBHOOK RECEBIDO ===")
            
            # Obter dados do request
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                return JsonResponse({'error': 'Content-Type must be application/json'}, status=400)
            
            print("Dados recebidos:", json.dumps(data, indent=2))
            
            # Extrair informações
            chat_id = data.get('chatId') or data.get('from')
            mensagem = data.get('body', '')
            session = data.get('session', 'default')
            
            if not chat_id or not mensagem:
                return JsonResponse({'error': 'chatId and body are required'}, status=400)
            
            # Processar mensagem
            resultado = handler.processar_mensagem(chat_id, mensagem)
            print("Resultado do processamento:", resultado)
            
            # Executar ação
            if resultado.get('acao') == 'enviar_mensagem':
                waha.enviar_mensagem(chat_id, resultado['mensagem'])
            
            elif resultado.get('acao') == 'solicitar_cadastro':
                waha.enviar_mensagem(chat_id, resultado['mensagem'])
                handler.estados[chat_id] = 'aguardando_cadastro'
            
            return JsonResponse({'status': 'success', 'processed': True})
            
        except Exception as e:
            print(f"Erro no webhook: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)
    
    elif request.method == 'GET':
        # Para verificação do webhook
        return JsonResponse({'status': 'webhook active', 'message': 'WAHA webhook is running'})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

def dashboard(request):
    """Dashboard para monitorar o chatbot"""
    return render(request, 'chatbot/dashboard.html')