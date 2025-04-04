import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta

# Conectar ao MongoDB usando secrets
client = MongoClient(st.secrets["database"]["url"])
db = client.extintores
empresas_collection = db.empresas

# Autenticação
USUARIOS = {
    st.secrets["users"]["USUARIO1"]: st.secrets["users"]["SENHA1"],
    st.secrets["users"]["USUARIO2"]: st.secrets["users"]["SENHA2"]
}

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

# Menu lateral
menu = st.sidebar.radio("Menu", ["Cadastrar Empresa", "Empresas Cadastradas", "Relatório de Vencimento"])

# Cadastro de Empresa
if menu == "Cadastrar Empresa":
    st.title("Cadastro de Empresa")
    nome = st.text_input("Nome da Empresa")
    cidade = st.text_input("Cidade")
    endereco = st.text_input("Endereço Completo")
    telefone = st.text_input("Telefone")
    data_cadastro = st.date_input("Data do Cadastro", value=datetime.today())

    if "extintores" not in st.session_state:
        st.session_state.extintores = []

    st.subheader("Adicionar Extintores")

    col1, col2, col3 = st.columns(3)
    with col1:
        novo_tipo = st.selectbox("Modelo", ["ABC", "BC", "CO2", "Água"])
    with col2:
        nova_capacidade = st.selectbox("Capacidade", ["4kg", "6kg", "10kg", "10L", "75L"])
    with col3:
        nova_quantidade = st.number_input("Quantidade", min_value=1, step=1)

    if st.button("Adicionar Extintor"):
        st.session_state.extintores.append({
            "tipo": novo_tipo,
            "capacidade": nova_capacidade,
            "quantidade": nova_quantidade
        })

    for i, ext in enumerate(st.session_state.extintores):
        st.markdown(f"- **{ext['quantidade']}x {ext['tipo']} ({ext['capacidade']})**")
        if st.button(f"Remover Extintor {i+1}"):
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
            st.error("Preencha todos os campos e adicione ao menos um extintor.")

# Consulta Empresas
elif menu == "Empresas Cadastradas":
    st.title("Empresas Cadastradas")
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

# Relatório de Vencimento
elif menu == "Relatório de Vencimento":
    st.title("Relatório de Vencimento de Extintores")

    cidades = empresas_collection.distinct("cidade", {"usuario": st.session_state.usuario})
    cidade_filtro = st.selectbox("Filtrar por cidade", ["Todas"] + cidades)

    modelo_filtro = st.selectbox("Filtrar por modelo", ["Todos", "ABC", "BC", "CO2", "Água"])
    capacidade_filtro = st.selectbox("Filtrar por capacidade", ["Todas", "4kg", "6kg", "10kg", "10L", "75L"])

    data_inicio = st.date_input("Data de Início", value=datetime.today())
    data_fim = st.date_input("Data de Fim", value=datetime.today() + timedelta(days=30))

    query = {
        "usuario": st.session_state.usuario,
        "vencimento": {"$gte": data_inicio.strftime("%Y-%m-%d"), "$lte": data_fim.strftime("%Y-%m-%d")}
    }
    if cidade_filtro != "Todas":
        query["cidade"] = cidade_filtro

    empresas = list(empresas_collection.find(query))

    if modelo_filtro != "Todos":
        empresas = [e for e in empresas if any(ext["tipo"] == modelo_filtro for ext in e["extintores"])]

    if capacidade_filtro != "Todas":
        empresas = [e for e in empresas if any(ext["capacidade"] == capacidade_filtro for ext in e["extintores"])]

    if empresas:
        for empresa in empresas:
            st.subheader(empresa["nome"])
            st.write(f"Cidade: {empresa['cidade']} | Vencimento: {empresa['vencimento']}")
            for ext in empresa["extintores"]:
                st.write(f"- {ext['quantidade']}x {ext['tipo']} ({ext['capacidade']})")
    else:
        st.info("Nenhuma empresa encontrada com os filtros selecionados.")
