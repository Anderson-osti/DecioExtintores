import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson import ObjectId

# Conectar ao MongoDB
MONGO_URL = st.secrets["database"]["url"]
client = MongoClient(MONGO_URL)
db = client["extintores_db"]
companies_collection = db["companies"]

# Usuários do sistema
USERS = {
    st.secrets["users"]["USUARIO1"].lower(): st.secrets["users"]["SENHA1"],
    st.secrets["users"]["USUARIO2"].lower(): st.secrets["users"]["SENHA2"]
}

# Autenticação
if "logged_in" not in st.session_state:
    st.title("Login")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if USERS.get(username.lower()) == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username.lower()
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
        data_manual = st.date_input("Data do Cadastro", datetime.today())

        st.subheader("Extintores")
        if "extintores" not in st.session_state:
            st.session_state.extintores = []

        tipo = st.selectbox("Tipo de Extintor", ["ABC", "BC", "CO2", "Água"])
        modelo = st.selectbox("Modelo/Capacidade", ["4kg", "6kg", "10kg", "10L", "75L"])
        quantidade = st.number_input("Quantidade", min_value=1, step=1)

        if st.button("Adicionar Extintor"):
            st.session_state.extintores.append({
                "tipo": tipo,
                "modelo": modelo,
                "quantidade": quantidade
            })

        for i, ext in enumerate(st.session_state.extintores):
            st.write(f"{i+1}. Tipo: {ext['tipo']} | Modelo: {ext['modelo']} | Quantidade: {ext['quantidade']}")

        st.subheader("Mangueiras")
        tipos_mangueiras = ["15m", "30m"]
        mangueiras = st.multiselect("Mangueiras de Incêndio", tipos_mangueiras)

        if st.button("Cadastrar Empresa"):
            empresa = {
                "nome": nome_empresa,
                "endereco": endereco,
                "cidade": cidade,
                "telefone": telefone,
                "extintores": st.session_state.extintores,
                "mangueiras": mangueiras,
                "usuario": st.session_state["username"],
                "data_cadastro": datetime.combine(data_manual, datetime.min.time())
            }
            companies_collection.insert_one(empresa)
            st.success("Empresa cadastrada com sucesso!")
            st.session_state.extintores = []
            st.rerun()

    elif pagina == "Empresas Cadastradas":
        st.title("Empresas Cadastradas")
        busca = st.text_input("Buscar empresa")
        empresas = list(companies_collection.find({"usuario": st.session_state["username"]}))

        empresas_filtradas = [e for e in empresas if busca.lower() in e["nome"].lower()] if busca else empresas

        nomes_empresas = [e["nome"] for e in empresas_filtradas]
        selecionada = st.selectbox("Selecionar Empresa", ["Selecione"] + nomes_empresas)

        for empresa in empresas_filtradas:
            if empresa["nome"] == selecionada:
                st.write(f"📍 Endereço: {empresa['endereco']}")
                st.write(f"🏙️ Cidade: {empresa['cidade']}")
                st.write(f"📞 Telefone: {empresa['telefone']}")
                st.write("🧯 Extintores:")
                for ext in empresa["extintores"]:
                    st.write(f"- {ext['quantidade']}x {ext['tipo']} - {ext['modelo']}")
                st.write(f"🚿 Mangueiras: {', '.join(empresa['mangueiras']) if empresa['mangueiras'] else 'Nenhuma'}")
                st.write(f"📅 Cadastro: {empresa['data_cadastro'].strftime('%d/%m/%Y')}")

                if st.button("Excluir Empresa"):
                    companies_collection.delete_one({"_id": ObjectId(empresa["_id"])})
                    st.success("Empresa excluída!")
                    st.rerun()

    elif pagina == "Relatório de Vencimento":
        st.title("Relatório de Vencimento")

        data_referencia = st.date_input("Selecionar data de referência", datetime.today())
        limite = datetime.combine(data_referencia, datetime.min.time()) + timedelta(days=365)

        empresas = list(companies_collection.find({"usuario": st.session_state["username"]}))

        empresas_venc = [e for e in empresas if e["data_cadastro"] + timedelta(days=365) <= limite]

        tipo_filtro = st.text_input("Filtrar por Tipo/Modelo de Extintor")

        if tipo_filtro:
            tipo_filtro = tipo_filtro.lower()
            empresas_venc = [e for e in empresas_venc if any(tipo_filtro in (ext["tipo"] + ext["modelo"]).lower()
                                                             for ext in e["extintores"])]

        for empresa in empresas_venc:
            st.markdown("---")
            st.write(f"📍 Endereço: {empresa['endereco']}")
            st.write(f"🏙️ Cidade: {empresa['cidade']}")
            st.write(f"📞 Telefone: {empresa['telefone']}")
            st.write("🧯 Extintores:")
            for ext in empresa["extintores"]:
                st.write(f"- {ext['quantidade']}x {ext['tipo']} - {ext['modelo']}")
            st.write(f"📅 Cadastro: {empresa['data_cadastro'].strftime('%d/%m/%Y')}")
            st.write(f"⚠️ Vencimento: {(empresa['data_cadastro'] + timedelta(days=365)).strftime('%d/%m/%Y')}")

    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()
