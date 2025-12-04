# web_scraping/services/users_scraper.py
import time
import re
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_scraper import BaseScraper
from datetime import datetime

class UsersScraper(BaseScraper):
    def __init__(self, browser_manager):
        super().__init__(browser_manager)
        self.users_url = "https://aruja.gocfranquias.com.br/Cadastro/Paciente.aspx"
    
    def scrape_recent_users(self, limit=20):
        """Extrai os últimos usuários cadastrados (limitado a 'limit' registros)"""
        if not self.ensure_login():
            return []
        
        print(f"🔄 Navegando para página de pacientes...")
        self.browser.driver.get(self.users_url)
        
        # Aguarda a tabela carregar
        try:
            WebDriverWait(self.browser.driver, 15).until(
                EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_GridView1"))
            )
        except:
            print("❌ Tabela de usuários não encontrada")
            return []
        
        # Primeiro, ordenar por data de cadastro (mais recentes primeiro)
        try:
            print("🔄 Ordenando por data de cadastro...")
            sort_link = self.browser.driver.find_element(
                By.ID, 
                "ctl00_ContentPlaceHolder1_GridView1_ctl01_lnkDataCadastro"
            )
            sort_link.click()
            
            # Aguarda recarregar
            time.sleep(2)
            WebDriverWait(self.browser.driver, 15).until(
                EC.presence_of_element_located((By.ID, "ctl00_ContentPlaceHolder1_GridView1"))
            )
            
            # Clica novamente para ordenar decrescente (mais recentes primeiro)
            sort_link = self.browser.driver.find_element(
                By.ID, 
                "ctl00_ContentPlaceHolder1_GridView1_ctl01_lnkDataCadastro"
            )
            sort_link.click()
            time.sleep(2)
            
        except Exception as e:
            print(f"⚠️ Não foi possível ordenar por data: {e}")
        
        users_data = []
        page = 1
        max_pages = 10  # safety limit

        seen_keys = set()
        consecutive_no_new = 0

        while len(users_data) < limit and page <= max_pages:
            try:
                # Wait for the grid to load; be permissive about the selector
                WebDriverWait(self.browser.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#ctl00_ContentPlaceHolder1_GridView1"))
                )

                # Collect all data rows (fallback from strict selectors)
                all_rows = self.browser.driver.find_elements(By.CSS_SELECTOR, "#ctl00_ContentPlaceHolder1_GridView1 tr")
                rows = []
                for r in all_rows:
                    try:
                        # treat as data row if it contains at least one td
                        if r.find_elements(By.TAG_NAME, 'td'):
                            rows.append(r)
                    except:
                        continue

                print(f"📊 Página {page}: encontradas {len(rows)} linhas (candidatas)")

                if not rows:
                    print("ℹ️ Nenhuma linha encontrada - finalizando")
                    break

                added_this_page = 0
                for i, row in enumerate(rows):
                    if len(users_data) >= limit:
                        break

                    try:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) < 3:
                            continue

                        # Try multiple ways to extract the expected spans; if missing, fallback to text
                        def _safe_text(cell, selector_list):
                            for sel in selector_list:
                                try:
                                    el = cell.find_element(By.CSS_SELECTOR, sel)
                                    txt = el.text.strip()
                                    if txt:
                                        return txt
                                except:
                                    continue
                            return cell.text.strip()

                        full_name = _safe_text(cells[0], ["span[id*='Label1']", "span"])
                        birth_date = _safe_text(cells[1], ["span[id*='Label2']", "span"])
                        responsible1 = _safe_text(cells[2], ["span[id*='Label3']", "span"]) if len(cells) > 2 else None
                        responsible2 = _safe_text(cells[3], ["span[id*='Label4']", "span"]) if len(cells) > 3 else None
                        register_date = _safe_text(cells[4], ["span[id*='Label5']", "span"]) if len(cells) > 4 else None

                        # Build stable key to avoid duplicates across pages
                        key = f"{full_name}|{register_date}"
                        if key in seen_keys:
                            # already seen
                            continue

                        seen_keys.add(key)
                        users_data.append({
                            'name': full_name,
                            'birth_date': birth_date,
                            'responsible1': responsible1 if responsible1 else None,
                            'responsible2': responsible2 if responsible2 else None,
                            'register_date': register_date,
                        })
                        added_this_page += 1
                        print(f"✅ [{len(users_data)}] {full_name} - Cadastro: {register_date}")

                    except Exception as e:
                        print(f"❌ Erro ao processar linha {i+1}: {e}")
                        continue

                if len(users_data) >= limit:
                    break

                # pagination handling: try __doPostBack to next page, fallback to next button/pager links
                seen_before = len(seen_keys)
                page += 1
                postback_arg = f"Page${page}"

                try:
                    script = "if (typeof __doPostBack === 'function') { __doPostBack(arguments[0], arguments[1]); }"
                    self.browser.driver.execute_script(script, 'ctl00$ContentPlaceHolder1$GridView1', postback_arg)
                    time.sleep(1)
                    WebDriverWait(self.browser.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#ctl00_ContentPlaceHolder1_GridView1 tr"))
                    )
                except Exception:
                    # Try next button image
                    try:
                        next_button = self.browser.driver.find_element(By.CSS_SELECTOR, "input[src*='resultset_next.png']")
                        next_button.click()
                        time.sleep(1.5)
                    except Exception:
                        # Try pager links
                        try:
                            pager_links = self.browser.driver.find_elements(By.CSS_SELECTOR, "#ctl00_ContentPlaceHolder1_GridView1 a")
                            clicked = False
                            for a in pager_links:
                                try:
                                    if str(page) == a.text.strip():
                                        a.click()
                                        clicked = True
                                        break
                                except:
                                    continue
                            if not clicked:
                                print("ℹ️ Não foi possível navegar para próxima página — finalizando")
                                break
                            time.sleep(1)
                        except Exception:
                            print("ℹ️ Não há mais páginas ou não foi possível avançar")
                            break

                # after navigation, check whether new rows were discovered
                seen_after = len(seen_keys)
                if seen_after > seen_before:
                    consecutive_no_new = 0
                else:
                    consecutive_no_new += 1

                if consecutive_no_new >= 2:
                    print("ℹ️ Duas páginas consecutivas sem novos registros — finalizando paginação")
                    break

            except Exception as e:
                print(f"❌ Erro na página {page}: {e}")
                break

        return users_data[:limit]
    
    def _parse_date(self, date_str):
        """Converte string de data DD/MM/YYYY para objeto datetime"""
        try:
            if date_str and date_str.strip():
                return datetime.strptime(date_str.strip(), '%d/%m/%Y').date()
            return None
        except Exception as e:
            print(f"❌ Erro ao converter data '{date_str}': {e}")
            return None
    
    def get_recent_users_for_display(self):
        """
        Retorna dados dos últimos 20 usuários formatados para exibição
        """
        print("🔄 Iniciando busca dos últimos 20 usuários cadastrados...")
        users_data = self.scrape_recent_users(limit=20)
        
        if not users_data:
            return {
                'status': 'error',
                'message': 'Nenhum usuário foi encontrado',
                'users': []
            }
        
        # Formata os dados para exibição
        formatted_users = []
        for user in users_data:
            formatted_users.append({
                'name': user['name'],
                'birth_date': user['birth_date'],
                'responsible1': user['responsible1'],
                'responsible2': user['responsible2'],
                'register_date': user['register_date'],
                'initials': self._get_initials(user['name'])
            })
        
        result = {
            'status': 'success',
            'total': len(formatted_users),
            'users': formatted_users,
            'message': f"{len(formatted_users)} usuários encontrados"
        }
        
        print(f"✅ {result['message']}")
        return result
    
    def _get_initials(self, name):
        """Extrai iniciais do nome para exibição"""
        if not name:
            return "??"
        
        parts = name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        elif len(parts) == 1:
            return parts[0][:2].upper()
        return "??"