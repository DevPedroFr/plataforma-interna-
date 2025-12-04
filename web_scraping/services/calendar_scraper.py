# web_scraping/services/calendar_scraper.py
import time
import re
import json
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base_scraper import BaseScraper
from core.models import Appointment, User, Vaccine

class CalendarScraper(BaseScraper):
    def __init__(self, browser_manager):
        if not browser_manager.driver:
            print("🔄 Iniciando navegador para o CalendarScraper...")
            browser_manager.start_browser(headless=True)  # Modo headless
            
        super().__init__(browser_manager)
        self.calendar_url = "https://aruja.gocfranquias.com.br/Cadastro/AgendaAtendimentos.aspx"

    def scrape_calendar(self):
        """Extrai todos os agendamentos do calendário"""
        print("🚀 Iniciando scraping do calendário...")
        
        if not self.browser or not self.browser.driver:
            print("❌ Navegador não está disponível")
            return []
        
        # Login
        if not self.ensure_login():
            print("❌ Falha no login - não é possível acessar o calendário")
            return []

        print("🔄 Navegando para página de agenda...")
        self.browser.driver.get(self.calendar_url)

        # Aguarda o calendário carregar
        try:
            WebDriverWait(self.browser.driver, 20).until(
                EC.presence_of_element_located((By.ID, "DatePicker"))
            )
            print("✅ Calendário carregado com sucesso")
            
        except Exception as e:
            print(f"❌ Erro ao carregar calendário: {e}")
            return []

        # Extrai agendamentos
        appointments = self._extract_appointments_from_script()
        
        print(f"📊 Total de agendamentos extraídos: {len(appointments)}")
        
        # Sincroniza com o banco
        self._sync_appointments_to_db(appointments)
        
        return appointments

    def _extract_appointments_from_script(self):
        """Extrai agendamentos diretamente do script JavaScript"""
        appointments = []
        
        try:
            # Executa JavaScript para obter o objeto cellContents diretamente
            script = """
            if (typeof cellContents !== 'undefined') {
                return JSON.stringify(cellContents);
            } else {
                return null;
            }
            """
            
            result = self.browser.driver.execute_script(script)
            
            if result:
                print("✅ cellContents encontrado via JavaScript")
                appointments = self._parse_cell_contents_json(result)
            else:
                print("❌ cellContents não encontrado via JavaScript, tentando parse do HTML...")
                appointments = self._extract_from_html()
                
        except Exception as e:
            print(f"❌ Erro ao executar script: {e}")
            appointments = self._extract_from_html()
            
        return appointments

    def _parse_cell_contents_json(self, cell_contents_json):
        """Parse do objeto cellContents como JSON"""
        appointments = []
        
        try:
            cell_contents = json.loads(cell_contents_json)
            print(f"📅 Dias com agendamentos: {len(cell_contents)}")
            
            for date_str, html_content in cell_contents.items():
                try:
                    day_appointments = self._parse_appointments_for_date(date_str, html_content)
                    appointments.extend(day_appointments)
                    print(f"  📋 {date_str}: {len(day_appointments)} agendamentos")
                    
                except Exception as e:
                    print(f"❌ Erro ao processar data {date_str}: {e}")
                    continue
                    
        except json.JSONDecodeError as e:
            print(f"❌ Erro no parse do JSON: {e}")
            
        return appointments

    def _parse_appointments_for_date(self, date_str, html_content):
        """Extrai todos os agendamentos de uma data específica"""
        appointments = []
        
        # Encontra todos os blocos de agendamento
        appointment_pattern = r'<div align=left style="[^"]*margin: 1px;[^"]*background-color: #F4511E[^"]*"[^>]*>(.*?)</div>'
        
        matches = re.findall(appointment_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        for i, match in enumerate(matches):
            appointment_data = self._parse_single_appointment(match, date_str, i)
            if appointment_data:
                appointments.append(appointment_data)
                
        return appointments

    def _parse_single_appointment(self, appointment_html, date_str, index):
        """Parse de um agendamento individual"""
        try:
            # Encontra conteúdo dentro das tags <font>
            font_pattern = r'<font[^>]*>(.*?)</font>'
            font_matches = re.findall(font_pattern, appointment_html, re.DOTALL)
            
            if not font_matches:
                return None
                
            font_content = font_matches[0]
            
            # Divide o conteúdo em linhas (considerando <BR>)
            lines = [line.strip() for line in re.split(r'<BR\s*/?>', font_content) if line.strip()]
            
            if not lines:
                return None
            
            # Parse das informações
            appointment_data = {
                'date': date_str,
                'lines': lines
            }
            
            # Primeira linha geralmente tem horário e nome
            first_line = lines[0]
            
            # Extrai horário (padrão: HH:MM)
            time_match = re.search(r'(\d{1,2}:\d{2})', first_line)
            if time_match:
                appointment_data['time'] = time_match.group(1)
                # Remove o horário para obter o nome
                name_part = first_line.replace(time_match.group(1), '').strip()
                appointment_data['patient_name'] = name_part
            else:
                appointment_data['time'] = "09:00"  # Horário padrão
                appointment_data['patient_name'] = first_line
            
            # Segunda linha geralmente tem informações da vacina
            if len(lines) > 1:
                appointment_data['vaccine_info'] = lines[1]
            else:
                appointment_data['vaccine_info'] = "Vacina não especificada"
            
            # Linhas restantes são observações
            if len(lines) > 2:
                appointment_data['observations'] = ' | '.join(lines[2:])
            else:
                appointment_data['observations'] = ""
            
            # Extrai telefone se disponível
            phone_match = re.search(r'(\d{2}\s*\d{4,5}-\d{4})', appointment_html)
            if phone_match:
                appointment_data['phone'] = phone_match.group(1)
            else:
                appointment_data['phone'] = "Não informado"
            
            return appointment_data
            
        except Exception as e:
            print(f"❌ Erro ao parsear agendamento {index} para {date_str}: {e}")
            return None

    def _extract_from_html(self):
        """Método alternativo: extrai do HTML da página"""
        print("🔄 Extraindo agendamentos do HTML...")
        appointments = []
        
        html = self.browser.driver.page_source
        
        # Procura pelo script que contém cellContents
        script_pattern = r'var\s+cellContents\s*=\s*(\{.*?\});'
        script_match = re.search(script_pattern, html, re.DOTALL)
        
        if script_match:
            print("✅ cellContents encontrado no HTML")
            try:
                # Limpa e converte para JSON
                cell_contents_str = script_match.group(1)
                
                # Processa o JavaScript para JSON
                cell_contents_str = self._clean_js_object(cell_contents_str)
                
                appointments = self._parse_cell_contents_json(cell_contents_str)
                
            except Exception as e:
                print(f"❌ Erro ao processar cellContents do HTML: {e}")
        
        return appointments

    def _clean_js_object(self, js_obj_str):
        """Converte objeto JavaScript para JSON válido"""
        try:
            # Substitui aspas simples por duplas
            js_obj_str = js_obj_str.replace("'", '"')
            
            # Remove vírgulas finais
            js_obj_str = re.sub(r',\s*}', '}', js_obj_str)
            js_obj_str = re.sub(r',\s*]', ']', js_obj_str)
            
            # Escapa quebras de linha
            js_obj_str = js_obj_str.replace('\n', '\\n')
            js_obj_str = js_obj_str.replace('\r', '\\r')
            
            return js_obj_str
            
        except Exception as e:
            print(f"❌ Erro ao limpar objeto JS: {e}")
            return js_obj_str

    def _sync_appointments_to_db(self, appointments):
        """Insere os agendamentos no banco de dados"""
        created_count = 0
        updated_count = 0
        
        print(f"💾 Sincronizando {len(appointments)} agendamentos com o banco...")
        
        for appt in appointments:
            try:
                # Converte data do formato DD-MM-YYYY
                appt_date = datetime.strptime(appt['date'], '%d-%m-%Y').date()
                
                # Busca ou cria usuário
                user, user_created = User.objects.get_or_create(
                    name=appt['patient_name'],
                    defaults={
                        'phone': appt.get('phone', 'Não informado'),
                        'via_chatbot': False,
                        'synced': True
                    }
                )
                
                # Atualiza telefone se necessário
                if not user_created and appt.get('phone') != 'Não informado':
                    user.phone = appt['phone']
                    user.save()
                
                # Busca ou cria vacina
                vaccine = None
                vaccine_info = appt.get('vaccine_info', '')
                if vaccine_info and vaccine_info != 'Vacina não especificada':
                    # Limpa o nome da vacina
                    vaccine_name = vaccine_info.strip()
                    if len(vaccine_name) > 200:
                        vaccine_name = vaccine_name[:200]
                    
                    vaccine = Vaccine.objects.filter(name__icontains=vaccine_name).first()
                    if not vaccine:
                        vaccine = Vaccine.objects.create(
                            name=vaccine_name,
                            current_stock=0,
                            minimum_stock=10
                        )
                
                # Verifica se agendamento já existe
                existing = Appointment.objects.filter(
                    user=user,
                    appointment_date=appt_date,
                    appointment_time=appt.get('time', '09:00')
                ).first()
                
                if existing:
                    # Atualiza dados existentes
                    existing.vaccine = vaccine
                    existing.observations = appt.get('observations', '')
                    existing.status = 'scheduled'
                    existing.save()
                    updated_count += 1
                else:
                    # Cria novo agendamento - SEM appointment_type
                    Appointment.objects.create(
                        user=user,
                        vaccine=vaccine,
                        appointment_date=appt_date,
                        appointment_time=appt.get('time', '09:00'),
                        dose='',
                        status='scheduled',
                        via_chatbot=False,
                        observations=appt.get('observations', '')
                    )
                    created_count += 1
                    
            except Exception as e:
                print(f"❌ Erro ao sincronizar agendamento {appt.get('patient_name', 'N/A')}: {e}")
                continue

        print(f"📊 Sincronização concluída: {created_count} novos, {updated_count} atualizados")

    def get_appointment_statistics(self):
        """Retorna estatísticas dos agendamentos"""
        appointments = self.scrape_calendar()
        
        stats = {
            'total': len(appointments),
            'by_date': {},
            'by_vaccine': {},
        }
        
        for appt in appointments:
            # Por data
            date = appt['date']
            stats['by_date'][date] = stats['by_date'].get(date, 0) + 1
            
            # Por vacina
            vaccine = appt.get('vaccine_info', 'Não especificada')
            stats['by_vaccine'][vaccine] = stats['by_vaccine'].get(vaccine, 0) + 1
        
        return stats