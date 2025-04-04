import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta

# Autenticação com secrets
MONGO_URL = st.secrets["database"]["url"]
USERS = {
    st.secrets["users"]["USUARIO1"]: st.secrets["users"]["SENHA1"],
    st.secrets["users"]["USUARIO2"]: st.secrets["users"]["SENHA2"]
}

# Conectar ao MongoDB
client = MongoClient(MONGO_URL)
db = client["extintores_db"]
companies_collection = db["companies"]

# Função de autenticação
def authenticate(username, password):
    return USERS.get(username) == password

# Tela de login
if "logged_in" not in st.session_state:
    st.title("Login")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if authenticate(username, password):
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos")

# Após login
if st.session_state.get("logged_in"):
    st.sidebar.title("Navegação")
    pagina = st.sidebar.radio("Ir para", ["Cadastro de Empresa", "Empresas Cadastradas", "Relatório de Vencimento"])

    if pagina == "Cadastro de Empresa":
        st.title("Cadastro de Empresa")
        nome_empresa = st.text_input("Nome da Empresa")
        endereco = st.text_area("Endereço Completo")
        cidade = st.text_input("Cidade")
        telefone = st.text_input("Telefone")

        tipos_extintores = ["ABC 4kg", "ABC 6kg", "ABC 10kg", "BC 4kg", "BC 6kg", "CO2 4kg", "CO2 6kg", "Água 10L", "Água 75L"]
        extintores = st.multiselect("Modelos de Extintores", tipos_extintores)

        tipos_mangueiras = ["15m", "30m"]
        mangueiras = st.multiselect("Mangueiras de Incêndio", tipos_mangueiras)

        if st.button("Cadastrar Empresa"):
            data_cadastro = datetime.now()
            data_vencimento = data_cadastro + timedelta(days=365)

            empresa = {
                "nome": nome_empresa,
                "endereco": endereco,
                "cidade": cidade,
                "telefone": telefone,
                "extintores": extintores,
                "mangueiras": mangueiras,
                "usuario": st.session_state["username"],
                "data_cadastro": data_cadastro,
                "data_vencimento": data_vencimento
            }

            companies_collection.insert_one(empresa)
            st.success("Empresa cadastrada com sucesso!")
            st.rerun()

    elif pagina == "Empresas Cadastradas":
        st.title("Empresas Cadastradas")

        empresas = list(companies_collection.find({"usuario": st.session_state["username"]}))
        nomes_empresas = [empresa["nome"] for empresa in empresas]
        empresa_selecionada = st.selectbox("Buscar empresa", ["Selecione"] + nomes_empresas)

        if empresa_selecionada != "Selecione":
            empresa = next(e for e in empresas if e["nome"] == empresa_selecionada)
            st.write(f"📍 Endereço: {empresa['endereco']}")
            st.write(f"🏙️ Cidade: {empresa['cidade']}")
            st.write(f"📞 Telefone: {empresa['telefone']}")
            st.write(f"🧯 Extintores: {', '.join(empresa['extintores'])}")
            st.write(f"🚿 Mangueiras: {', '.join(empresa['mangueiras'])}")
            st.write(f"📅 Cadastro: {empresa['data_cadastro'].strftime('%d/%m/%Y')}")
            st.write(f"⚠️ Vencimento: {empresa['data_vencimento'].strftime('%d/%m/%Y')}")

            if st.button("Excluir Empresa"):
                companies_collection.delete_one({"_id": empresa["_id"]})
                st.success("Empresa excluída com sucesso!")
                st.rerun()

    elif pagina == "Relatório de Vencimento":
        st.title("Empresas com Extintores a Vencer")

        hoje = datetime.now()
        proximo_ano = hoje + timedelta(days=365)

        cidades_disponiveis = companies_collection.distinct("cidade", {"usuario": st.session_state["username"]})
        cidade_filtro = st.selectbox("Filtrar por Cidade", ["Todas"] + sorted(cidades_disponiveis))

        tipos_extintores_disponiveis = ["ABC 4kg", "ABC 6kg", "ABC 10kg", "BC 4kg", "BC 6kg", "CO2 4kg", "CO2 6kg", "Água 10L", "Água 75L"]
        extintor_filtro = st.selectbox("Filtrar por Tipo de Extintor", ["Todos"] + tipos_extintores_disponiveis)

        filtro = {
            "usuario": st.session_state["username"],
            "data_vencimento": {"$lte": proximo_ano}
        }

        if cidade_filtro != "Todas":
            filtro["cidade"] = cidade_filtro

        empresas_vencendo = companies_collection.find(filtro)

        if extintor_filtro != "Todos":
            empresas_vencendo = filter(lambda e: extintor_filtro in e["extintores"], empresas_vencendo)

        for empresa in empresas_vencendo:
            with st.expander(empresa["nome"]):
                st.write(f"📍 Endereço: {empresa['endereco']}")
                st.write(f"🏙️ Cidade: {empresa['cidade']}")
                st.write(f"📞 Telefone: {empresa['telefone']}")
                st.write(f"🧯 Extintores: {', '.join(empresa['extintores'])}")
                st.write(f"🚿 Mangueiras: {', '.join(empresa['mangueiras'])}")
                st.write(f"📅 Cadastro: {empresa['data_cadastro'].strftime('%d/%m/%Y')}")
                st.write(f"⚠️ Vencimento: {empresa['data_vencimento'].strftime('%d/%m/%Y')}")

    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()
