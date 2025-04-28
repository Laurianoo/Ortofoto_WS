from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from logging.handlers import RotatingFileHandler
import logging
import os
import requests
import time

# URL base
url_base = "https://finatec.sibbr.gov.br/"

# Caminho de navegação no menu
caminho_desejado = [
    "Dados", 
    "Lidar", 
    "Edital 53_2022", 
    "PRODUTO 03 - ORTOFOTOS E PLANIMETRIA", 
    "Ortofotos", 
    "RJ", 
    "BLOCO_03_RJ"
]

# Diretório para salvar os arquivos
diretorio_destino = r"Output"
os.makedirs(diretorio_destino, exist_ok=True)

def setup_logging():
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    log_file = os.path.join("logs", "execucao.log") # Diretório dedicado para logs
    # Configurar handlers
    handlers = [
        RotatingFileHandler(
            log_file,
            maxBytes=5*1024*1024,  # 5 MB
            backupCount=3,
            encoding="utf-8"
        ),
        logging.StreamHandler()
    ]
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=handlers
    )
setup_logging()

# Configura e abre o Chrome
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)
driver.get(url_base)

try:
    # Primeiro, navega no menu até chegar na pasta desejada
    for parte in caminho_desejado:
        elemento = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((
                By.XPATH, 
                f"//a[contains(text(), '{parte}')] | //span[contains(text(), '{parte}')]"
            ))
        )
        if elemento.tag_name == "span":
            elemento = elemento.find_element(By.XPATH, "./parent::a")
        ActionChains(driver).move_to_element(elemento).click().perform()
        time.sleep(2)

    # Agora que estamos na pasta BLOCO_03_RJ, faz a paginação
    while True:
        # Coleta os links dos arquivos que começam com "RJ_"
        links = driver.find_elements(
            By.XPATH, 
            "//a[starts-with(./span/text(), 'RJ_')]"
        )
        logging.info(f"[Página atual] Encontrados {len(links)} arquivos começando com 'RJ_'")

        # Baixa cada arquivo encontrado
        for link in links:
            arquivo_url = link.get_attribute("href")
            nome_arquivo = os.path.join(diretorio_destino, arquivo_url.split("/")[-1])
            if os.path.exists(nome_arquivo):
                logging.info(f"Já existe, pulando: {nome_arquivo}")
                continue

            logging.info(f"Baixando: {arquivo_url}")
            resp = requests.get(arquivo_url, stream=True)
            resp.raise_for_status()
            with open(nome_arquivo, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            logging.info(f"Concluído: {nome_arquivo}")

        # Tenta clicar no botão "Next" usando o ID específico
        try:
            next_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "nextPage"))
            )
            logging.info("Indo para a próxima página...")
            next_btn.click()
            time.sleep(3)  # aguarda carregamento
        except TimeoutException:
            logging.info("Não há mais páginas. Processo finalizado.")
            break

except Exception as e:
    logging.error(f"Erro: {e}")

finally:
    driver.quit()
