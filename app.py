import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from fpdf import FPDF
import io
import base64

# Conexão com MongoDB (usando secrets)
client = MongoClient(st.secrets["database"]["url"])
db = client.extintores
empresas_col = db.empresas
usuarios = {
    st.secrets["users"]["USUARIO1"].lower(): st.secrets["users"]["SENHA1"],
    st.secrets["users"]["USUARIO2"].lower(): st.secrets["users"]["SENHA2"],
}

# Sessão
if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario = ""


# Função login
def login():
    st.title("Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if usuario.lower() in usuarios and senha == usuarios[usuario.lower()]:
            st.session_state.logado = True
            st.session_state.usuario = usuario
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos")


# Cadastro da empresa
def cadastrar_empresa():
    st.title("Cadastro de Empresa")
    nome = st.text_input("Nome da Empresa")
    cidade = st.text_input("Cidade")
    endereco = st.text_input("Endereço Completo")
    telefone = st.text_input("Telefone")
    data_cadastro = st.date_input("Data de Cadastro", value=datetime.today())

    st.subheader("Cadastro de Extintores")
    extintores = []
    with st.form("extintores_form"):
        tipo_extintor = st.selectbox("Tipo de Extintor", ["Pó ABC", "Pó BC", "CO2", "Água"])
        capacidade = st.selectbox("Capacidade", ["4kg", "6kg", "10kg", "10L", "75L"])
        quantidade = st.number_input("Quantidade", min_value=1, step=1)
        adicionar = st.form_submit_button("Adicionar")
        if adicionar:
            if "extintores_temp" not in st.session_state:
                st.session_state.extintores_temp = []
            st.session_state.extintores_temp.append({
                "tipo": tipo_extintor,
                "capacidade": capacidade,
                "quantidade": quantidade
            })

    if "extintores_temp" in st.session_state:
        for i, ext in enumerate(st.session_state.extintores_temp):
            st.write(f"{i+1}. {ext['tipo']} - {ext['capacidade']} - {ext['quantidade']} unidades")
            if st.button(f"Remover {i+1}"):
                st.session_state.extintores_temp.pop(i)
                st.rerun()

    st.subheader("Mangueiras de Incêndio")
    qtd_m15 = st.number_input("Mangueiras 15m", min_value=0, step=1)
    qtd_m30 = st.number_input("Mangueiras 30m", min_value=0, step=1)

    if st.button("Salvar Empresa"):
        if nome and cidade:
            empresa = {
                "nome": nome,
                "cidade": cidade,
                "endereco": endereco,
                "telefone": telefone,
                "data_cadastro": datetime.combine(data_cadastro, datetime.min.time()),
                "usuario": st.session_state.usuario,
                "extintores": st.session_state.get("extintores_temp", []),
                "mangueiras": {
                    "15m": qtd_m15,
                    "30m": qtd_m30
                }
            }
            empresas_col.insert_one(empresa)
            st.success("Empresa cadastrada com sucesso!")
            st.session_state.extintores_temp = []
            st.rerun()
        else:
            st.error("Preencha todos os campos obrigatórios")


# Consulta e edição
def consultar_empresas():
    st.title("Empresas Cadastradas")
    busca = st.text_input("Buscar por nome")
    if busca:
        empresas = empresas_col.find({"nome": {"$regex": busca, "$options": "i"}, "usuario": st.session_state.usuario})
    else:
        empresas = empresas_col.find({"usuario": st.session_state.usuario})

    for empresa in empresas:
        with st.expander(empresa["nome"]):
            st.write(f"Cidade: {empresa.get('cidade', '')}")
            st.write(f"Endereço: {empresa.get('endereco', '')}")
            st.write(f"Telefone: {empresa.get('telefone', '')}")
            st.write(f"Data Cadastro: {empresa['data_cadastro'].strftime('%d/%m/%Y')}")
            st.write("**Extintores:**")
            for ext in empresa.get("extintores", []):
                st.write(f"- {ext['tipo']} - {ext['capacidade']} - {ext['quantidade']} un")
            st.write("**Mangueiras:**")
            st.write(f"15m: {empresa.get('mangueiras', {}).get('15m', 0)} un")
            st.write(f"30m: {empresa.get('mangueiras', {}).get('30m', 0)} un")
            if st.button("Excluir", key=str(empresa['_id'])):
                empresas_col.delete_one({"_id": ObjectId(empresa['_id'])})
                st.success("Empresa excluída")
                st.rerun()


# Relatório de vencimentos
def relatorio():
    st.title("Relatório de Vencimento")
    cidade_filtro = st.text_input("Filtrar por cidade")
    tipo_extintor_filtro = st.text_input("Filtrar por tipo de extintor")
    data_inicio = st.date_input("Início do Período", value=datetime.today())
    data_fim = st.date_input("Fim do Período", value=datetime.today() + timedelta(days=30))

    query = {"usuario": st.session_state.usuario}
    if cidade_filtro:
        query["cidade"] = {"$regex": cidade_filtro, "$options": "i"}

    empresas = empresas_col.find(query)
    vencendo = []

    for emp in empresas:
        vencimento = emp["data_cadastro"] + timedelta(days=365)
        if data_inicio <= vencimento.date() <= data_fim:
            if tipo_extintor_filtro:
                if any(tipo_extintor_filtro.lower() in ext['tipo'].lower() or tipo_extintor_filtro.lower() in ext['capacidade'].lower() for ext in emp.get("extintores", [])):
                    vencendo.append((emp, vencimento))
            else:
                vencendo.append((emp, vencimento))

    for emp, venc in vencendo:
        with st.expander(emp["nome"]):
            st.write(f"Cidade: {emp.get('cidade', '')}")
            st.write(f"Telefone: {emp.get('telefone', '')}")
            st.write(f"Vencimento: {venc.strftime('%d/%m/%Y')}")

    if vencendo:
        if st.button("Baixar PDF"):
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt="Relatório de Vencimentos", ln=True, align='C')
            for emp, venc in vencendo:
                pdf.cell(200, 10, txt=f"{emp['nome']} - {emp.get('cidade', '')} - {venc.strftime('%d/%m/%Y')}", ln=True)
            pdf_output = io.BytesIO()
            pdf.output(pdf_output)
            b64 = base64.b64encode(pdf_output.getvalue()).decode()
            href = f'<a href="data:application/pdf;base64,{b64}" download="relatorio.pdf">Clique aqui para baixar o PDF</a>'
            st.markdown(href, unsafe_allow_html=True)


# App
if not st.session_state.logado:
    login()
else:
    menu = st.sidebar.selectbox("Menu", ["Cadastrar Empresa", "Empresas Cadastradas", "Relatório de Vencimento"])
    if menu == "Cadastrar Empresa":
        cadastrar_empresa()
    elif menu == "Empresas Cadastradas":
        consultar_empresas()
    elif menu == "Relatório de Vencimento":
        relatorio()
