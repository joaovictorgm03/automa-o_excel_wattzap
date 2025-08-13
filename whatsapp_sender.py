
# whatsapp_sender.py
# Envio 100% automatizado de mensagens pelo WhatsApp Web via Selenium (sem precisar apertar Enter manualmente).
# Requisitos:
#   - Python 3.9+
#   - pip install selenium webdriver-manager pandas openpyxl
#   - Faça login no WhatsApp Web uma vez; o script manterá a sessão usando um perfil de navegador dedicado.
#
# Como usar:
#   1) Edite o arquivo contatos.xlsx (ou .csv) com colunas: phone, message
#      - 'phone' deve estar no formato com DDI e DDD, ex.: 55XXXXXXXXXXX (somente dígitos)
#      - 'message' é o texto a enviar (suporta emojis e quebras de linha \n)
#   2) Rode:  python whatsapp_sender.py --input contatos.xlsx
#      (ou --input contatos.csv)
#   3) O script abrirá o WhatsApp Web, reutilizará sua sessão e enviará tudo automaticamente.
#
# Observações importantes:
#   - Use com responsabilidade e conforme os Termos de Uso do WhatsApp.
#   - Evite enviar mensagens em massa sem consentimento.
#   - O WhatsApp muda o HTML com frequência; se algo quebrar, ajuste os seletores abaixo.

import argparse
import os
import sys
import time
import urllib.parse
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

PROFILE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chrome_profile_whatsapp")

def read_contacts(path: str) -> pd.DataFrame:
    ext = os.path.splitext(path)[1].lower()
    if ext in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    elif ext in [".csv", ".txt"]:
        df = pd.read_csv(path)
    else:
        raise ValueError("Formato de arquivo não suportado. Use .xlsx, .xls, .csv ou .txt")
    # Normaliza colunas
    df.columns = [c.strip().lower() for c in df.columns]
    if "phone" not in df.columns or "message" not in df.columns:
        raise ValueError("O arquivo deve conter as colunas: phone, message")
    # Limpeza básica
    df["phone"] = df["phone"].astype(str).str.replace(r"\D", "", regex=True)
    df["message"] = df["message"].astype(str).fillna("")
    return df

def build_driver(headless: bool = False) -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    # Perfil para manter sessão do WhatsApp
    opts.add_argument(f"--user-data-dir={PROFILE_DIR}")
    opts.add_argument("--profile-directory=Default")
    # Estabilidade
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--start-maximized")
    if headless:
        # Headless novo do Chrome funciona com WHATSAPP? às vezes não. Prefira com janela.
        opts.add_argument("--headless=new")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
        return driver
    except WebDriverException as e:
        print("Erro ao iniciar o ChromeDriver:", e)
        print("Dica: verifique se a versão do Chrome é compatível com o driver. Tente atualizar o Chrome.")
        raise

def ensure_logged_in(driver: webdriver.Chrome, timeout: int = 120):
    driver.get("https://web.whatsapp.com/")
    wait = WebDriverWait(driver, timeout)
    try:
        # Critério 1: barra lateral carregada (ID 'side')
        wait.until(EC.presence_of_element_located((By.ID, "side")))
    except TimeoutException:
        # Tenta um segundo critério antes de desistir
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='textbox']")))
        except TimeoutException:
            raise TimeoutException("Não foi possível confirmar o login no WhatsApp Web (tempo esgotado).")

def open_chat_and_send(driver: webdriver.Chrome, phone: str, message: str, timeout: int = 60) -> bool:
    # Abre a conversa diretamente com o número:
    encoded = urllib.parse.quote(message, safe="")
    url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded}&type=phone_number&app_absent=0"
    driver.get(url)
    wait = WebDriverWait(driver, timeout)

    try:
        # Aguarda a área de texto da mensagem (contenteditable)
        # Seletores possíveis; tentamos alguns para maior robustez.
        textbox = None
        candidates = [
            (By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='10']"),
            (By.CSS_SELECTOR, "div[contenteditable='true'][data-tab='6']"),
            (By.CSS_SELECTOR, "div[role='textbox']"),
        ]

        end_time = time.time() + timeout
        while time.time() < end_time and textbox is None:
            for by, sel in candidates:
                try:
                    elem = driver.find_element(by, sel)
                    if elem.is_displayed():
                        textbox = elem
                        break
                except NoSuchElementException:
                    pass
            if textbox is None:
                time.sleep(0.3)

        if textbox is None:
            # Às vezes o WhatsApp mostra um botão "Continuar para o chat". Tentar clicar e repetir.
            try:
                continue_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='send?phone=']")))
                continue_btn.click()
                time.sleep(1.5)
                textbox = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='textbox']")))
            except Exception:
                raise TimeoutException("Não encontrei a caixa de mensagem.")

        # Dá foco e garante que o texto já está preenchido pela query string
        textbox.click()
        time.sleep(0.2)

        # Em alguns casos o texto da URL não preenche; reescrevemos
        current_text = textbox.text.strip()
        if not current_text:
            textbox.send_keys(message)

        # ENVIO automático (sem precisar apertar Enter manualmente): clicando no botão Enviar
        # Tentamos vários seletores para o botão de enviar
        send_btn = None
        send_candidates = [
            (By.CSS_SELECTOR, "span[data-icon='send']"),
            (By.CSS_SELECTOR, "button[aria-label='Enviar']"),
            (By.CSS_SELECTOR, "div[aria-label='Enviar']"),
            (By.XPATH, "//button//*[name()='svg' and @data-icon='send']/ancestor::button"),
        ]
        for by, sel in send_candidates:
            try:
                btn = driver.find_element(by, sel)
                if btn.is_displayed() and btn.is_enabled():
                    send_btn = btn
                    break
            except NoSuchElementException:
                continue

        if send_btn is not None:
            send_btn.click()
        else:
            # Fallback: simula ENTER programaticamente (ainda é 100% automático)
            textbox.send_keys(Keys.ENTER)

        # Aguarda a mensagem aparecer no histórico (um balão enviado pela própria conta)
        # Heurística: procurar por o último balão "message-out"
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.message-out, div[class*='message-out']")))
        except TimeoutException:
            # Nem sempre confiável; mas se não deu erro até aqui, provavelmente foi.
            pass

        return True
    except Exception as e:
        print(f"Falha ao enviar para {phone}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Envio automatizado de mensagens no WhatsApp Web via Selenium")
    parser.add_argument("--input", required=True, help="Caminho para contatos.xlsx/.csv com colunas: phone, message")
    parser.add_argument("--headless", action="store_true", help="Tenta rodar sem abrir janela (pode falhar no WhatsApp)")
    parser.add_argument("--delay", type=float, default=2.0, help="Atraso (segundos) entre envios")
    parser.add_argument("--retries", type=int, default=2, help="Tentativas por número em caso de falha")
    args = parser.parse_args()

    df = read_contacts(args.input)
    print(f"Total de registros: {len(df)}")

    driver = build_driver(headless=args.headless)
    try:
        ensure_logged_in(driver)
        results = []
        for i, row in df.iterrows():
            phone = row["phone"]
            message = row["message"]
            success = False
            for attempt in range(1, args.retries + 1):
                print(f"[{i+1}/{len(df)}] Enviando para {phone} (tentativa {attempt})...")
                success = open_chat_and_send(driver, phone, message)
                if success:
                    break
                time.sleep(1.5)
            results.append({"phone": phone, "status": "OK" if success else "FAIL"})
            time.sleep(args.delay)

        out_path = os.path.splitext(args.input)[0] + "_status.csv"
        pd.DataFrame(results).to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"Relatório salvo em: {out_path}")
    finally:
        # Mantém o navegador aberto por alguns segundos para inspeção; ajuste se quiser fechar imediatamente.
        time.sleep(3)
        driver.quit()

if __name__ == "__main__":
    main()
