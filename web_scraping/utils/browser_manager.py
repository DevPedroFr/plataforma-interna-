# web_scraping/utils/browser_manager.py
import os
import shutil
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import time
import logging

logger = logging.getLogger(__name__)


class BrowserManager:
    def __init__(self):
        self.driver = None
    
    def _get_chromedriver_path(self):
        """
        Retorna o caminho do ChromeDriver.
        Primeiro tenta usar o do sistema (Docker), depois tenta webdriver_manager (local).
        """
        # 1. Verificar se existe no PATH do sistema (Docker)
        system_chromedriver = shutil.which('chromedriver')
        if system_chromedriver:
            logger.info(f"Usando ChromeDriver do sistema: {system_chromedriver}")
            return system_chromedriver
        
        # 2. Verificar caminho comum no Linux
        if os.path.exists('/usr/local/bin/chromedriver'):
            logger.info("Usando ChromeDriver em /usr/local/bin/chromedriver")
            return '/usr/local/bin/chromedriver'
        
        # 3. Fallback: usar webdriver_manager (para desenvolvimento local)
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            path = ChromeDriverManager().install()
            logger.info(f"Usando ChromeDriver via webdriver_manager: {path}")
            return path
        except Exception as e:
            logger.error(f"Erro ao obter ChromeDriver: {e}")
            raise Exception("ChromeDriver não encontrado. Instale o Chrome/ChromeDriver ou use Docker.")
    
    def start_browser(self, headless=True):
        """Inicia o navegador Chrome"""
        if self.driver:
            try:
                # Tenta acessar uma propriedade para verificar se o driver ainda é válido
                _ = self.driver.current_url
                logger.info("✅ Navegador já está iniciado!")
                return self.driver
            except:
                # Se der erro, fecha o driver atual
                self.quit_browser()
        
        try:
            options = Options()
            
            if headless:
                options.add_argument('--headless=new')  # Novo modo headless
            
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('excludeSwitches', ['enable-automation'])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Obtém o caminho do ChromeDriver
            chromedriver_path = self._get_chromedriver_path()
            service = Service(chromedriver_path)
            self.driver = webdriver.Chrome(service=service, options=options)
            
            if not self.driver:
                raise Exception("Driver não foi inicializado corretamente")
            
            # Configura timeouts
            self.driver.implicitly_wait(10)  # Espera implícita global
            self.driver.set_page_load_timeout(30)  # Timeout de carregamento de página
            
            # Remove o indicador de automação
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("✅ Navegador iniciado com sucesso!")
            return self.driver
            
        except Exception as e:
            logger.warning(f"❌ Erro ao iniciar navegador: {e}")
            raise
    
    def quit_browser(self):
        """Fecha o navegador"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("✅ Navegador fechado!")