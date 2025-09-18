# whatsapp_disparos.py
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import urllib.parse

def criar_mensagem(nome, template):
    """Substitui {nome} na mensagem."""
    return template.format(nome=nome)

def enviar_mensagem(numero, mensagem, driver):
    """Envia mensagem para um número via WhatsApp Web."""
    numero = str(numero).replace("+", "").replace(" ", "").replace("-", "")
    msg_enc = urllib.parse.quote(mensagem)
    url = f"https://web.whatsapp.com/send?phone={numero}&text={msg_enc}"
    driver.get(url)
    time.sleep(8)  # espera WhatsApp Web carregar
    try:
        # botão enviar
        btn = driver.find_element(By.XPATH, '//span[@data-icon="send"]')
        btn.click()
        time.sleep(2)
    except:
        print(f"Erro ao enviar para {numero}")

def enviar_whatsapp(df, mensagem_padrao):
    """Função principal para enviar mensagens."""
    # filtra contatos válidos
    if "Telefone" not in df.columns:
        print("Coluna 'Telefone' não encontrada no DataFrame.")
        return
    df_validos = df[df["Telefone"].notna()]
    if df_validos.empty:
        print("Nenhum telefone válido para envio.")
        return

    # inicia navegador
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    driver.get("https://web.whatsapp.com")
    print("🔹 Abra o WhatsApp Web e escaneie o QR Code")
    input("Pressione Enter quando estiver conectado no WhatsApp Web...")

    for _, row in df_validos.iterrows():
        nome = row["Nome"] if "Nome" in row and pd.notna(row["Nome"]) else ""
        numero = row["Telefone"]
        mensagem = criar_mensagem(nome, mensagem_padrao)
        enviar_mensagem(numero, mensagem, driver)
        print(f"✅ Mensagem enviada para {numero} — {nome}")

    print("✅ Todas as mensagens foram enviadas!")
    driver.quit()
