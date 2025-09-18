# analitic.py (versão robusta de leitura e relatório PDF + WhatsApp)
import re
import unicodedata
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import whatsapp_sender
import whatsapp_disparos
from selenium import webdriver
from io import BytesIO, StringIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

st.set_page_config(layout="wide")
st.title("📊 Análise de Vendas e Bilhetes — Robust")

# ---------- Helpers ----------
def normalize(text: str) -> str:
    if pd.isna(text):
        return ""
    text = str(text)
    text = unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("ASCII")
    return text.lower().strip()

def find_column(columns, candidates):
    norm_cols = [(col, normalize(col)) for col in columns]
    for cand in candidates:
        for orig, norm in norm_cols:
            if cand in norm:
                return orig
    return None

def parse_currency(x):
    if pd.isna(x):
        return np.nan
    s = str(x).strip()
    s = re.sub(r'[^\d,.\-]', '', s)
    if s == '':
        return np.nan
    if '.' in s and ',' in s:
        s = s.replace('.', '').replace(',', '.')
    else:
        if ',' in s and '.' not in s:
            s = s.replace(',', '.')
    try:
        return float(s)
    except:
        s2 = re.sub(r'[^\d.\-]', '', s)
        try:
            return float(s2)
        except:
            return np.nan

def parse_int(x):
    if pd.isna(x):
        return 0
    s = str(x)
    s = re.sub(r'[^\d\-]', '', s)
    if s == '':
        return 0
    try:
        return int(float(s))
    except:
        try:
            return int(re.sub(r'[^\d]', '', s))
        except:
            return 0

# ---------- Upload ----------
uploaded_files = st.file_uploader(
    "Selecione os arquivos CSV (aceita múltiplos):",
    type=["csv"],
    accept_multiple_files=True
)

if not uploaded_files:
    st.info("Carregue um ou mais arquivos CSV para iniciar a análise.")
    st.stop()

st.info(f"Processando {len(uploaded_files)} arquivo(s)...")

dfs = []
for file in uploaded_files:
    try:
        raw = file.read()
        try:
            text = raw.decode("utf-8")
        except:
            text = raw.decode("latin-1", errors="replace")

        try:
            df = pd.read_csv(StringIO(text), sep=None, engine='python', low_memory=False)
        except Exception:
            df = pd.read_csv(StringIO(text), low_memory=False)

        if df.empty:
            st.warning(f"O arquivo {file.name} está vazio — ignorado.")
            continue

        cols = list(df.columns)
        # encontrar colunas relevantes
        data_col = find_column(cols, ["data_pedido", "data", "pedido", "date", "created_at"])
        qtd_col = find_column(cols, ["qtd", "quant", "qtd_bilhetes", "quantidade", "bilhet", "ticket", "qty", "qtde"])
        valor_col = find_column(cols, ["valor", "value", "preco", "price", "amount", "total"])
        email_col = find_column(cols, ["e-mail", "email", "e_mail", "cliente_email", "mail"])
        nome_col = find_column(cols, ["nome", "name", "cliente"])
        ref_col = find_column(cols, ["referencia", "referência", "reference", "ref", "id_transacao"])
        telefone_col = find_column(cols, ["telefone", "celular", "phone", "whatsapp", "contato"])

        missing = []
        if data_col is None: missing.append("Data")
        if qtd_col is None: missing.append("Qtd/Bilhetes")
        if valor_col is None: missing.append("Valor")
        if missing:
            st.warning(f"Arquivo {file.name} ignorado — faltando: {', '.join(missing)}")
            continue

        # montar df padronizado
        df2 = pd.DataFrame()
        df2["Data_Pedido"] = pd.to_datetime(df[data_col], errors="coerce", dayfirst=True)
        df2["Qtd_bilhetes"] = df[qtd_col].apply(parse_int)
        df2["Valor"] = df[valor_col].apply(parse_currency)
        df2["E-mail"] = df[email_col].astype(str).str.strip() if email_col else np.nan
        df2["Nome"] = df[nome_col].astype(str).str.strip() if nome_col else np.nan
        df2["Telefone"] = df[telefone_col].astype(str).str.strip() if telefone_col else np.nan
        df2["Referência_externa_do_pagamento"] = df[ref_col].astype(str).str.strip() if ref_col else np.nan
        df2["arquivo_origem"] = file.name

        df2 = df2.dropna(subset=["Data_Pedido"])
        if df2.empty:
            st.warning(f"Arquivo {file.name} não possui datas válidas — ignorado.")
            continue

        dfs.append(df2)
        st.success(f"{file.name} — registros válidos: {len(df2)}")

    except Exception as e:
        st.error(f"Erro ao processar {file.name}: {e}")

if not dfs:
    st.error("Nenhum arquivo válido para análise. Verifique os arquivos e os nomes de colunas.")
    st.stop()

# ---------- Combina e limpa ----------
df_total = pd.concat(dfs, ignore_index=True)
df_total["ID_unico"] = df_total["Referência_externa_do_pagamento"].fillna("") + "__" + df_total["E-mail"].fillna("") + "__" + df_total["Data_Pedido"].astype(str)
df_total = df_total.drop_duplicates(subset="ID_unico", keep="first").reset_index(drop=True)

df_total["Valor"] = pd.to_numeric(df_total["Valor"], errors="coerce").fillna(0.0)
df_total["Qtd_bilhetes"] = pd.to_numeric(df_total["Qtd_bilhetes"], errors="coerce").fillna(0).astype(int)

# ---------- Métricas gerais ----------
total_vendas = df_total["Valor"].sum()
total_bilhetes = df_total["Qtd_bilhetes"].sum()
ticket_medio = total_vendas / total_bilhetes if total_bilhetes > 0 else 0.0

st.subheader("Resumo Rápido")
c1, c2, c3 = st.columns(3)
c1.metric("Valor total vendido (R$)", f"{total_vendas:,.2f}")
c2.metric("Total bilhetes", f"{total_bilhetes:,d}")
c3.metric("Ticket médio (R$)", f"{ticket_medio:,.2f}")

# ---------- Agrupamentos ----------
df_total["AnoMes"] = df_total["Data_Pedido"].dt.to_period("M")
df_total["AnoSemana"] = df_total["Data_Pedido"].dt.to_period("W")
mensal = df_total.groupby("AnoMes").agg({"Qtd_bilhetes":"sum", "Valor":"sum"}).reset_index()
mensal["Ticket_medio"] = mensal["Valor"] / mensal["Qtd_bilhetes"].replace({0: np.nan})
mensal["Crescimento_valor_pct"] = mensal["Valor"].pct_change().fillna(0) * 100
mensal["Crescimento_qtd_pct"] = mensal["Qtd_bilhetes"].pct_change().fillna(0) * 100

semanal = df_total.groupby("AnoSemana").agg({"Qtd_bilhetes":"sum", "Valor":"sum"}).reset_index()
semanal["Ticket_medio"] = semanal["Valor"] / semanal["Qtd_bilhetes"].replace({0: np.nan})
semanal["Crescimento_qtd_pct"] = semanal["Qtd_bilhetes"].pct_change().fillna(0) * 100

# ---------- Gráficos ----------
st.subheader("Vendas por mês (Valor)")
fig1 = px.bar(mensal, x=mensal["AnoMes"].astype(str), y="Valor", labels={"Valor":"Valor (R$)", "AnoMes":"Mês"})
st.plotly_chart(fig1, use_container_width=True)

st.subheader("Bilhetes por mês")
fig2 = px.bar(mensal, x=mensal["AnoMes"].astype(str), y="Qtd_bilhetes", labels={"Qtd_bilhetes":"Qtd bilhetes"})
st.plotly_chart(fig2, use_container_width=True)

st.subheader("Ticket médio por mês")
fig3 = px.line(mensal, x=mensal["AnoMes"].astype(str), y="Ticket_medio", markers=True)
st.plotly_chart(fig3, use_container_width=True)

st.subheader("Comparação semanal: bilhetes x valor")
fig4 = px.bar(semanal, x=semanal["AnoSemana"].astype(str), y="Qtd_bilhetes", labels={"Qtd_bilhetes":"Qtd bilhetes"})
fig4.add_scatter(x=semanal["AnoSemana"].astype(str), y=semanal["Valor"], mode="lines+markers", name="Valor")
st.plotly_chart(fig4, use_container_width=True)

# ---------- Análise por dia do mês ----------
df_total["Dia"] = df_total["Data_Pedido"].dt.day
dias = df_total.groupby("Dia").agg({"Qtd_bilhetes":"mean", "Valor":"mean"}).reset_index().sort_values("Dia")
dias["Ticket_medio"] = dias["Valor"] / dias["Qtd_bilhetes"].replace({0: np.nan})
melhor_dia = dias.loc[dias["Valor"].idxmax()]
pior_dia = dias.loc[dias["Valor"].idxmin()]

st.subheader("Média de vendas por dia do mês (consolidada)")
fig_dias = px.bar(dias, x="Dia", y="Valor", labels={"Valor":"Valor médio (R$)", "Dia":"Dia do mês"})
st.plotly_chart(fig_dias, use_container_width=True)
st.write(f"🔥 Melhor dia (média): dia {int(melhor_dia['Dia'])} — R$ {melhor_dia['Valor']:.2f}")
st.write(f"❄️ Pior dia (média): dia {int(pior_dia['Dia'])} — R$ {pior_dia['Valor']:.2f}")

# ---------- Top clientes ----------
if df_total["E-mail"].notna().any():
    clientes = df_total.groupby("E-mail", as_index=False).agg({"Valor":"sum", "Qtd_bilhetes":"sum", "Nome":"first"})
    clientes = clientes.sort_values("Valor", ascending=False)
    top_cliente = clientes.iloc[0]
    st.subheader("Top cliente")
    st.write(f"{top_cliente.get('Nome', top_cliente['E-mail'])} — R$ {top_cliente['Valor']:.2f} — {int(top_cliente['Qtd_bilhetes']):,d} bilhetes")
else:
    st.info("Sem coluna de E-mail para análise de clientes.")

# ---------- Insights rápidos ----------
insights = []
if len(mensal) >= 2:
    ultimo = mensal.iloc[-1]
    penultimo = mensal.iloc[-2]
    diff_val = ultimo["Valor"] - penultimo["Valor"]
    diff_bil = int(ultimo["Qtd_bilhetes"] - penultimo["Qtd_bilhetes"])
    pct_val = (diff_val / penultimo["Valor"] * 100) if penultimo["Valor"] != 0 else np.nan
    insights.append(f"Valor: último mês ({ultimo['AnoMes']}) variação R$ {diff_val:,.2f} ({pct_val:.2f}%) vs mês anterior.")
    insights.append(f"Bilhetes: variação de {diff_bil:,d} bilhetes vs mês anterior.")
else:
    insights.append("Dados mensais insuficientes para comparação mês a mês.")
insights.append(f"Melhor dia médio do mês: {int(melhor_dia['Dia'])} — R$ {melhor_dia['Valor']:.2f}")
insights.append(f"Pior dia médio do mês: {int(pior_dia['Dia'])} — R$ {pior_dia['Valor']:.2f}")

st.subheader("Insights rápidos")
for it in insights:
    st.write(it)

# ---------- Gerar PDF ----------
def gerar_pdf_bytes():
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=30, bottomMargin=18)
    styles = getSampleStyleSheet()
    elems = []

    elems.append(Paragraph("Relatório: Análise de Vendas e Bilhetes", styles['Title']))
    elems.append(Spacer(1,12))
    elems.append(Paragraph(f"Valor total vendido: R$ {total_vendas:,.2f}", styles['Normal']))
    elems.append(Paragraph(f"Total de bilhetes vendidos: {total_bilhetes:,d}", styles['Normal']))
    elems.append(Paragraph(f"Ticket médio: R$ {ticket_medio:,.2f}", styles['Normal']))
    elems.append(Spacer(1,12))

    elems.append(Paragraph("Resumo Mensal", styles['Heading2']))
    table_data = [["Mês","Qtd Bilhetes","Valor (R$)","Ticket médio (R$)"]]
    for _, r in mensal.iterrows():
        table_data.append([str(r["AnoMes"]), f"{int(r['Qtd_bilhetes']):,d}", f"{r['Valor']:,.2f}", f"{r['Ticket_medio']:,.2f}"])
    t = Table(table_data, hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.lightgrey), ('GRID',(0,0),(-1,-1),0.25,colors.grey)]))
    elems.append(t)
    elems.append(Spacer(1,12))

    elems.append(Paragraph("Melhor e pior dia do mês (média consolidada)", styles['Heading2']))
    elems.append(Paragraph(f"Melhor dia (média): dia {int(melhor_dia['Dia'])} — R$ {melhor_dia['Valor']:.2f}", styles['Normal']))
    elems.append(Paragraph(f"Pior dia (média): dia {int(pior_dia['Dia'])} — R$ {pior_dia['Valor']:.2f}", styles['Normal']))
    elems.append(Spacer(1,12))

    elems.append(Paragraph("Insights Rápidos", styles['Heading2']))
    for it in insights:
        elems.append(Paragraph(it, styles['Normal']))

    doc.build(elems)
    buf.seek(0)
    return buf

if st.button("📥 Gerar/baixar PDF"):
    pdf_buf = gerar_pdf_bytes()
    st.download_button("Clique para baixar o PDF", data=pdf_buf, file_name="relatorio_vendas_v3.pdf", mime="application/pdf")


# ---------- (restante do código de agrupamentos, gráficos, análises e PDF mantém igual) ----------

# ---------- Integração com WhatsApp ----------
# if st.button("📲 Abrir painel WhatsApp"):
#     whatsapp_sender.whatsapp_ui(df_total)




if st.button("📲 Disparo de WhatsApp (via QR)"):
    mensagem_padrao = st.text_area("Mensagem a enviar:", "Olá {nome}, obrigado pela compra! 🎉")
    whatsapp_disparos.enviar_whatsapp(df_total, mensagem_padrao)