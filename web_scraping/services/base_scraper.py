# web_scraping/services/base_scraper.py
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from django.conf import settings

class BaseScraper:
    def __init__(self, browser_manager):
        self.browser = browser_manager
        if not self.browser.driver:
            print("🔄 Iniciando navegador...")
            self.browser.start_browser(headless=True)
        self.logged_in = False
    
    def login(self, username=None, password=None):
        """Faz login no sistema matriz"""
        if self.logged_in:
            return True
            
        if not self.browser or not self.browser.driver:
            print("❌ Navegador não foi inicializado corretamente")
            return False
            
        print("🔐 Realizando login no sistema matriz...")
        
        # Usa credenciais do Django settings (que lê do .env) ou variáveis de ambiente como fallback
        username = username or getattr(settings, 'MATRIX_SYSTEM_USERNAME', None) or os.getenv('MATRIX_SYSTEM_USERNAME', '')
        password = password or getattr(settings, 'MATRIX_SYSTEM_PASSWORD', None) or os.getenv('MATRIX_SYSTEM_PASSWORD', '')
        
        if not username or not password:
            print("❌ Credenciais do sistema matriz não configuradas!")
            print("   Configure MATRIX_SYSTEM_USERNAME e MATRIX_SYSTEM_PASSWORD no .env")
            return False
        
        try:
            # Navega para página de login
            login_url = "https://aruja.gocfranquias.com.br/login.aspx"
            self.browser.driver.get(login_url)
            
            print(f"📄 Página de login carregada: {self.browser.driver.current_url}")
            
            # Aguarda o formulário carregar com timeout maior
            WebDriverWait(self.browser.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Tenta encontrar os campos de login por diferentes seletores
            username_field = None
            password_field = None
            login_button = None
            
            # Método 1: Procura por name
            username_field = self.browser.driver.find_element(By.NAME, "Login1$UserName")
            password_field = self.browser.driver.find_element(By.NAME, "Login1$Password")
            login_button = self.browser.driver.find_element(By.NAME, "Login1$LoginButton")
            
            if not all([username_field, password_field, login_button]):
                # Método 2: Procura por ID
                username_field = self.browser.driver.find_element(By.ID, "Login1_UserName")
                password_field = self.browser.driver.find_element(By.ID, "Login1_Password")
                login_button = self.browser.driver.find_element(By.ID, "Login1_LoginButton")
            
            if not all([username_field, password_field, login_button]):
                # Método 3: Procura por CSS selector
                username_field = self.browser.driver.find_element(By.CSS_SELECTOR, "input[name*='UserName']")
                password_field = self.browser.driver.find_element(By.CSS_SELECTOR, "input[name*='Password']")
                login_button = self.browser.driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']")
            
            # Preenche formulário
            username_field.clear()
            username_field.send_keys(username)
            
            password_field.clear()
            password_field.send_keys(password)
            
            print("📝 Credenciais preenchidas, clicando no botão de login...")
            
            # Clica no botão de login
            login_button.click()
            
            # Aguarda o processamento do login
            time.sleep(5)
            
            # Verifica se login foi bem sucedido
            current_url = self.browser.driver.current_url
            print(f"🔍 URL atual após login: {current_url}")
            
            # Verifica se foi redirecionado para página inicial
            if "Inicio.aspx" in current_url or "inicio" in current_url.lower():
                self.logged_in = True
                print("✅ Login realizado com sucesso!")
                return True
            else:
                # Verifica mensagens de erro
                error_selectors = [
                    ".error", 
                    ".alert-danger", 
                    ".alert-error",
                    "[style*='color:red']",
                    "#Login1_FailureText"
                ]
                
                for selector in error_selectors:
                    try:
                        error_elem = self.browser.driver.find_element(By.CSS_SELECTOR, selector)
                        if error_elem.is_displayed() and error_elem.text.strip():
                            print(f"❌ Erro no login: {error_elem.text}")
                            break
                    except:
                        continue
                else:
                    print("❌ Login falhou - Não foi redirecionado para página inicial")
                
                # Tira screenshot para debug
                self.browser.driver.save_screenshot("login_error.png")
                print("📸 Screenshot do erro salvo como login_error.png")
                
                return False
                
        except Exception as e:
            print(f"❌ Erro durante o login: {str(e)}")
            
            # Tira screenshot para debug
            self.browser.driver.save_screenshot("login_exception.png")
            print("📸 Screenshot da exceção salvo como login_exception.png")
            
            # Salva HTML da página para debug
            with open("login_page.html", "w", encoding="utf-8") as f:
                f.write(self.browser.driver.page_source)
            print("💾 HTML da página de login salvo como login_page.html")
            
            return False
    
    def ensure_login(self):
        """Garante que está logado no sistema"""
        if not self.logged_in:
            return self.login()
        return True
    
    def wait_for_element(self, by, value, timeout=10):
        """Aguarda elemento aparecer"""
        try:
            return WebDriverWait(self.browser.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except Exception as e:
            print(f"❌ Elemento não encontrado: {by}={value} - {e}")
            return None
    
    def safe_find_element(self, by, value, default=None):
        """Encontra elemento de forma segura"""
        try:
            return self.browser.driver.find_element(by, value)
        except:
            return default
    
    def safe_find_elements(self, by, value):
        """Encontra elementos de forma segura"""
        try:
            return self.browser.driver.find_elements(by, value)
        except:
            return []