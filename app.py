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


def authenticate(username, password):
    return USERS.get(username) == password


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

if st.session_state.get("logged_in"):
    st.sidebar.title("Navegação")
    pagina = st.sidebar.radio("Ir para", ["Cadastro de Empresa", "Empresas Cadastradas", "Relatório de Vencimento"])

    if pagina == "Cadastro de Empresa":
        st.title("Cadastro de Empresa")
        nome_empresa = st.text_input("Nome da Empresa")
        endereco = st.text_area("Endereço Completo")
        cidade = st.text_input("Cidade")
        telefone = st.text_input("Telefone")

        tipos_extintores = {
            "ABC": ["4kg", "6kg", "10kg"],
            "BC": ["4kg", "6kg", "10kg"],
            "CO2": ["4kg", "6kg", "10kg"],
            "Água": ["10L", "75L"]
        }
        extintores_selecionados = []
        for tipo, capacidades in tipos_extintores.items():
            with st.expander(f"{tipo}"):
                for capacidade in capacidades:
                    quantidade = st.number_input(f"{capacidade} ({tipo})", min_value=0, step=1,
                                                 key=f"{tipo}_{capacidade}")
                    if quantidade > 0:
                        extintores_selecionados.append(
                            {"tipo": tipo, "capacidade": capacidade, "quantidade": quantidade})

        tipos_mangueiras = ["15m", "30m"]
        mangueiras = st.multiselect("Mangueiras de Incêndio", tipos_mangueiras)

        data_cadastro = st.date_input("Data de Cadastro", datetime.today())

        if st.button("Cadastrar Empresa"):
            empresa = {
                "nome": nome_empresa,
                "endereco": endereco,
                "cidade": cidade,
                "telefone": telefone,
                "extintores": extintores_selecionados,
                "mangueiras": mangueiras,
                "usuario": st.session_state["username"],
                "data_cadastro": datetime.combine(data_cadastro, datetime.min.time()),
                "data_vencimento": datetime.combine(data_cadastro, datetime.min.time()) + timedelta(days=365)
            }
            companies_collection.insert_one(empresa)
            st.success("Empresa cadastrada com sucesso!")
            st.rerun()

    elif pagina == "Relatório de Vencimento":
        st.title("Empresas com Extintores a Vencer")
        data_inicio = st.date_input("Data Inicial", datetime.today())
        data_fim = st.date_input("Data Final", datetime.today() + timedelta(days=365))
        cidades_disponiveis = companies_collection.distinct("cidade", {"usuario": st.session_state["username"]})
        cidade_filtro = st.selectbox("Filtrar por Cidade", ["Todas"] + sorted(cidades_disponiveis))

        tipos_extintores_disponiveis = ["ABC", "BC", "CO2", "Água"]
        extintor_filtro = st.selectbox("Filtrar por Tipo de Extintor", ["Todos"] + tipos_extintores_disponiveis)

        filtro = {
            "usuario": st.session_state["username"],
            "data_vencimento": {"$gte": datetime.combine(data_inicio, datetime.min.time()),
                                "$lte": datetime.combine(data_fim, datetime.min.time())}
        }

        if cidade_filtro != "Todas":
            filtro["cidade"] = {"$regex": f"^{cidade_filtro}$", "$options": "i"}

        empresas_vencendo = list(companies_collection.find(filtro))

        if extintor_filtro != "Todos":
            empresas_vencendo = [e for e in empresas_vencendo if
                                 any(ext["tipo"].lower() == extintor_filtro.lower() for ext in e.get("extintores", []))]

        for empresa in empresas_vencendo:
            with st.expander(empresa["nome"]):
                st.write(f"📍 Endereço: {empresa['endereco']}")
                st.write(f"🏙️ Cidade: {empresa['cidade']}")
                st.write(f"📞 Telefone: {empresa['telefone']}")
                extintores_info = ", ".join(
                    [f"{ext['quantidade']}x {ext['capacidade']} {ext['tipo']}" for ext in empresa["extintores"]])
                st.write(f"🧯 Extintores: {extintores_info}")
                st.write(f"🚿 Mangueiras: {', '.join(empresa['mangueiras'])}")
                st.write(f"📅 Cadastro: {empresa['data_cadastro'].strftime('%d/%m/%Y')}")
                st.write(f"⚠️ Vencimento: {empresa['data_vencimento'].strftime('%d/%m/%Y')}")

    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()
