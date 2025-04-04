import streamlit as st
import pymongo
import datetime
from bson.objectid import ObjectId
from fpdf import FPDF
import io
import re

# ----- CONFIGURAÇÕES INICIAIS ----- #

st.set_page_config(page_title="Sistema de Extintores", layout="wide")
st.title("Sistema de Gerenciamento de Extintores")

# Conexão com o MongoDB
mongo_url = st.secrets["database"]["url"]
client = pymongo.MongoClient(mongo_url)
db = client["extintores"]
colecao_empresas = db["empresas"]

# Autenticação
usuarios = {
    st.secrets["users"]["USUARIO1"].lower(): st.secrets["users"]["SENHA1"],
    st.secrets["users"]["USUARIO2"].lower(): st.secrets["users"]["SENHA2"]
}

if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    with st.form("login"):
        usuario = st.text_input("Usuário").lower()
        senha = st.text_input("Senha", type="password")
        login = st.form_submit_button("Entrar")

    if login:
        if usuario in usuarios and usuarios[usuario] == senha:
            st.session_state.logado = True
            st.session_state.usuario = usuario
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
    st.stop()

# MENU PRINCIPAL
menu = st.sidebar.selectbox("Menu", ["Cadastrar Empresa", "Empresas Cadastradas", "Relatório de Vencimento"])

# ----- FUNÇÃO CADASTRO ----- #
if menu == "Cadastrar Empresa":
    st.subheader("Cadastro de Empresa")

    with st.form("form_empresa"):
        nome = st.text_input("Nome da empresa")
        cidade = st.text_input("Cidade")
        endereco = st.text_input("Endereço")
        telefone = st.text_input("Telefone")
        data_cadastro = st.date_input("Data do Cadastro", value=datetime.date.today())

        st.markdown("### Extintores")
        extintores = []
        add_extintor = st.checkbox("Adicionar Extintor")
        while add_extintor:
            tipo = st.selectbox("Tipo de Extintor", ["Pó ABC", "Pó BC", "CO2", "Água"])
            capacidade = st.selectbox("Capacidade", ["4kg", "6kg", "10kg", "10L", "75L"])
            quantidade = st.number_input("Quantidade", min_value=1, step=1)
            extintores.append({"tipo": tipo, "capacidade": capacidade, "quantidade": quantidade})
            if not st.checkbox("Adicionar Outro Extintor"):
                break

        st.markdown("### Mangueiras")
        mangueiras = []
        add_mangueira = st.checkbox("Adicionar Mangueira")
        while add_mangueira:
            metragem = st.selectbox("Tamanho da Mangueira", ["15m", "30m"])
            quantidade = st.number_input(f"Quantidade ({metragem})", min_value=1, step=1, key=metragem)
            mangueiras.append({"metragem": metragem, "quantidade": quantidade})
            if not st.checkbox("Adicionar Outra Mangueira"):
                break

        enviar = st.form_submit_button("Salvar")

    if enviar:
        dados = {
            "nome": nome,
            "cidade": cidade,
            "endereco": endereco,
            "telefone": telefone,
            "usuario": st.session_state.usuario,
            "data_cadastro": str(data_cadastro),
            "extintores": extintores,
            "mangueiras": mangueiras
        }
        colecao_empresas.insert_one(dados)
        st.success("Empresa cadastrada com sucesso!")
        st.rerun()

# ----- FUNÇÃO VISUALIZAR / EDITAR / EXCLUIR ----- #
if menu == "Empresas Cadastradas":
    st.subheader("Empresas Cadastradas")

    empresas = list(colecao_empresas.find({"usuario": st.session_state.usuario}))
    nomes = [e["nome"] for e in empresas]

    empresa_selecionada = st.selectbox("Selecione uma empresa", nomes)

    if empresa_selecionada:
        empresa = next(e for e in empresas if e["nome"] == empresa_selecionada)

        st.write("### Dados da Empresa")
        st.write(f"**Cidade:** {empresa.get('cidade', '')}")
        st.write(f"**Endereço:** {empresa.get('endereco', '')}")
        st.write(f"**Telefone:** {empresa.get('telefone', '')}")
        st.write(f"**Data de Cadastro:** {empresa.get('data_cadastro', '')}")

        st.write("### Extintores")
        for ext in empresa.get("extintores", []):
            st.write(f"{ext['tipo']} - {ext['capacidade']} - Quantidade: {ext['quantidade']}")

        st.write("### Mangueiras")
        for m in empresa.get("mangueiras", []):
            st.write(f"{m['metragem']} - Quantidade: {m['quantidade']}")

        if st.button("Excluir Empresa"):
            colecao_empresas.delete_one({"_id": empresa["_id"]})
            st.success("Empresa excluída.")
            st.rerun()

# ----- FUNÇÃO RELATÓRIO ----- #
if menu == "Relatório de Vencimento":
    st.subheader("Empresas com Extintores a Vencer")

    cidades = sorted(set([e.get("cidade", "").title() for e in colecao_empresas.find({})]))
    cidade_filtro = st.selectbox("Filtrar por cidade", ["Todas"] + cidades)

    modelos = ["Pó ABC", "Pó BC", "CO2", "Água"]
    modelo_filtro = st.selectbox("Filtrar por modelo de extintor", ["Todos"] + modelos)

    data_inicio = st.date_input("Data inicial", value=datetime.date.today())
    data_fim = st.date_input("Data final", value=data_inicio + datetime.timedelta(days=30))

    resultados = []

    for empresa in colecao_empresas.find({"usuario": st.session_state.usuario}):
        data_cadastro = datetime.datetime.strptime(empresa["data_cadastro"], "%Y-%m-%d").date()
        data_vencimento = data_cadastro + datetime.timedelta(days=365)

        if data_inicio <= data_vencimento <= data_fim:
            if cidade_filtro != "Todas" and empresa.get("cidade", "").lower() != cidade_filtro.lower():
                continue
            if modelo_filtro != "Todos":
                if not any(ext["tipo"].lower() == modelo_filtro.lower() for ext in empresa.get("extintores", [])):
                    continue
            resultados.append((empresa, data_vencimento))

    for empresa, venc in resultados:
        st.write(f"**{empresa['nome']}** - Cidade: {empresa['cidade']} - Vencimento: {venc.strftime('%d/%m/%Y')}")

    if resultados:
        if st.button("Baixar Relatório em PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Relatório de Empresas com Extintores a Vencer", ln=True, align="C")
            pdf.ln(10)
            for empresa, venc in resultados:
                pdf.cell(200, 10, txt=f"{empresa['nome']} - Cidade: {empresa['cidade']} - Vence: {venc.strftime('%d/%m/%Y')}", ln=True)

            buffer = io.BytesIO()
            pdf.output(buffer)
            st.download_button(
                label="Download PDF",
                data=buffer.getvalue(),
                file_name="relatorio_extintores.pdf",
                mime="application/pdf"
            )
