import json
import os
from datetime import datetime

def salvar_json(dados, pasta, prefixo=""):
    """Salva dados em arquivo JSON"""
    try:
        os.makedirs(pasta, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nome_arquivo = f"{prefixo}_{timestamp}.json" if prefixo else f"dados_{timestamp}.json"
        caminho = os.path.join(pasta, nome_arquivo)
        
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        
        return caminho
    except Exception as e:
        print(f"Erro ao salvar arquivo: {e}")
        return None

def listar_arquivos(pasta, extensao='.json'):
    """Lista arquivos em uma pasta"""
    try:
        if not os.path.exists(pasta):
            return []
        return [f for f in os.listdir(pasta) if f.endswith(extensao)]
    except Exception as e:
        print(f"Erro ao listar arquivos: {e}")
        return []