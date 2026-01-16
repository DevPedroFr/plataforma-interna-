"""
Script para salvar a logo da VaccineCare na pasta static/images
"""
import base64
import os
from pathlib import Path

# Logo em base64 (a ser preenchida)
# Esta é a imagem da VaccineCare fornecida
LOGO_BASE64 = """
iVBORw0KGgoAAAANSUhEUgAABLAAAAEsCAYAAADfDtISAAAACXBIWXMAAC4jAAAuIwF4pT92AAAA
GXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAQdJJREFUeNrs3Xd4VFX+x/HPnUkl
IYQkQAIk9N57770XARUVRRRFRbFgV1Zd3V3L6q7YFVfFgr2goIL0Xnrvvfee0Nt9zr1Jfqz+fv/s
7u4zz/Mcnscwmbnl3nPPfO8573eMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
"""

def save_logo():
    """Salva a logo na pasta static/images"""
    # Determina o diretório do projeto
    base_dir = Path(__file__).resolve().parent
    static_images_dir = base_dir / 'static' / 'images'
    
    # Garante que o diretório existe
    static_images_dir.mkdir(parents=True, exist_ok=True)
    
    # Remove espaços em branco e quebras de linha do base64
    logo_data = LOGO_BASE64.strip().replace('\n', '').replace(' ', '')
    
    try:
        # Decodifica e salva
        logo_path = static_images_dir / 'logo.png'
        with open(logo_path, 'wb') as f:
            f.write(base64.b64decode(logo_data))
        
        print(f"✓ Logo salva com sucesso em: {logo_path}")
        return True
    except Exception as e:
        print(f"✗ Erro ao salvar logo: {e}")
        return False

if __name__ == '__main__':
    save_logo()
