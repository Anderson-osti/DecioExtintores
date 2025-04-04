import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
import uuid

# Conexão com o MongoDB
client = MongoClient(st.secrets["database"]["url"])
db = client.extintores
empresas_collection = db.empresas

# Autenticação de usuários
USUARIOS = {
    st.secrets["users"]["USUARIO1"]: st.secrets["users"]["SENHA1"],
    st.secrets["users"]["USUARIO2"]: st.secrets["users"]["SENHA2"]
}

# Sessão
if "logado" not in st.session_state:
    st.session_state.logado = False
if "usuario" not in st.session_state:
    st.session_state.usuario = ""

# Login
if not st.session_state.logado:
    st.title("Login")
    user = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if user in USUARIOS and USUARIOS[user] == password:
            st.session_state.logado = True
            st.session_state.usuario = user
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos")
    st.stop()

# Menu
menu = st.sidebar.radio("Menu", ["Cadastrar Empresa", "Empresas Cadastradas", "Relatório de Vencimento"])


# Função para adicionar extintores
def adicionar_extintor():
    tipo = st.selectbox("Tipo de Extintor", ["ABC", "BC", "CO2", "Água"], key=str(uuid.uuid4()))
    capacidade = st.selectbox("Capacidade", ["4kg", "6kg", "10kg", "10L"], key=str(uuid.uuid4()))
    quantidade = st.number_input("Quantidade", min_value=1, step=1, key=str(uuid.uuid4()))
    return {"tipo": tipo, "capacidade": capacidade, "quantidade": quantidade}


# Tela: Cadastrar Empresa
if menu == "Cadastrar Empresa":
    st.header("Cadastrar Empresa")
    nome = st.text_input("Nome da Empresa")
    cidade = st.text_input("Cidade")
    endereco = st.text_input("Endereço Completo")
    telefone = st.text_input("Telefone")
    data_cadastro = st.date_input("Data do Cadastro", value=datetime.today())

    st.subheader("Adicionar Extintores")
    extintores = []
    if "extintores" not in st.session_state:
        st.session_state.extintores = []

    if st.button("Adicionar Extintor"):
        st.session_state.extintores.append(adicionar_extintor())

    for i, ext in enumerate(st.session_state.extintores):
        st.write(f"{i+1}. Tipo: {ext['tipo']} | Capacidade: {ext['capacidade']} | Quantidade: {ext['quantidade']}")
        if st.button(f"Remover {i+1}"):
            st.session_state.extintores.pop(i)
            st.rerun()

    if st.button("Salvar Empresa"):
        if nome and cidade and endereco and telefone and st.session_state.extintores:
            empresa = {
                "nome": nome,
                "cidade": cidade,
                "endereco": endereco,
                "telefone": telefone,
                "data_cadastro": data_cadastro.strftime("%Y-%m-%d"),
                "vencimento": (data_cadastro + timedelta(days=365)).strftime("%Y-%m-%d"),
                "extintores": st.session_state.extintores,
                "usuario": st.session_state.usuario
            }
            empresas_collection.insert_one(empresa)
            st.success("Empresa cadastrada com sucesso!")
            st.session_state.extintores = []
            st.rerun()
        else:
            st.error("Preencha todos os campos e adicione ao menos um extintor")

# Tela: Empresas Cadastradas
elif menu == "Empresas Cadastradas":
    st.header("Empresas Cadastradas")
    empresas = list(empresas_collection.find({"usuario": st.session_state.usuario}))

    if not empresas:
        st.info("Nenhuma empresa cadastrada ainda.")
    else:
        nomes = [e["nome"] for e in empresas]
        selecionada = st.selectbox("Selecione uma empresa", nomes)
        empresa = next(e for e in empresas if e["nome"] == selecionada)

        st.write(f"**Nome:** {empresa['nome']}")
        st.write(f"**Cidade:** {empresa['cidade']}")
        st.write(f"**Endereço:** {empresa['endereco']}")
        st.write(f"**Telefone:** {empresa['telefone']}")
        st.write(f"**Data Cadastro:** {empresa['data_cadastro']}")
        st.write(f"**Vencimento:** {empresa['vencimento']}")

        st.subheader("Extintores:")
        for ext in empresa["extintores"]:
            st.write(f"- {ext['quantidade']}x {ext['tipo']} ({ext['capacidade']})")

        if st.button("Excluir Empresa"):
            empresas_collection.delete_one({"_id": empresa["_id"]})
            st.success("Empresa excluída.")
            st.rerun()

# Tela: Relatório de Vencimento
elif menu == "Relatório de Vencimento":
    st.header("Empresas com Extintores a Vencer")
    cidades = empresas_collection.distinct("cidade", {"usuario": st.session_state.usuario})
    cidade_filtro = st.selectbox("Filtrar por cidade", ["Todas"] + cidades)

    tipos = ["4kg", "6kg", "10kg", "10L"]
    tipo_filtro = st.selectbox("Filtrar por capacidade de extintor", ["Todas"] + tipos)

    data_inicio = st.date_input("Data início", value=datetime.today())
    data_fim = st.date_input("Data fim", value=datetime.today() + timedelta(days=30))

    query = {
        "usuario": st.session_state.usuario,
        "vencimento": {"$gte": data_inicio.strftime("%Y-%m-%d"), "$lte": data_fim.strftime("%Y-%m-%d")}
    }
    if cidade_filtro != "Todas":
        query["cidade"] = cidade_filtro

    empresas = list(empresas_collection.find(query))

    if tipo_filtro != "Todas":
        empresas = [e for e in empresas if any(ext["capacidade"] == tipo_filtro for ext in e["extintores"])]

    if empresas:
        for empresa in empresas:
            st.subheader(empresa["nome"])
            st.write(f"Cidade: {empresa['cidade']} | Vencimento: {empresa['vencimento']}")
    else:
        st.info("Nenhuma empresa encontrada para o filtro selecionado.")
