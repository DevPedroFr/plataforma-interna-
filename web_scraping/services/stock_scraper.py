# web_scraping/services/stock_scraper.py
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_scraper import BaseScraper
from core.models import Vaccine

class StockScraper(BaseScraper):
    def __init__(self, browser_manager):
        super().__init__(browser_manager)
        self.stock_url = "https://aruja.gocfranquias.com.br/Cadastro/Vacinas.aspx"
    
    def scrape_stock_data(self):
        """Extrai dados de estoque da página de vacinas"""
        if not self.ensure_login():
            return []
        
        print("🔄 Navegando para página de estoque...")
        self.browser.driver.get(self.stock_url)
        
        try:
            WebDriverWait(self.browser.driver, 15).until(
                EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_GridView1"))
            )
        except:
            print("❌ Tabela de estoque não encontrada")
            return []
        
        stock_data = []

        try:
            # The site uses an ASP.NET GridView with async postbacks to change pages.
            # We'll iterate pages by triggering the postback with __doPostBack and
            # stop when no rows are returned (user requested this behavior).
            page = 1
            max_pages = 50  # safety limit

            # Track seen rows to detect when pagination stops returning new data.
            seen_keys = set()
            consecutive_no_new = 0

            while page <= max_pages:
                # Wait for table rows to be present (or timeout)
                try:
                    WebDriverWait(self.browser.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#ctl00_ContentPlaceHolder1_GridView1 tr"))
                    )
                except:
                    # If table never appears, break
                    print("❌ Tabela de estoque não carregou na página", page)
                    break

                # Encontra todas as linhas da tabela (rows may include header/footer)
                rows = self.browser.driver.find_elements(
                    By.CSS_SELECTOR,
                    "#ctl00_ContentPlaceHolder1_GridView1 tr.gridview-row, #ctl00_ContentPlaceHolder1_GridView1 tr.gridview-alt-row"
                )

                print(f"📊 Página {page}: encontradas {len(rows)} linhas na tabela")

                if not rows:
                    # Stop when no data is returned, per your request
                    print("ℹ️ Nenhum dado encontrado — finalizando paginação")
                    break

                for i, row in enumerate(rows):
                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 7:
                            # Extrai nome do produto (primeira coluna com span)
                            name_element = None
                            try:
                                name_element = cells[0].find_element(By.TAG_NAME, "span")
                            except:
                                pass
                            vaccine_name = name_element.text.strip() if name_element else cells[0].text.strip() or "Nome não encontrado"

                            # Extrai laboratório (segunda coluna)
                            lab_text = cells[1].text.strip()

                            # Extrai preço de compra (terceira coluna)
                            purchase_price = self._parse_price(cells[2].text)
                            
                            # Extrai preço de venda (quarta coluna, geralmente em span)
                            sale_price = 0.0
                            try:
                                sale_price_element = cells[3].find_element(By.TAG_NAME, "span")
                                sale_price = self._parse_price(sale_price_element.text) if sale_price_element else 0.0
                            except:
                                sale_price = self._parse_price(cells[3].text)

                            # Extrai estoque atual (quinta coluna) - texto direto da célula
                            current_stock_text = cells[4].text.strip()
                            current_stock = self._parse_quantity(current_stock_text)
                            print(f"📦 Estoque atual bruto: '{current_stock_text}' -> {current_stock}")

                            # Extrai estoque disponível (sexta coluna, geralmente em span)
                            available_stock = current_stock
                            try:
                                available_stock_element = cells[5].find_element(By.TAG_NAME, "span")
                                available_stock_text = available_stock_element.text.strip()
                                available_stock = self._parse_quantity(available_stock_text)
                                print(f"📦 Estoque disponível bruto: '{available_stock_text}' -> {available_stock}")
                            except:
                                available_stock_text = cells[5].text.strip()
                                available_stock = self._parse_quantity(available_stock_text)
                                print(f"📦 Estoque disponível bruto (sem span): '{available_stock_text}' -> {available_stock}")

                            # Extrai estoque mínimo (sétima coluna, geralmente em span)
                            min_stock = 0
                            try:
                                min_stock_element = cells[6].find_element(By.TAG_NAME, "span")
                                min_stock_text = min_stock_element.text.strip()
                                min_stock = self._parse_quantity(min_stock_text)
                                print(f"📦 Estoque mínimo bruto: '{min_stock_text}' -> {min_stock}")
                            except:
                                min_stock_text = cells[6].text.strip()
                                min_stock = self._parse_quantity(min_stock_text)
                                print(f"📦 Estoque mínimo bruto (sem span): '{min_stock_text}' -> {min_stock}")

                            vaccine_data = {
                                'name': vaccine_name,
                                'laboratory': lab_text,
                                'purchase_price': purchase_price,
                                'sale_price': sale_price,
                                'current_stock': current_stock,
                                'available_stock': available_stock,
                                'min_stock': min_stock,
                            }

                            # Build a stable key for detection (name + lab + current_stock)
                            key = f"{vaccine_data['name']}|{vaccine_data['laboratory']}|{vaccine_data['current_stock']}"
                            if key not in seen_keys:
                                seen_keys.add(key)
                                stock_data.append(vaccine_data)
                                print(f"✅ [{len(stock_data)}] {vaccine_data['name'][:50]}... - Estoque: {vaccine_data['current_stock']}")
                            else:
                                # Duplicate row (already seen on previous pages)
                                print(f"↩️ Linha já vista: {vaccine_data['name'][:50]}")

                    except Exception as e:
                        print(f"❌ Erro ao processar linha {i+1} na página {page}: {e}")
                        continue

                # If after processing this page we didn't add any new keys, increment consecutive_no_new
                # We'll stop when we see 2 consecutive pages without new rows (configurable)
                # Capture a snapshot of seen count to compare after navigation
                seen_before = len(seen_keys)

                # Try to advance to next page by triggering the GridView postback
                page += 1

                # Build the postback argument Page$n
                postback_arg = f"Page${page}"

                try:
                    # Use __doPostBack to request the next page. If __doPostBack is not
                    # available this will raise — in that case try to click a pager link.
                    script = "if (typeof __doPostBack === 'function') { __doPostBack(arguments[0], arguments[1]); }"
                    self.browser.driver.execute_script(script, 'ctl00$ContentPlaceHolder1$GridView1', postback_arg)

                    # Small wait to allow AJAX update; then wait for new rows to load
                    time.sleep(1)
                    WebDriverWait(self.browser.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#ctl00_ContentPlaceHolder1_GridView1 tr"))
                    )
                except Exception as e:
                    # Fallback: try to find a pager link and click it
                    try:
                        pager_links = self.browser.driver.find_elements(By.CSS_SELECTOR, "#ctl00_ContentPlaceHolder1_GridView1 a")
                        clicked = False
                        for a in pager_links:
                            try:
                                onclick = a.get_attribute('href') or a.get_attribute('onclick') or ''
                                if f"Page${page}" in onclick or f"Page%24{page}" in onclick or str(page) == a.text.strip():
                                    a.click()
                                    clicked = True
                                    break
                            except:
                                continue

                        if not clicked:
                            print("ℹ️ Não foi possível navegar para próxima página — finalizando")
                            break

                        # wait for the grid to refresh
                        time.sleep(1)
                        WebDriverWait(self.browser.driver, 15).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "#ctl00_ContentPlaceHolder1_GridView1 tr"))
                        )
                    except Exception:
                        print("ℹ️ Não foi possível avançar paginação — finalizando")
                        break

                # After navigation and waiting, compute whether new rows were discovered
                seen_after = len(seen_keys)
                if seen_after > seen_before:
                    consecutive_no_new = 0
                else:
                    consecutive_no_new += 1

                # If we had two consecutive pages with no new rows, assume we've reached the end
                if consecutive_no_new >= 2:
                    print("ℹ️ Duas páginas consecutivas sem novos registros — finalizando paginação")
                    break

            # end while

        except Exception as e:
            print(f"❌ Erro geral ao extrair dados: {e}")

        return stock_data
    
    def _parse_price(self, price_text):
        """Converte texto de preço para float"""
        try:
            # Remove "R$" e espaços, trata vírgula como separador decimal
            cleaned = re.sub(r'[^\d,]', '', price_text.replace('R$', '').strip())
            cleaned = cleaned.replace(',', '.')
            return float(cleaned) if cleaned else 0.0
        except Exception as e:
            print(f"❌ Erro ao converter preço '{price_text}': {e}")
            return 0.0
    
    def _parse_quantity(self, quantity_text):
        """Converte texto de quantidade para inteiro"""
        try:
            # Limpa o texto: remove espaços e caracteres especiais
            quantity_text = quantity_text.strip()
            
            # Se estiver vazio, retorna 0
            if not quantity_text:
                return 0
            
            # Remove todos os caracteres não numéricos (mantém apenas dígitos)
            cleaned = re.sub(r'[^\d]', '', quantity_text)
            
            # Converte para inteiro
            result = int(cleaned) if cleaned else 0
            return result
        except Exception as e:
            print(f"❌ Erro ao converter quantidade '{quantity_text}': {e}")
            return 0
    
    def sync_stock_to_database(self):
        """Sincroniza dados de estoque com o banco de dados"""
        print("🔄 Iniciando sincronização de estoque...")
        stock_data = self.scrape_stock_data()
        
        if not stock_data:
            return {
                'status': 'error',
                'message': 'Nenhum dado foi extraído',
                'total_scraped': 0,
                'created': 0,
                'updated': 0
            }
        
        updated_count = 0
        created_count = 0
        errors = []
        
        for vaccine_data in stock_data:
            try:
                # Busca vacina pelo nome ou cria uma nova
                vaccine, created = Vaccine.objects.get_or_create(
                    name=vaccine_data['name']
                )
                
                # SEMPRE atualiza os campos de estoque e preço, independente se foi criada ou não
                vaccine.laboratory = vaccine_data.get('laboratory', vaccine.laboratory)
                vaccine.current_stock = vaccine_data.get('current_stock', vaccine.current_stock)
                vaccine.available_stock = vaccine_data.get('available_stock', vaccine.available_stock)
                vaccine.min_stock = vaccine_data.get('min_stock', vaccine.min_stock)
                vaccine.minimum_stock = vaccine_data.get('min_stock', vaccine.minimum_stock)  # Mantém sincronizado
                
                # Atualiza preços se fornecidos
                if vaccine_data.get('purchase_price'):
                    vaccine.purchase_price = vaccine_data['purchase_price']
                if vaccine_data.get('sale_price'):
                    vaccine.sale_price = vaccine_data['sale_price']
                
                vaccine.save()
                
                if created:
                    created_count += 1
                    print(f"✅ Vacina criada: {vaccine.name} - Estoque: {vaccine.current_stock}")
                else:
                    updated_count += 1
                    print(f"✅ Vacina atualizada: {vaccine.name} - Estoque: {vaccine.current_stock}")
                    
            except Exception as e:
                error_msg = f"Erro ao salvar {vaccine_data['name']}: {e}"
                errors.append(error_msg)
                print(f"❌ {error_msg}")
        
        result = {
            'status': 'success',
            'total_scraped': len(stock_data),
            'created': created_count,
            'updated': updated_count,
            'errors': errors,
            'message': f"Sincronização concluída: {created_count} criadas, {updated_count} atualizadas"
        }
        
        print(f"✅ {result['message']}")
        return result