# whatsapp_sender.py (refatorado para QR Code + envio automático)
import pandas as pd
import streamlit as st
import pywhatkit as pwk
import time

def whatsapp_ui(df):
    st.subheader("📲 Disparo de mensagens WhatsApp")

    # Verifica se existe coluna 'Telefone'
    if 'Telefone' not in df.columns:
        st.error("O DataFrame não contém a coluna 'Telefone'.")
        return
    
    df_phones = df[df["Telefone"].notna()].copy()
    if df_phones.empty:
        st.info("Nenhum cliente com telefone disponível para envio.")
        return

    mensagem_padrao = st.text_area(
        "Mensagem a ser enviada (use {nome} para personalizar)",
        value="Olá {nome}, obrigado pela sua compra! 🎉",
        height=120
    )

    if st.button("📡 Conectar WhatsApp e enviar mensagens"):
        st.info("O WhatsApp Web vai abrir no navegador. Escaneie o QR Code com seu celular para autenticar.")

        progress_text = st.empty()
        total = len(df_phones)

        for idx, row in df_phones.iterrows():
            numero = str(row["Telefone"]).replace("+", "").replace(" ", "").replace("-", "")
            mensagem = mensagem_padrao.format(nome=row.get("Nome", "Cliente"))

            try:
                # envia mensagem instantaneamente
                pwk.sendwhatmsg_instantly(f"+{numero}", mensagem, wait_time=10, tab_close=True)
                progress_text.text(f"✅ Mensagem enviada para {row.get('Nome', numero)} ({idx+1}/{total})")
                time.sleep(1)  # intervalo para evitar bloqueios

            except Exception as e:
                progress_text.text(f"❌ Erro ao enviar para {row.get('Nome', numero)}: {e}")
                time.sleep(1)

        st.success("📩 Envio de mensagens concluído!")
        st.balloons()
