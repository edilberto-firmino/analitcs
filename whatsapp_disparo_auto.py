# whatsapp_disparo_auto.py
import pandas as pd
import time
import urllib.parse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ---------- Configurações ----------
CSV_FILE = "clientes_whatsapp.csv"  # coloque o caminho do seu CSV
MENSAGEM_PADRAO = "Olá {nome}, obrigado pela sua compra! 🎉"
TEMPO_CARREGAMENTO = 15  # segundos para o WhatsApp Web carregar

# ---------- Funções ----------
def criar_link_whatsapp(numero, mensagem):
    numero = str(numero).replace("+", "").replace(" ", "").replace("-", "")
    msg_enc = urllib.parse.quote(mensagem)
    return f"https://wa.me/{numero}?text={msg_enc}"

def enviar_mensagens(df):
    # Configura Chrome
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    # Abre WhatsApp Web
    driver.get("https://web.whatsapp.com")
    print("🔹 Escaneie o QR code com seu celular... aguardando carregamento...")
    time.sleep(TEMPO_CARREGAMENTO)  # aguarda você escanear o QR code

    for idx, row in df.iterrows():
        try:
            link = criar_link_whatsapp(row["Telefone"], MENSAGEM_PADRAO.format(nome=row.get("Nome","Cliente")))
            driver.get(link)
            time.sleep(5)  # espera a página carregar

            # Clica no botão de enviar
            send_btn = driver.find_element(By.XPATH, '//button[@data-testid="compose-btn-send"]')
            send_btn.click()
            print(f"✅ Mensagem enviada para {row.get('Nome', row['Telefone'])}")
            time.sleep(3)  # espera entre envios
        except Exception as e:
            print(f"❌ Erro ao enviar para {row.get('Nome', row['Telefone'])}: {e}")

    print("🎯 Todas as mensagens enviadas!")
    driver.quit()

# ---------- Execução ----------
if __name__ == "__main__":
    df = pd.read_csv(CSV_FILE)
    df = df[df["Telefone"].notna()]
    if df.empty:
        print("❌ Nenhum telefone válido no CSV.")
    else:
        enviar_mensagens(df)
