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
        data_cadastro = st.date_input("Data de Cadastro", datetime.today())

        tipos_extintores = {
            "ABC": ["4kg", "6kg", "10kg"],
            "BC": ["4kg", "6kg", "10kg"],
            "CO2": ["4kg", "6kg", "10kg"],
            "ÁGUA": ["10L", "75L"]
        }

        extintores = []
        for tipo, capacidades in tipos_extintores.items():
            with st.expander(f"Extintores {tipo}"):
                for capacidade in capacidades:
                    quantidade = st.number_input(f"Quantidade {capacidade}", min_value=0, step=1,
                                                 key=f"{tipo}_{capacidade}")
                    if quantidade > 0:
                        extintores.append({"tipo": tipo, "capacidade": capacidade, "quantidade": quantidade})

        tipos_mangueiras = ["15m", "30m"]
        mangueiras = st.multiselect("Mangueiras de Incêndio", tipos_mangueiras)

        if st.button("Cadastrar Empresa"):
            data_vencimento = datetime.combine(data_cadastro, datetime.min.time()) + timedelta(days=365)
            empresa = {
                "nome": nome_empresa,
                "endereco": endereco,
                "cidade": cidade,
                "telefone": telefone,
                "extintores": extintores,
                "mangueiras": mangueiras,
                "usuario": st.session_state["username"],
                "data_cadastro": data_cadastro.strftime('%Y-%m-%d'),
                "data_vencimento": data_vencimento.strftime('%Y-%m-%d')
            }

            companies_collection.insert_one(empresa)
            st.success("Empresa cadastrada com sucesso!")
            st.rerun()

    elif pagina == "Empresas Cadastradas":
        st.title("Empresas Cadastradas")
        empresas = list(companies_collection.find({"usuario": st.session_state["username"]}))
        nomes_empresas = [empresa["nome"] for empresa in empresas]

        empresa_selecionada = st.selectbox("Buscar Empresa", [""] + nomes_empresas)

        if empresa_selecionada:
            empresa = next(e for e in empresas if e["nome"] == empresa_selecionada)
            st.write(f"📍 Endereço: {empresa['endereco']}")
            st.write(f"🏙️ Cidade: {empresa['cidade']}")
            st.write(f"📞 Telefone: {empresa['telefone']}")
            st.write("🧯 Extintores:")
            for extintor in empresa["extintores"]:
                st.write(f"- {extintor['tipo']} {extintor['capacidade']} ({extintor['quantidade']} unidades)")
            st.write(f"🚿 Mangueiras: {', '.join(empresa['mangueiras'])}")
            st.write(f"📅 Cadastro: {empresa['data_cadastro']}")
            st.write(f"⚠️ Vencimento: {empresa['data_vencimento']}")

    elif pagina == "Relatório de Vencimento":
        st.title("Empresas com Extintores a Vencer")
        cidades_disponiveis = companies_collection.distinct("cidade", {"usuario": st.session_state["username"]})
        cidade_filtro = st.selectbox("Filtrar por Cidade", ["Todas"] + sorted(cidades_disponiveis))
        empresas_vencendo = companies_collection.find({"usuario": st.session_state["username"]})

        if cidade_filtro != "Todas":
            empresas_vencendo = filter(lambda e: e["cidade"].lower() == cidade_filtro.lower(), empresas_vencendo)

        for empresa in empresas_vencendo:
            with st.expander(empresa["nome"]):
                st.write(f"📍 Endereço: {empresa['endereco']}")
                st.write(f"🏙️ Cidade: {empresa['cidade']}")
                st.write(f"📞 Telefone: {empresa['telefone']}")
                st.write("🧯 Extintores:")
                for extintor in empresa["extintores"]:
                    st.write(f"- {extintor['tipo']} {extintor['capacidade']} ({extintor['quantidade']} unidades)")
                st.write(f"🚿 Mangueiras: {', '.join(empresa['mangueiras'])}")
                st.write(f"📅 Cadastro: {empresa['data_cadastro']}")
                st.write(f"⚠️ Vencimento: {empresa['data_vencimento']}")

    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()
