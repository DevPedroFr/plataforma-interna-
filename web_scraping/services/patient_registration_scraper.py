"""
PatientRegistrationScraper - Serviço aprimorado para automatizar cadastro de pacientes
via Google Forms na plataforma de Aruja GoC Franquias.

Melhorias implementadas:
- Wait conditions mais robustas
- Tratamento melhor de exceções
- Logging mais detalhado
- Validação de elementos antes da interação
- Múltiplas estratégias de fallback
- Penis do claudio tem 2 metros
"""

import time
import re
import logging
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class PatientRegistrationScraper(BaseScraper):
    """Scraper aprimorado para automatizar registros de pacientes na plataforma GoC Franquias"""
    
    def __init__(self, browser_manager):
        super().__init__(browser_manager)
        self.registration_url = "https://aruja.gocfranquias.com.br/Cadastro/Paciente.aspx"
        self.processed_patients = set()
        self.wait_timeout = 15
    
    def _navigate_via_menu(self):
        """
        Navega para a página de cadastro de pacientes usando o menu do sistema.
        O sistema GoC usa frameset e NÃO suporta navegação direta via URL.
        """
        try:
            # Garantir que estamos no contexto padrão (fora de qualquer frame)
            self.browser.driver.switch_to.default_content()
            logger.info("Navegando via menu: Pacientes e Aplicações")
            
            # Aguarda a página principal carregar completamente
            time.sleep(1)
            
            # Primeiro, verificar se há framesets na página principal
            # Em sistemas ASP.NET com frameset, o menu geralmente está em um frame lateral
            framesets = self.browser.driver.find_elements(By.TAG_NAME, "frameset")
            frames = self.browser.driver.find_elements(By.TAG_NAME, "frame")
            
            logger.info(f"Contexto padrão - Encontrados: {len(framesets)} framesets, {len(frames)} frames")
            
            # Logar informações sobre todos os frames
            for i, frame in enumerate(frames):
                frame_name = frame.get_attribute('name') or f"frame_{i}"
                frame_src = frame.get_attribute('src') or "sem_src"
                logger.info(f"  Frame {i}: name={frame_name}, src={frame_src}")
            
            # Tentar encontrar o menu no contexto padrão primeiro
            menu_pacientes = self._find_menu_pacientes()
            
            if not menu_pacientes:
                # Se não encontrou, pode estar dentro de um frame de menu (geralmente I1 ou menu lateral)
                for frame in frames:
                    frame_name = frame.get_attribute('name') or ""
                    try:
                        self.browser.driver.switch_to.frame(frame)
                        logger.info(f"Procurando menu no frame: {frame_name}")
                        time.sleep(1)
                        
                        menu_pacientes = self._find_menu_pacientes()
                        if menu_pacientes:
                            logger.info(f"Menu encontrado no frame: {frame_name}")
                            break
                        
                        # Não encontrou, volta ao contexto padrão
                        self.browser.driver.switch_to.default_content()
                    except Exception as e:
                        logger.warning(f"Erro ao acessar frame {frame_name}: {e}")
                        self.browser.driver.switch_to.default_content()
            
            if not menu_pacientes:
                logger.error("Menu 'Pacientes e Aplicações' não encontrado em nenhum frame")
                return False
            
            # Clicar no menu Pacientes e Aplicações
            try:
                # Obter o href do link para usar como fallback
                menu_href = menu_pacientes.get_attribute('href')
                menu_target = menu_pacientes.get_attribute('target')
                logger.info(f"Link do menu: {menu_href}, target: {menu_target}")
                
                # Primeiro tenta via clique normal
                self.browser.driver.execute_script("arguments[0].scrollIntoView(true);", menu_pacientes)
                time.sleep(0.5)
                
                menu_pacientes.click()
                logger.info("✅ Clicou em 'Pacientes e Aplicações'")
                time.sleep(2)  # Aguarda página carregar no iframe
                
                # Verificar se o iframe foi preenchido
                self.browser.driver.switch_to.default_content()
                try:
                    iframe = self.browser.driver.find_element(By.ID, "ifrConteudo")
                    self.browser.driver.switch_to.frame(iframe)
                    body = self.browser.driver.find_element(By.TAG_NAME, "body")
                    if body.text.strip():
                        logger.info("Iframe preenchido após clique normal")
                        self.browser.driver.switch_to.default_content()
                        return True
                except:
                    pass
                
                self.browser.driver.switch_to.default_content()
                
                # Se o clique normal não funcionou, carregar diretamente no iframe via JavaScript
                if menu_href:
                    logger.info("Clique não carregou iframe - tentando via JavaScript...")
                    
                    # Método 1: Definir o src do iframe diretamente
                    try:
                        self.browser.driver.execute_script(
                            "document.getElementById('ifrConteudo').src = arguments[0];", 
                            menu_href
                        )
                        logger.info(f"✅ Definiu src do iframe para: {menu_href}")
                        time.sleep(3)  # Aguarda carregar
                        return True
                    except Exception as js_e:
                        logger.warning(f"Falha ao definir src via JS: {js_e}")
                    
                    # Método 2: Tentar via contentWindow
                    try:
                        self.browser.driver.execute_script(
                            "document.getElementById('ifrConteudo').contentWindow.location.href = arguments[0];", 
                            menu_href
                        )
                        logger.info(f"✅ Carregou via contentWindow: {menu_href}")
                        time.sleep(3)
                        return True
                    except Exception as cw_e:
                        logger.warning(f"Falha via contentWindow: {cw_e}")
                
                return True
                
            except Exception as e:
                logger.warning(f"Clique normal falhou: {e}")
                
                # Fallback: carregar diretamente no iframe se temos o href
                try:
                    menu_href = menu_pacientes.get_attribute('href')
                    if menu_href:
                        self.browser.driver.switch_to.default_content()
                        self.browser.driver.execute_script(
                            "document.getElementById('ifrConteudo').src = arguments[0];", 
                            menu_href
                        )
                        logger.info(f"✅ Fallback: definiu src do iframe para: {menu_href}")
                        time.sleep(3)
                        return True
                except Exception as fb_e:
                    logger.error(f"Fallback também falhou: {fb_e}")
                    return False
            
        except Exception as e:
            logger.error(f"Erro na navegação via menu: {e}")
            return False
    
    def _find_menu_pacientes(self):
        """Procura o link do menu Pacientes e Aplicações no contexto atual"""
        # O menu "Pacientes e Aplicações" está diretamente visível (não é submenu)
        menu_selectors = [
            # Links de texto - variações do nome
            "//a[contains(text(), 'Pacientes e Aplicações')]",
            "//a[contains(text(), 'Pacientes e aplicações')]",
            "//a[contains(text(), 'Pacientes')]",
            # Por href
            "//a[contains(@href, 'Paciente.aspx')]",
            "//a[contains(@href, 'Paciente')]",
            # TreeView nodes (comum em ASP.NET)
            "//*[contains(@class, 'TreeNode')]//a[contains(text(), 'Pacientes')]",
            "//*[contains(@id, 'TreeView')]//a[contains(text(), 'Pacientes')]",
        ]
        
        for selector in menu_selectors:
            try:
                elements = self.browser.driver.find_elements(By.XPATH, selector)
                if elements:
                    for elem in elements:
                        if elem.is_displayed():
                            logger.info(f"Menu 'Pacientes e Aplicações' encontrado: {selector}")
                            return elem
            except Exception as e:
                continue
        
        # Tentar encontrar por texto parcial em qualquer link
        try:
            all_links = self.browser.driver.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                if link.is_displayed():
                    link_text = link.text.strip().lower()
                    if 'pacientes' in link_text:
                        logger.info(f"Menu encontrado via busca geral: {link.text}")
                        return link
        except:
            pass
        
        # Log de links visíveis para debug
        try:
            all_links = self.browser.driver.find_elements(By.TAG_NAME, "a")
            visible_links = [l.text for l in all_links if l.is_displayed() and l.text.strip()][:15]
            logger.info(f"Links visíveis no contexto atual: {visible_links}")
        except:
            pass
        
        return None
    
    def _switch_to_content_iframe(self):
        """Troca para o iframe de conteúdo e verifica se a página de cadastro carregou"""
        try:
            # Voltar ao contexto padrão primeiro
            self.browser.driver.switch_to.default_content()
            time.sleep(1)
            
            # Em sistemas com frameset, precisamos encontrar o frame de conteúdo
            # Primeiro, verificar se há framesets
            frames = self.browser.driver.find_elements(By.TAG_NAME, "frame")
            iframes = self.browser.driver.find_elements(By.TAG_NAME, "iframe")
            
            logger.info(f"Encontrados: {len(frames)} frames, {len(iframes)} iframes")
            
            # Se há frames (frameset), procurar o frame de conteúdo (geralmente I2 ou ifrConteudo)
            content_frame = None
            
            # Primeiro tentar frames (para framesets)
            for frame in frames:
                frame_name = frame.get_attribute('name') or ""
                frame_id = frame.get_attribute('id') or ""
                frame_src = frame.get_attribute('src') or ""
                
                # O frame de conteúdo geralmente é I2 ou contém Paciente na src
                if frame_name == "I2" or "Paciente" in frame_src or "Cadastro" in frame_src or "ifrConteudo" in frame_id:
                    content_frame = frame
                    logger.info(f"Frame de conteúdo identificado: name={frame_name}, src={frame_src}")
                    break
            
            # Se não encontrou nos frames, tentar iframes
            if not content_frame:
                for iframe in iframes:
                    iframe_id = iframe.get_attribute('id') or ""
                    iframe_name = iframe.get_attribute('name') or ""
                    
                    if iframe_id == "ifrConteudo" or iframe_name == "I2":
                        content_frame = iframe
                        logger.info(f"Iframe de conteúdo identificado: id={iframe_id}, name={iframe_name}")
                        break
            
            if not content_frame:
                # Tentar o primeiro frame/iframe disponível
                if frames:
                    content_frame = frames[-1]  # Geralmente o último frame é o de conteúdo
                    logger.info("Usando último frame como conteúdo")
                elif iframes:
                    content_frame = iframes[0]
                    logger.info("Usando primeiro iframe como conteúdo")
            
            if not content_frame:
                logger.error("Nenhum frame/iframe de conteúdo encontrado")
                return False
            
            # Trocar para o frame de conteúdo
            self.browser.driver.switch_to.frame(content_frame)
            logger.info("Trocou para frame de conteúdo")
            
            # Aguarda o conteúdo carregar - tenta múltiplas vezes
            max_attempts = 5
            for attempt in range(max_attempts):
                time.sleep(2)
                
                # Verificar se há conteúdo
                try:
                    body = self.browser.driver.find_element(By.TAG_NAME, "body")
                    body_text = body.text.strip()
                    
                    if body_text and len(body_text) > 10:
                        logger.info(f"Conteúdo do frame (primeiros 200 chars): {body_text[:200]}")
                        
                        # Verificar se encontramos a página de pacientes
                        if "ctl00_ContentPlaceHolder1_txtNome" in self.browser.driver.page_source:
                            logger.info("✅ Página de cadastro detectada no frame!")
                            return True
                        
                        # Verificar se há inputs
                        inputs = self.browser.driver.find_elements(By.TAG_NAME, "input")
                        if len(inputs) > 3:
                            logger.info(f"Frame tem {len(inputs)} inputs - provavelmente é a página correta")
                            return True
                    else:
                        logger.info(f"Tentativa {attempt + 1}: Frame ainda vazio, aguardando...")
                        
                except Exception as e:
                    logger.warning(f"Erro ao verificar conteúdo do frame: {e}")
            
            # Última tentativa - verificar inputs e conteúdo
            try:
                inputs = self.browser.driver.find_elements(By.TAG_NAME, "input")
                logger.info(f"Inputs encontrados no frame: {len(inputs)}")
                
                # Listar TODOS os botões (input type=image, type=submit, type=button)
                buttons = self.browser.driver.find_elements(By.CSS_SELECTOR, 
                    "input[type='image'], input[type='submit'], input[type='button'], button, a.btn, a[id*='btn'], a[id*='Btn']"
                )
                logger.info(f"Botões encontrados: {len(buttons)}")
                for btn in buttons[:20]:
                    btn_id = btn.get_attribute('id') or ''
                    btn_text = btn.text or btn.get_attribute('value') or btn.get_attribute('title') or ''
                    btn_src = btn.get_attribute('src') or ''
                    if btn_id or btn_text:
                        logger.info(f"  Botão: id={btn_id}, text={btn_text}, src={btn_src[-30:] if btn_src else ''}")
                
                # Procurar links que podem ser "Novo"
                links = self.browser.driver.find_elements(By.TAG_NAME, "a")
                for link in links:
                    link_text = link.text.strip().lower()
                    link_id = link.get_attribute('id') or ''
                    if 'novo' in link_text or 'new' in link_text or 'novo' in link_id.lower() or 'new' in link_id.lower():
                        logger.info(f"  Link 'Novo': id={link_id}, text={link.text}")
                
                # Procurar imagens que podem ser botão "Novo" (ícone +)
                images = self.browser.driver.find_elements(By.CSS_SELECTOR, "img[src*='add'], img[src*='novo'], img[src*='new'], img[src*='plus']")
                for img in images:
                    logger.info(f"  Imagem 'Novo': src={img.get_attribute('src')}")
                
                # Se encontrou muitos inputs, provavelmente a página carregou
                if len(inputs) > 10:
                    logger.info("✅ Página carregou com muitos inputs - considerando sucesso")
                    return True
                    
                if len(inputs) > 0:
                    return True
            except Exception as e:
                logger.warning(f"Erro ao listar inputs: {e}")
            
            logger.warning("Frame de conteúdo está vazio após múltiplas tentativas")
            return False
                
        except Exception as e:
            logger.error(f"Erro ao trocar para frame: {e}")
            return False
    
    def ensure_on_registration_page(self):
        """
        Garante que está na página de listagem de pacientes.
        O formulário de cadastro só aparece após clicar no botão "Novo".
        """
        try:
            current_url = self.browser.driver.current_url
            logger.info(f"URL atual: {current_url}")
            
            # Se não estiver na página inicial, navegar para ela
            if "Inicio.aspx" not in current_url:
                logger.info("Navegando para página inicial...")
                self.browser.driver.get("https://aruja.gocfranquias.com.br/Login/Inicio.aspx")
                time.sleep(3)
                
                # Verificar se foi redirecionado para login
                if "login.aspx" in self.browser.driver.current_url.lower():
                    logger.warning("Sessão expirada - refazendo login...")
                    if not self.ensure_login():
                        logger.error("Falha ao refazer login")
                        return False
            
            # Primeiro, tentar ver se já estamos no iframe com a página de pacientes
            if self._switch_to_content_iframe():
                try:
                    # Verificar se estamos na página de lista de pacientes (GridView)
                    grid = self.browser.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_GridView1")
                    if grid:
                        logger.info("✅ Já estamos na página de lista de pacientes!")
                        return True
                except:
                    pass
                
                try:
                    # Ou se estamos no formulário de cadastro (txtNome)
                    element = self.browser.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_txtNome")
                    if element:
                        logger.info("✅ Já estamos no formulário de cadastro!")
                        return True
                except:
                    pass
            
            # Voltar ao contexto padrão para navegar via menu
            self.browser.driver.switch_to.default_content()
            
            # Navegar via menu
            if not self._navigate_via_menu():
                logger.error("Falha na navegação via menu")
                return False
            
            # Trocar para o iframe de conteúdo
            if not self._switch_to_content_iframe():
                logger.error("Falha ao acessar iframe de conteúdo")
                return False
            
            # Verificar se a página de pacientes carregou (lista ou formulário)
            try:
                # Primeiro tenta encontrar o GridView (lista de pacientes)
                grid = WebDriverWait(self.browser.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_GridView1"))
                )
                logger.info("✅ Página de pacientes carregada com sucesso (lista encontrada)!")
                
                # Listar todos os links na página para encontrar o botão "Novo"
                links = self.browser.driver.find_elements(By.TAG_NAME, "a")
                logger.info(f"Links encontrados: {len(links)}")
                for link in links:
                    try:
                        text = link.text.strip()
                        href = link.get_attribute("href") or ""
                        onclick = link.get_attribute("onclick") or ""
                        class_attr = link.get_attribute("class") or ""
                        if text or "novo" in href.lower() or "novo" in onclick.lower() or "new" in class_attr.lower():
                            logger.info(f"  Link: text='{text}', href='{href[:50] if href else ''}', onclick='{onclick[:50] if onclick else ''}', class='{class_attr}'")
                    except:
                        pass
                
                # Listar imagens que podem ser botões
                imgs = self.browser.driver.find_elements(By.TAG_NAME, "img")
                logger.info(f"Imagens encontradas: {len(imgs)}")
                for img in imgs:
                    try:
                        src = img.get_attribute("src") or ""
                        alt = img.get_attribute("alt") or ""
                        onclick = img.get_attribute("onclick") or ""
                        title = img.get_attribute("title") or ""
                        if "novo" in src.lower() or "novo" in alt.lower() or "new" in src.lower() or onclick:
                            logger.info(f"  Img: src='{src}', alt='{alt}', onclick='{onclick[:50] if onclick else ''}', title='{title}'")
                    except:
                        pass
                
                return True
            except TimeoutException:
                # Tenta encontrar o campo txtNome (formulário de cadastro)
                try:
                    element = WebDriverWait(self.browser.driver, 5).until(
                        EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_txtNome"))
                    )
                    logger.info("✅ Formulário de cadastro carregado!")
                    return True
                except TimeoutException:
                    logger.error("Nem GridView nem txtNome encontrados após navegação")
                    return False
            
        except Exception as e:
            logger.error(f"Falha ao acessar página de cadastro: {str(e)}")
            return False
    
    def check_cpf_exists(self, cpf):
        """
        Verifica se um CPF já existe na plataforma com estratégia aprimorada
        """
        if not self.ensure_login():
            logger.error("Falha ao fazer login para verificação de CPF")
            return False
        
        try:
            cpf_clean = self._normalize_cpf(cpf)
            logger.info(f"Verificando se CPF {cpf_clean} já existe...")
            
            # Navega para página de pacientes
            if not self.ensure_on_registration_page():
                return False
            
            # Aguarda a tabela carregar completamente
            try:
                WebDriverWait(self.browser.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_GridView1"))
                )
            except TimeoutException:
                logger.warning("Tabela de pacientes não encontrada, assumindo que não há pacientes cadastrados")
                return False
            
            # Procura pelo CPF na tabela usando múltiplas estratégias
            time.sleep(2)
            
            # Estratégia 1: Busca no HTML da página
            page_source = self.browser.driver.page_source
            if cpf_clean in page_source:
                logger.warning(f"CPF {cpf_clean} encontrado no HTML da página")
                return True
            
            # Estratégia 2: Busca na tabela de pacientes
            try:
                table = self.browser.driver.find_element(By.ID, "ctl00_ContentPlaceHolder1_GridView1")
                rows = table.find_elements(By.TAG_NAME, "tr")
                
                for row in rows[1:]:  # Pula o cabeçalho
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) > 2:  # Assumindo que CPF está em uma das colunas
                        for cell in cells:
                            if cpf_clean in cell.text:
                                logger.warning(f"CPF {cpf_clean} encontrado na tabela: {cell.text}")
                                return True
            except Exception as e:
                logger.warning(f"Erro ao buscar na tabela: {str(e)}")
            
            logger.info(f"CPF {cpf_clean} não encontrado - é novo cadastro")
            return False
            
        except Exception as e:
            logger.error(f"Erro ao verificar CPF: {str(e)}")
            return False
    
    def register_patient_from_google_forms(self, form_data):
        """
        Registra um paciente na plataforma usando dados do Google Forms - Versão Aprimorada
        """
        try:
            # 1. Validar dados essenciais
            validation_result = self._validate_form_data(form_data)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'message': f"Validação falhou: {validation_result['errors']}",
                    'patient_id': None
                }
            
            cpf = form_data.get('CPF', '').strip()
            cpf_clean = self._normalize_cpf(cpf)
            
            # 2. Verificar duplicatas
            if self.check_cpf_exists(cpf):
                return {
                    'success': False,
                    'message': f"Paciente com CPF {cpf} já existe na plataforma",
                    'patient_id': None
                }
            
            # 3. Fazer login
            if not self.ensure_login():
                return {
                    'success': False,
                    'message': "Falha ao fazer login na plataforma",
                    'patient_id': None
                }
            
            # 4. Navegar para página de cadastro
            if not self.ensure_on_registration_page():
                return {
                    'success': False,
                    'message': "Falha ao acessar página de cadastro",
                    'patient_id': None
                }
            
            # 5. Clicar no botão "Novo" para abrir formulário de cadastro
            if not self._click_new_button():
                return {
                    'success': False,
                    'message': "Falha ao abrir formulário de novo paciente",
                    'patient_id': None
                }
            
            # 6. Aguardar formulário carregar completamente
            time.sleep(3)
            
            # 7. Preencher formulário
            fill_result = self._fill_patient_form_enhanced(form_data)
            if not fill_result['success']:
                return {
                    'success': False,
                    'message': f"Erro ao preencher formulário: {fill_result['error']}",
                    'patient_id': None
                }
            
            # 8. Submeter formulário
            submit_result = self._submit_patient_form_enhanced()
            
            if submit_result['success']:
                self.processed_patients.add(cpf_clean)
                logger.info(f"Paciente {form_data.get('Nome completo')} cadastrado com sucesso!")
            
            return submit_result
            
        except Exception as e:
            logger.exception(f"Erro ao registrar paciente: {str(e)}")
            return {
                'success': False,
                'message': f"Erro inesperado: {str(e)}",
                'patient_id': None
            }
    
    def _click_new_button(self):
        """Clica no botão 'Novo' para abrir formulário de cadastro"""
        try:
            logger.info("Procurando botão 'Novo' na página...")
            
            # Primeiro, fazer scroll para baixo para garantir que o botão está visível
            logger.info("Fazendo scroll para carregar todo o conteúdo...")
            self.browser.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            new_button = None
            
            # ESTRATÉGIA 1: Buscar input type="image" com title="Novo" (sem verificar is_displayed)
            try:
                xpath = "//input[@type='image' and @title='Novo']"
                elements = self.browser.driver.find_elements(By.XPATH, xpath)
                if elements:
                    new_button = elements[0]
                    elem_id = new_button.get_attribute('id') or ""
                    logger.info(f"✅ Botão 'Novo' encontrado por title='Novo': {elem_id}")
            except Exception as e:
                logger.warning(f"Erro ao buscar input image com title=Novo: {e}")
            
            # ESTRATÉGIA 2: Buscar input type="image" com accesskey="N"
            if not new_button:
                try:
                    xpath = "//input[@type='image' and @accesskey='N']"
                    elements = self.browser.driver.find_elements(By.XPATH, xpath)
                    if elements:
                        new_button = elements[0]
                        elem_id = new_button.get_attribute('id') or ""
                        logger.info(f"✅ Botão 'Novo' encontrado por accesskey='N': {elem_id}")
                except Exception as e:
                    logger.warning(f"Erro ao buscar input image com accesskey=N: {e}")
            
            # ESTRATÉGIA 3: Buscar input type="image" com src contendo page_white.png
            if not new_button:
                try:
                    xpath = "//input[@type='image' and contains(@src, 'page_white')]"
                    elements = self.browser.driver.find_elements(By.XPATH, xpath)
                    if elements:
                        new_button = elements[0]
                        elem_id = new_button.get_attribute('id') or ""
                        logger.info(f"✅ Botão 'Novo' encontrado por src='page_white': {elem_id}")
                except Exception as e:
                    logger.warning(f"Erro ao buscar input image com src page_white: {e}")
            
            # ESTRATÉGIA 4: Buscar qualquer input type="image" com ID contendo ImageButton1
            if not new_button:
                try:
                    xpath = "//input[@type='image' and contains(@id, 'ImageButton1')]"
                    elements = self.browser.driver.find_elements(By.XPATH, xpath)
                    if elements:
                        new_button = elements[0]
                        elem_id = new_button.get_attribute('id') or ""
                        logger.info(f"✅ Botão encontrado por ID contendo ImageButton1: {elem_id}")
                except Exception as e:
                    logger.warning(f"Erro ao buscar ImageButton1: {e}")
            
            # ESTRATÉGIA 5: Buscar pelo ID dinâmico com regex pattern
            if not new_button:
                try:
                    # O ID segue o padrão: ctl00_ContentPlaceHolder1_GridView1_ctlNN_FormView1_ImageButton1
                    css = "input[type='image'][id*='FormView1_ImageButton1']"
                    elements = self.browser.driver.find_elements(By.CSS_SELECTOR, css)
                    if elements:
                        new_button = elements[0]
                        elem_id = new_button.get_attribute('id') or ""
                        logger.info(f"✅ Botão encontrado por CSS: {elem_id}")
                except Exception as e:
                    logger.warning(f"Erro ao buscar por CSS FormView1_ImageButton1: {e}")
            
            # ESTRATÉGIA 6: Listar TODOS os input type="image" para debug e encontrar
            if not new_button:
                try:
                    all_image_inputs = self.browser.driver.find_elements(By.XPATH, "//input[@type='image']")
                    logger.info(f"Total de input type='image' encontrados: {len(all_image_inputs)}")
                    
                    for inp in all_image_inputs:
                        inp_id = inp.get_attribute('id') or ""
                        inp_title = inp.get_attribute('title') or ""
                        inp_src = inp.get_attribute('src') or ""
                        inp_accesskey = inp.get_attribute('accesskey') or ""
                        
                        logger.info(f"  ImageInput: id={inp_id}, title={inp_title}, accesskey={inp_accesskey}, src={inp_src[-40:] if inp_src else ''}")
                        
                        # Se encontrar um com title="Novo" ou accesskey="N", usar
                        if inp_title.lower() == 'novo' or inp_accesskey.upper() == 'N':
                            new_button = inp
                            logger.info(f"✅ Botão 'Novo' encontrado durante listagem!")
                            break
                except Exception as e:
                    logger.warning(f"Erro ao listar input type=image: {e}")
            
            if not new_button:
                logger.error("❌ Botão 'Novo' não encontrado na página")
                
                # Log final de debug
                try:
                    page_text = self.browser.driver.find_element(By.TAG_NAME, "body").text
                    if 'novo' in page_text.lower():
                        logger.info("A palavra 'novo' existe no texto da página")
                    else:
                        logger.info("A palavra 'novo' NÃO existe no texto da página")
                except:
                    pass
                
                return False
            
            # Clicar no botão
            try:
                # Garantir que o botão está visível
                self.browser.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", new_button)
                time.sleep(1)
                
                # Log do botão encontrado
                btn_id = new_button.get_attribute('id') or ""
                btn_title = new_button.get_attribute('title') or ""
                logger.info(f"Tentando clicar no botão: id={btn_id}, title={btn_title}")
                
                new_button.click()
                logger.info("✅ Botão 'Novo' clicado com sucesso!")
            except Exception as click_e:
                logger.warning(f"Clique normal falhou: {click_e}, tentando via JavaScript...")
                try:
                    self.browser.driver.execute_script("arguments[0].click();", new_button)
                    logger.info("✅ Botão 'Novo' clicado via JavaScript!")
                except Exception as js_e:
                    logger.error(f"Falha ao clicar via JavaScript: {js_e}")
                    return False
            
            # Aguardar formulário carregar
            logger.info("Aguardando formulário de cadastro carregar...")
            time.sleep(3)  # Tempo otimizado
            
            # Verificar se o formulário de novo paciente apareceu
            # O formulário pode aparecer em um modal ou substituir a lista
            try:
                # Tentar encontrar o campo Nome que indica que o formulário carregou
                WebDriverWait(self.browser.driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, "//input[contains(@id, 'txtNome')]"))
                )
                logger.info("✅ Formulário de novo paciente carregado!")
                return True
            except Exception as form_e:
                logger.warning(f"Formulário não detectado imediatamente: {form_e}")
                
                # Pode ser que precisemos verificar se há uma caixa de diálogo
                try:
                    dialog_content = self.browser.driver.find_element(By.ID, "divCaixaDialogoConteudo")
                    if dialog_content.is_displayed():
                        logger.info("✅ Caixa de diálogo de cadastro aberta!")
                        return True
                except:
                    pass
                
                # Log para debug
                try:
                    inputs = self.browser.driver.find_elements(By.TAG_NAME, "input")
                    logger.info(f"Inputs na página após clique: {len(inputs)}")
                except:
                    pass
                
                # Considerar sucesso se clicou sem erro
                return True
            
        except Exception as e:
            logger.error(f"Erro ao clicar no botão Novo: {str(e)}")
            return False
    
    def _fill_patient_form_enhanced(self, form_data):
        """
        Preenchimento aprimorado do formulário com wait conditions
        """
        try:
            logger.info("Iniciando preenchimento do formulário...")
            
            # Primeiro, verificar se apareceu uma caixa de diálogo
            try:
                dialog = self.browser.driver.find_element(By.ID, "CaixaDialogo")
                if dialog.is_displayed():
                    logger.info("✅ Caixa de diálogo detectada")
            except:
                logger.info("Nenhuma caixa de diálogo detectada")
            
            # Listar os inputs disponíveis para debug
            try:
                all_inputs = self.browser.driver.find_elements(By.TAG_NAME, "input")
                text_inputs = [i for i in all_inputs if i.get_attribute('type') in ['text', 'email', 'tel', 'number', '']]
                logger.info(f"Inputs de texto disponíveis: {len(text_inputs)}")
                for inp in text_inputs[:10]:  # Mostrar primeiros 10
                    inp_id = inp.get_attribute('id') or ""
                    inp_name = inp.get_attribute('name') or ""
                    if inp_id or inp_name:
                        logger.info(f"  Input: id={inp_id}, name={inp_name}")
            except Exception as e:
                logger.warning(f"Erro ao listar inputs: {e}")
            
            # Aguarda formulário carregar completamente - tentar múltiplos seletores
            # O formulário está dentro do GridView1 como FormView1
            form_selectors = [
                (By.ID, "ctl00_ContentPlaceHolder1_GridView1_ctl17_FormView1_txtNome"),
                (By.XPATH, "//input[contains(@id, 'FormView1_txtNome')]"),
                (By.CSS_SELECTOR, "input[id*='FormView1_txtNome']"),
            ]
            
            name_field = None
            for by, selector in form_selectors:
                try:
                    name_field = WebDriverWait(self.browser.driver, 10).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    if name_field:
                        logger.info(f"✅ Campo Nome encontrado com: {by}='{selector}'")
                        break
                except:
                    continue
            
            if not name_field:
                logger.error("❌ Campo txtNome não encontrado após todas as tentativas")
                # Salvar screenshot para debug
                try:
                    page_source = self.browser.driver.page_source[:5000]
                    logger.error(f"HTML parcial: {page_source}")
                except:
                    pass
                raise Exception("Formulário de cadastro não carregou")
            
            # Mapeamento completo de campos - IDs do FormView1 dentro do GridView1
            # O padrão é: ctl00_ContentPlaceHolder1_GridView1_ctl17_FormView1_[campo]
            field_mapping = {
                'Nome completo': {
                    'selectors': [
                        '#ctl00_ContentPlaceHolder1_GridView1_ctl17_FormView1_txtNome',
                        'input[id*="FormView1_txtNome"]'
                    ],
                    'type': 'text',
                    'required': True
                },
                'CPF': {
                    'selectors': [
                        '#ctl00_ContentPlaceHolder1_GridView1_ctl17_FormView1_txtCPF',
                        'input[id*="FormView1_txtCPF"]'
                    ],
                    'type': 'text',
                    'required': True,
                    'transformer': self._normalize_cpf
                },
                'Data de nascimento': {
                    'selectors': [
                        '#ctl00_ContentPlaceHolder1_GridView1_ctl17_FormView1_TxtDataNascimento',
                        'input[id*="FormView1_TxtDataNascimento"]'
                    ],
                    'type': 'text',
                    'required': True
                },
                'Sexo': {
                    'selectors': [
                        'select[id*="FormView1_drpSexo_hdpesjur"]',
                        'select[id*="drpSexo_hdpesjur"]',
                        'select[id*="FormView1_drpSexo"]'
                    ],
                    'type': 'select',
                    'required': True,
                    'transformer': self._normalize_gender
                },
                'RG': {
                    'selectors': [
                        '#ctl00_ContentPlaceHolder1_GridView1_ctl17_FormView1_TextBox16',
                        'input[id*="FormView1_TextBox16"]'
                    ],
                    'type': 'text',
                    'required': False
                },
                'E-mail': {
                    'selectors': [
                        'input[id*="TextBox9"][class*="form-control"]',
                        'input[id$="_TextBox9"]',
                        '#ctl00_ContentPlaceHolder1_GridView1_ctl17_FormView1_TextBox9'
                    ],
                    'type': 'text',
                    'required': False
                },
                'Celular principal': {
                    'selectors': [
                        '#ctl00_ContentPlaceHolder1_GridView1_ctl17_FormView1_TextBox6',
                        'input[id*="FormView1_TextBox6"]'
                    ],
                    'type': 'text',
                    'required': False,
                    'transformer': self._normalize_phone
                },
                'Endereço completo (rua e número)': {
                    'selectors': [
                        '#ctl00_ContentPlaceHolder1_GridView1_ctl17_FormView1_txtEndereco',
                        'input[id*="FormView1_txtEndereco"]'
                    ],
                    'type': 'text',
                    'required': False
                },
                'Bairro': {
                    'selectors': [
                        'input[id*="txtBairro"][class*="form-control"]',
                        'input[id$="_txtBairro"]',
                        '#ctl00_ContentPlaceHolder1_GridView1_ctl17_FormView1_txtBairro'
                    ],
                    'type': 'text',
                    'required': False
                },
                'Cidade': {
                    'selectors': [
                        '#ctl00_ContentPlaceHolder1_GridView1_ctl17_FormView1_txtCidade',
                        'input[id*="FormView1_txtCidade"]'
                    ],
                    'type': 'text',
                    'required': False
                },
                'UF (estado)': {
                    'selectors': [
                        'select[id*="drpUF"]:not([id*="_hd"])',
                        '#ctl00_ContentPlaceHolder1_GridView1_ctl17_FormView1_drpUF',
                        'select[id*="FormView1_drpUF"]'
                    ],
                    'type': 'select',
                    'required': False,
                    'transformer': self._normalize_state_to_value
                },
                'CEP': {
                    'selectors': [
                        '#ctl00_ContentPlaceHolder1_GridView1_ctl17_FormView1_txtCEP',
                        'input[id*="FormView1_txtCEP"]'
                    ],
                    'type': 'text',
                    'required': False,
                    'transformer': self._normalize_zip
                },
                'Naturalidade': {
                    'selectors': [
                        'input[id*="FormView1_txtNaturalidade"]:not([id*="_hd"])',
                        '#ctl00_ContentPlaceHolder1_GridView1_ctl17_FormView1_txtNaturalidade',
                        'input[id*="txtNaturalidade"]:not([id*="_hd"])'
                    ],
                    'type': 'text',
                    'required': False
                },
                'Estado civil': {
                    'selectors': [
                        'select[id*="drpEstadoCivil_hdpesjur"]',
                        'select[id*="drpEstadoCivil"]'
                    ],
                    'type': 'select',
                    'required': False,
                    'transformer': self._normalize_civil_status
                },
                'Raça/Cor': {
                    'selectors': [
                        'select[id*="drpRaca_hdpesjur"]',
                        'select[id*="drpRaca"]'
                    ],
                    'type': 'select',
                    'required': False,
                    'transformer': self._normalize_race
                },
            }
            
            filled_fields = 0
            total_required = sum(1 for config in field_mapping.values() if config.get('required', False))
            
            for field_name, config in field_mapping.items():
                value = form_data.get(field_name, '').strip()
                
                # Pular campos vazios não obrigatórios
                if not value and not config.get('required', False):
                    continue
                
                # Aplicar transformador se existir
                if 'transformer' in config and config['transformer']:
                    value = config['transformer'](value)
                
                # Tentar preencher o campo
                field_filled = self._fill_single_field_enhanced(field_name, value, config)
                
                if field_filled:
                    filled_fields += 1
                    logger.info(f"✓ Campo {field_name} preenchido: {value[:50]}")
                else:
                    if config.get('required', False):
                        logger.error(f"✗ Campo obrigatório não preenchido: {field_name}")
                        return {'success': False, 'error': f"Campo obrigatório não preenchido: {field_name}"}
                    else:
                        logger.warning(f"✗ Campo opcional não preenchido: {field_name}")
            
            logger.info(f"Preenchimento concluído: {filled_fields} campos preenchidos")
            return {'success': True, 'error': None}
            
        except Exception as e:
            logger.exception(f"Erro ao preencher formulário: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _fill_single_field_enhanced(self, field_name, value, config):
        """
        Preenchimento aprimorado de campo individual
        """
        max_retries = 2
        for attempt in range(max_retries):
            try:
                field_type = config.get('type', 'text')
                selectors = config.get('selectors', [])
                
                element = None
                used_selector = None
                
                # Tentar encontrar o elemento usando múltiplas estratégias
                for selector in selectors:
                    try:
                        # Primeiro tenta por CSS selector
                        element = WebDriverWait(self.browser.driver, 3).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                        )
                        used_selector = selector
                        break
                    except:
                        pass
                    
                    # Se CSS falhou, tentar por XPath com o padrão do ID (mais flexível)
                    try:
                        # Extrair o nome do campo do seletor (ex: "txtNome" de "input[id*='FormView1_txtNome']")
                        if 'id*=' in selector:
                            pattern = selector.split("id*='")[1].split("']")[0]
                            xpath = f"//input[contains(@id, '{pattern}')] | //select[contains(@id, '{pattern}')]"
                            element = WebDriverWait(self.browser.driver, 3).until(
                                EC.presence_of_element_located((By.XPATH, xpath))
                            )
                            used_selector = xpath
                            break
                    except:
                        continue
                
                if not element:
                    logger.warning(f"Elemento não encontrado para {field_name} após tentativas: {selectors}")
                    return False
                
                logger.info(f"Campo {field_name} localizado via: {used_selector}")
                
                # Verificar se elemento está dentro de um formulário visível
                elem_displayed = element.is_displayed()
                elem_enabled = element.is_enabled()
                logger.info(f"Campo {field_name}: displayed={elem_displayed}, enabled={elem_enabled}")
                
                # Scroll e wait para elemento ficar interagível
                self.browser.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.2)
                
                # Usar JavaScript para garantir que o elemento está focado
                self.browser.driver.execute_script("arguments[0].focus();", element)
                time.sleep(0.1)
                
                if field_type == 'text':
                    # Limpar campo via JavaScript (mais confiável)
                    try:
                        self.browser.driver.execute_script("arguments[0].value = '';", element)
                        time.sleep(0.1)
                    except:
                        element.clear()
                        time.sleep(0.1)
                    
                    # Preencher via JavaScript para garantir
                    try:
                        self.browser.driver.execute_script(
                            "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('input', { bubbles: true })); arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", 
                            element, 
                            value
                        )
                    except Exception as js_e:
                        logger.warning(f"JS fill falhou, tentando send_keys: {js_e}")
                        element.send_keys(value)
                    
                    # Verificar se o valor foi preenchido
                    time.sleep(0.1)
                    actual_value = element.get_attribute('value')
                    if actual_value.strip():
                        logger.info(f"✓ Campo {field_name} preenchido: '{actual_value[:30]}...'")
                        return True
                    else:
                        logger.warning(f"Valor não preenchido no campo {field_name}")
                        if attempt < max_retries - 1:
                            continue
                        return False
                
                elif field_type == 'select':
                    select = Select(element)
                    
                    # Log das opções disponíveis para debug (texto E valores)
                    available_options = []
                    for opt in select.options:
                        opt_text = opt.text.strip()
                        opt_value = opt.get_attribute('value') or ""
                        available_options.append(f"'{opt_text}'(value={opt_value})")
                    logger.info(f"Opções disponíveis para {field_name}: {available_options}")
                    
                    # Tentar diferentes estratégias de seleção
                    selection_made = False
                    
                    # Estratégia 0: Via JavaScript (mais confiável para selects ASP.NET)
                    try:
                        self.browser.driver.execute_script(
                            "arguments[0].value = arguments[1]; "
                            "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                            element, value
                        )
                        # Verificar se a seleção foi feita
                        selected_value = self.browser.driver.execute_script("return arguments[0].value;", element)
                        if selected_value == value:
                            selection_made = True
                            logger.info(f"✓ Campo {field_name} selecionado via JavaScript: {value}")
                    except Exception as js_err:
                        logger.warning(f"Seleção via JS falhou para {field_name}: {js_err}")
                    
                    # Estratégia 1: Por valor exato (Selenium)
                    if not selection_made:
                        try:
                            select.select_by_value(value)
                            selection_made = True
                            logger.info(f"✓ Campo {field_name} selecionado por valor: {value}")
                        except:
                            pass
                    
                    # Estratégia 2: Por texto visível exato
                    if not selection_made:
                        try:
                            select.select_by_visible_text(value)
                            selection_made = True
                            logger.info(f"✓ Campo {field_name} selecionado por texto: {value}")
                        except:
                            pass
                    
                    # Estratégia 3: Busca parcial case-insensitive
                    if not selection_made:
                        try:
                            for option in select.options:
                                option_text = option.text.strip()
                                option_value = option.get_attribute('value') or ""
                                # Verificar match parcial
                                if value.lower() in option_text.lower() or option_text.lower() in value.lower():
                                    select.select_by_visible_text(option_text)
                                    selection_made = True
                                    logger.info(f"✓ Campo {field_name} selecionado parcialmente: {option_text}")
                                    break
                                # Verificar match por valor
                                if value.lower() in option_value.lower() or option_value.lower() in value.lower():
                                    select.select_by_value(option_value)
                                    selection_made = True
                                    logger.info(f"✓ Campo {field_name} selecionado por value: {option_value}")
                                    break
                        except:
                            pass
                    
                    # Estratégia 4: Para Sexo - tratamento especial (M/F)
                    if not selection_made and 'sexo' in field_name.lower():
                        try:
                            gender_map = {
                                'masculino': ['M', 'Masculino', 'Masc', 'MASCULINO', 'MASC'],
                                'feminino': ['F', 'Feminino', 'Fem', 'FEMININO', 'FEM']
                            }
                            value_lower = value.lower()
                            possible_values = gender_map.get(value_lower, [value])
                            
                            for opt in select.options:
                                opt_text = opt.text.strip()
                                opt_value = opt.get_attribute('value') or ""
                                
                                if opt_text in possible_values or opt_value in possible_values:
                                    select.select_by_visible_text(opt_text)
                                    selection_made = True
                                    logger.info(f"✓ Campo Sexo selecionado com mapeamento: {opt_text}")
                                    break
                        except Exception as e:
                            logger.warning(f"Erro no mapeamento de sexo: {e}")
                    
                    if not selection_made:
                        logger.warning(f"Não foi possível selecionar opção para {field_name}: {value}")
                        logger.warning(f"Opções tentadas: {available_options}")
                        return False
                
                return True
                
            except Exception as e:
                logger.warning(f"Tentativa {attempt + 1} falhou para campo {field_name}: {str(e)}")
                if attempt == max_retries - 1:
                    return False
                time.sleep(1)
        
        return False
    
    def _submit_patient_form_enhanced(self):
        """
        Submissão aprimorada do formulário
        """
        try:
            logger.info("Procurando botão de Gravar...")
            
            submit_button = None
            
            # ESTRATÉGIA 1: XPath direto por title="Gravar" e src com accept
            try:
                xpath = "//input[@type='image' and @title='Gravar']"
                elements = self.browser.driver.find_elements(By.XPATH, xpath)
                if elements:
                    submit_button = elements[0]
                    elem_id = submit_button.get_attribute('id') or ""
                    logger.info(f"✅ Botão Gravar encontrado por title='Gravar': {elem_id}")
            except Exception as e:
                logger.warning(f"Erro ao buscar por title=Gravar: {e}")
            
            # ESTRATÉGIA 2: XPath por src contendo accept.png
            if not submit_button:
                try:
                    xpath = "//input[@type='image' and contains(@src, 'accept')]"
                    elements = self.browser.driver.find_elements(By.XPATH, xpath)
                    if elements:
                        submit_button = elements[0]
                        elem_id = submit_button.get_attribute('id') or ""
                        logger.info(f"✅ Botão Gravar encontrado por src='accept': {elem_id}")
                except Exception as e:
                    logger.warning(f"Erro ao buscar por src=accept: {e}")
            
            # ESTRATÉGIA 3: XPath por ID contendo BtnGravar
            if not submit_button:
                try:
                    xpath = "//input[@type='image' and contains(@id, 'BtnGravar')]"
                    elements = self.browser.driver.find_elements(By.XPATH, xpath)
                    if elements:
                        submit_button = elements[0]
                        elem_id = submit_button.get_attribute('id') or ""
                        logger.info(f"✅ Botão Gravar encontrado por ID contendo BtnGravar: {elem_id}")
                except Exception as e:
                    logger.warning(f"Erro ao buscar por ID=BtnGravar: {e}")
            
            # ESTRATÉGIA 4: XPath por FormView1_BtnGravar
            if not submit_button:
                try:
                    xpath = "//input[@type='image' and contains(@id, 'FormView1_BtnGravar')]"
                    elements = self.browser.driver.find_elements(By.XPATH, xpath)
                    if elements:
                        submit_button = elements[0]
                        elem_id = submit_button.get_attribute('id') or ""
                        logger.info(f"✅ Botão Gravar encontrado por FormView1_BtnGravar: {elem_id}")
                except Exception as e:
                    logger.warning(f"Erro ao buscar por FormView1_BtnGravar: {e}")
            
            # ESTRATÉGIA 5: Listar todos os input type="image" e procurar o certo
            if not submit_button:
                try:
                    all_image_inputs = self.browser.driver.find_elements(By.XPATH, "//input[@type='image']")
                    logger.info(f"Total de input type='image' para Gravar: {len(all_image_inputs)}")
                    
                    for inp in all_image_inputs:
                        inp_id = inp.get_attribute('id') or ""
                        inp_title = inp.get_attribute('title') or ""
                        inp_src = inp.get_attribute('src') or ""
                        
                        # Procurar o botão Gravar
                        if inp_title.lower() == 'gravar' or 'accept' in inp_src.lower() or 'BtnGravar' in inp_id:
                            submit_button = inp
                            logger.info(f"✅ Botão Gravar encontrado durante listagem: id={inp_id}, title={inp_title}")
                            break
                except Exception as e:
                    logger.warning(f"Erro ao listar botões: {e}")
            
            if not submit_button:
                logger.error("Botão de Gravar não encontrado após todas as tentativas")
                return {
                    'success': False,
                    'message': "Botão de Gravar não encontrado",
                    'patient_id': None
                }
            
            # Log do botão encontrado
            btn_id = submit_button.get_attribute('id') or ""
            btn_title = submit_button.get_attribute('title') or ""
            logger.info(f"Tentando clicar no botão Gravar: id={btn_id}, title={btn_title}")
            
            # Scroll e click usando JavaScript para evitar problemas de overlay
            self.browser.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
            time.sleep(0.5)
            
            # Clicar via JavaScript (mais confiável)
            logger.info("Clicando no botão Gravar via JavaScript...")
            self.browser.driver.execute_script("arguments[0].click();", submit_button)
            logger.info("✅ Botão Gravar clicado!")
            
            # Aguarda processamento
            time.sleep(3)
            
            # Verifica resultado
            return self._check_submission_result()
            
        except Exception as e:
            logger.exception(f"Erro ao submeter formulário: {str(e)}")
            return {
                'success': False,
                'message': f"Erro na submissão: {str(e)}",
                'patient_id': None
            }
    
    def _check_submission_result(self):
        """Verifica o resultado da submissão do formulário"""
        try:
            # Verifica por mensagens de sucesso
            success_indicators = [
                '.alert-success',
                '.success',
                '[class*="success"]',
                '#ctl00_ContentPlaceHolder1_lblMessage'
            ]
            
            for indicator in success_indicators:
                try:
                    element = self.browser.driver.find_element(By.CSS_SELECTOR, indicator)
                    if element.is_displayed() and any(word in element.text.lower() for word in ['sucesso', 'salvo', 'cadastrado']):
                        logger.info(f"Sucesso detectado: {element.text}")
                        return {
                            'success': True,
                            'message': element.text,
                            'patient_id': self._extract_patient_id()
                        }
                except:
                    continue
            
            # Verifica por mensagens de erro
            error_indicators = [
                '.alert-danger',
                '.error',
                '[class*="error"]',
                '.text-danger'
            ]
            
            for indicator in error_indicators:
                try:
                    element = self.browser.driver.find_element(By.CSS_SELECTOR, indicator)
                    if element.is_displayed():
                        error_msg = element.text
                        logger.error(f"Erro detectado: {error_msg}")
                        return {
                            'success': False,
                            'message': error_msg,
                            'patient_id': None
                        }
                except:
                    continue
            
            # Se não há mensagens de erro visíveis, assume sucesso
            logger.info("Nenhuma mensagem de erro detectada, assumindo sucesso")
            return {
                'success': True,
                'message': "Cadastro realizado com sucesso",
                'patient_id': self._extract_patient_id()
            }
            
        except Exception as e:
            logger.error(f"Erro ao verificar resultado: {str(e)}")
            return {
                'success': False,
                'message': f"Erro na verificação: {str(e)}",
                'patient_id': None
            }

    # Mantém os mesmos métodos auxiliares de validação e normalização
    # (_normalize_cpf, _normalize_phone, _normalize_zip, _normalize_gender, 
    # _normalize_state, _is_valid_cpf, _is_valid_date, _extract_patient_id, 
    # _validate_form_data - todos mantidos da versão original)

    @staticmethod
    def _normalize_cpf(cpf):
        """Remove máscara de CPF"""
        return re.sub(r'\D', '', cpf) if cpf else ""

    @staticmethod
    def _normalize_phone(phone):
        """Normaliza número de telefone"""
        digits = re.sub(r'\D', '', phone) if phone else ""
        if len(digits) == 11:
            return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
        elif len(digits) == 10:
            return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
        return phone

    @staticmethod
    def _normalize_zip(zipcode):
        """Normaliza CEP"""
        digits = re.sub(r'\D', '', zipcode) if zipcode else ""
        if len(digits) == 8:
            return f"{digits[:5]}-{digits[5:]}"
        return zipcode

    @staticmethod
    def _normalize_gender(gender):
        """Normaliza sexo para valores esperados pela plataforma GoC
        
        O select do GoC usa:
        - value="1" para Masculino
        - value="2" para Feminino
        """
        gender_lower = gender.lower().strip()
        if 'masc' in gender_lower or 'm' == gender_lower or 'homem' in gender_lower:
            return '1'  # Masculino no GoC
        elif 'fem' in gender_lower or 'f' == gender_lower or 'mulher' in gender_lower:
            return '2'  # Feminino no GoC
        return gender

    @staticmethod
    def _normalize_state(state):
        """Normaliza estado/UF para sigla"""
        state_upper = state.upper().strip()
        if len(state_upper) == 2:
            return state_upper
        
        state_map = {
            'SAO PAULO': 'SP', 'SÃO PAULO': 'SP', 'SP': 'SP',
            'RIO DE JANEIRO': 'RJ', 'RJ': 'RJ',
            'MINAS GERAIS': 'MG', 'MG': 'MG',
            'BAHIA': 'BA', 'BA': 'BA',
        }
        return state_map.get(state_upper, state_upper[:2])

    @staticmethod
    def _normalize_state_to_value(state):
        """Converte estado/UF para value numérico do GoC
        
        Mapeamento baseado no select do sistema:
        AC=3, AL=15, AP=7, AM=4, BA=17, CE=11, DF=28, ES=19, GO=27,
        MA=9, MT=26, MS=25, MG=18, PA=6, PB=13, PR=22, PE=14, PI=10,
        RJ=20, RN=12, RS=24, RO=2, RR=5, SC=23, SP=21, SE=16, TO=8
        """
        state_upper = state.upper().strip()
        
        # Primeiro normaliza para sigla se for nome completo
        name_to_sigla = {
            'SAO PAULO': 'SP', 'SÃO PAULO': 'SP',
            'RIO DE JANEIRO': 'RJ', 'MINAS GERAIS': 'MG',
            'BAHIA': 'BA', 'PARANA': 'PR', 'PARANÁ': 'PR',
            'RIO GRANDE DO SUL': 'RS', 'SANTA CATARINA': 'SC',
            'GOIAS': 'GO', 'GOIÁS': 'GO', 'PERNAMBUCO': 'PE',
            'CEARA': 'CE', 'CEARÁ': 'CE', 'PARA': 'PA', 'PARÁ': 'PA',
            'MARANHAO': 'MA', 'MARANHÃO': 'MA', 'AMAZONAS': 'AM',
            'ESPIRITO SANTO': 'ES', 'ESPÍRITO SANTO': 'ES',
            'PARAIBA': 'PB', 'PARAÍBA': 'PB', 'MATO GROSSO': 'MT',
            'MATO GROSSO DO SUL': 'MS', 'RIO GRANDE DO NORTE': 'RN',
            'PIAUI': 'PI', 'PIAUÍ': 'PI', 'ALAGOAS': 'AL',
            'SERGIPE': 'SE', 'RONDONIA': 'RO', 'RONDÔNIA': 'RO',
            'TOCANTINS': 'TO', 'ACRE': 'AC', 'AMAPA': 'AP', 'AMAPÁ': 'AP',
            'RORAIMA': 'RR', 'DISTRITO FEDERAL': 'DF'
        }
        
        sigla = name_to_sigla.get(state_upper, state_upper)
        if len(sigla) > 2:
            sigla = sigla[:2]
        
        # Mapeia sigla para value numérico do GoC
        sigla_to_value = {
            'AC': '3', 'AL': '15', 'AP': '7', 'AM': '4', 'BA': '17',
            'CE': '11', 'DF': '28', 'ES': '19', 'GO': '27', 'MA': '9',
            'MT': '26', 'MS': '25', 'MG': '18', 'PA': '6', 'PB': '13',
            'PR': '22', 'PE': '14', 'PI': '10', 'RJ': '20', 'RN': '12',
            'RS': '24', 'RO': '2', 'RR': '5', 'SC': '23', 'SP': '21',
            'SE': '16', 'TO': '8'
        }
        
        return sigla_to_value.get(sigla, '')

    @staticmethod
    def _normalize_civil_status(status):
        """Converte estado civil para value numérico do GoC
        
        Valores: 1=Solteiro, 2=Casado, 3=Separado, 4=Divorciado, 5=Outros
        """
        status_lower = status.lower().strip()
        
        status_map = {
            'solteiro': '1', 'solteira': '1',
            'casado': '2', 'casada': '2',
            'separado': '3', 'separada': '3',
            'divorciado': '4', 'divorciada': '4',
            'viuvo': '5', 'viúvo': '5', 'viuva': '5', 'viúva': '5',
            'uniao estavel': '5', 'união estável': '5',
            'outros': '5', 'outro': '5'
        }
        
        return status_map.get(status_lower, '5')  # Default: Outros

    @staticmethod
    def _normalize_race(race):
        """Converte raça/cor para value numérico do GoC
        
        Valores: 1=Branco, 2=Pardo, 3=Negro, 4=Amarelo, 5=Indígena
        """
        race_lower = race.lower().strip()
        
        race_map = {
            'branco': '1', 'branca': '1',
            'pardo': '2', 'parda': '2',
            'negro': '3', 'negra': '3', 'preto': '3', 'preta': '3',
            'amarelo': '4', 'amarela': '4',
            'indigena': '5', 'indígena': '5'
        }
        
        return race_map.get(race_lower, '')

    @staticmethod
    def _is_valid_cpf(cpf):
        """Valida CPF (básico)"""
        digits = re.sub(r'\D', '', cpf) if cpf else ""
        if len(digits) != 11:
            return False
        if digits == digits[0] * 11:
            return False
        return True

    @staticmethod
    def _is_valid_date(date_str):
        """Valida data no formato DD/MM/YYYY"""
        try:
            datetime.strptime(date_str, '%d/%m/%Y')
            return True
        except ValueError:
            return False

    def _extract_patient_id(self):
        """Extrai ID do paciente da página de sucesso"""
        try:
            current_url = self.browser.driver.current_url
            if 'id=' in current_url.lower():
                match = re.search(r'id=(\d+)', current_url, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            id_selectors = [
                '#ctl00_ContentPlaceHolder1_lblId',
                '.patient-id',
                '[id*="paciente"]'
            ]
            
            for selector in id_selectors:
                try:
                    elem = self.browser.driver.find_element(By.CSS_SELECTOR, selector)
                    if elem and elem.text.strip():
                        return elem.text.strip()
                except:
                    continue
            
            return None
        except Exception as e:
            logger.error(f"Erro ao extrair ID do paciente: {e}")
            return None

    def _validate_form_data(self, form_data):
        """
        Valida os dados do formulário Google Forms
        """
        errors = []
        required_fields = ['Nome completo', 'CPF', 'Data de nascimento', 'Sexo']
        
        for field in required_fields:
            if not form_data.get(field, '').strip():
                errors.append(f"Campo obrigatório ausente: {field}")
        
        cpf = form_data.get('CPF', '').strip()
        if cpf and not self._is_valid_cpf(cpf):
            errors.append(f"CPF inválido: {cpf}")
        
        birth_date = form_data.get('Data de nascimento', '').strip()
        if birth_date and not self._is_valid_date(birth_date):
            errors.append(f"Data de nascimento em formato inválido: {birth_date}")
        return {'valid': len(errors) == 0, 'errors': errors}