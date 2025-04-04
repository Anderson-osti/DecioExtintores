import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
from fpdf import FPDF

# Autenticação com secrets
MONGO_URL = st.secrets["database"]["url"]
USERS = {
    st.secrets["users"]["USUARIO1"]: st.secrets["users"]["SENHA1"],
    st.secrets["users"]["USUARIO2"]: st.secrets["users"]["SENHA2"]
}

# Conexão com MongoDB
client = MongoClient(MONGO_URL)
db = client["extintores_db"]
companies_collection = db["companies"]

# Autenticação
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

        tipos_extintores = {
            "ABC": ["4kg", "6kg", "10kg"],
            "BC": ["4kg", "6kg", "10kg"],
            "ÁGUA": ["10L", "75L"]
        }

        extintores = []
        for modelo, capacidades in tipos_extintores.items():
            with st.expander(f"{modelo}"):
                for capacidade in capacidades:
                    qtd = st.number_input(f"{modelo} - {capacidade}", min_value=0, step=1, key=f"{modelo}_{capacidade}")
                    if qtd > 0:
                        extintores.append({"modelo": modelo, "capacidade": capacidade, "quantidade": qtd})

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

        busca = st.text_input("Buscar por nome de empresa")
        empresas = list(companies_collection.find({"usuario": st.session_state["username"]}))

        if busca:
            empresas = [e for e in empresas if busca.lower() in e["nome"].lower()]

        nomes = [e["nome"] for e in empresas]
        nome_selecionado = st.selectbox("Selecione uma empresa", [""] + nomes)

        empresa = next((e for e in empresas if e["nome"] == nome_selecionado), None)
        if empresa:
            st.write(f"📍 Endereço: {empresa['endereco']}")
            st.write(f"🏙️ Cidade: {empresa['cidade']}")
            st.write(f"📞 Telefone: {empresa['telefone']}")
            st.write("🧯 Extintores:")
            for ext in empresa["extintores"]:
                st.write(f"• {ext['modelo']} - {ext['capacidade']}: {ext['quantidade']} unidades")
            st.write(f"🚿 Mangueiras: {', '.join(empresa['mangueiras'])}")
            st.write(f"📅 Cadastro: {empresa['data_cadastro'].strftime('%d/%m/%Y')}")
            st.write(f"⚠️ Vencimento: {empresa['data_vencimento'].strftime('%d/%m/%Y')}")

            if st.button("Excluir Empresa"):
                companies_collection.delete_one({"_id": empresa["_id"]})
                st.success("Empresa excluída com sucesso.")
                st.rerun()

    elif pagina == "Relatório de Vencimento":
        st.title("Relatório de Vencimento de Extintores")

        data_inicio = st.date_input("Data início", datetime.now().date())
        data_fim = st.date_input("Data fim", (datetime.now() + timedelta(days=365)).date())

        cidades = companies_collection.distinct("cidade", {"usuario": st.session_state["username"]})
        cidade_filtro = st.selectbox("Filtrar por Cidade", ["Todas"] + sorted(cidades))

        tipos_extintores = ["ABC", "BC", "ÁGUA"]
        tipo_filtro = st.selectbox("Filtrar por Tipo de Extintor", ["Todos"] + tipos_extintores)

        filtro = {
            "usuario": st.session_state["username"],
            "data_vencimento": {
                "$gte": datetime.combine(data_inicio, datetime.min.time()),
                "$lte": datetime.combine(data_fim, datetime.max.time())
            }
        }

        if cidade_filtro != "Todas":
            filtro["cidade"] = cidade_filtro

        empresas = list(companies_collection.find(filtro))

        if tipo_filtro != "Todos":
            empresas = [e for e in empresas if any(ext["modelo"].lower() == tipo_filtro.lower() for ext in e["extintores"])]

        for empresa in empresas:
            with st.expander(empresa["nome"]):
                st.write(f"🏙️ Cidade: {empresa['cidade']}")
                st.write(f"📞 Telefone: {empresa['telefone']}")
                for ext in empresa["extintores"]:
                    st.write(f"🧯 {ext['modelo']} - {ext['capacidade']}: {ext['quantidade']} un")
                st.write(f"🚿 Mangueiras: {', '.join(empresa['mangueiras'])}")
                st.write(f"📅 Cadastro: {empresa['data_cadastro'].strftime('%d/%m/%Y')}")
                st.write(f"⚠️ Vencimento: {empresa['data_vencimento'].strftime('%d/%m/%Y')}")

        if st.button("Baixar PDF"):
            pdf = FPDF(orientation="P", unit="mm", format="A4")
            pdf.add_page()
            pdf.set_font("Arial", size=10)
            pdf.cell(200, 10, txt="Relatório de Vencimento", ln=True, align="C")
            pdf.ln(5)

            for emp in empresas:
                pdf.set_font("Arial", style="B", size=10)
                pdf.cell(200, 6, f"{emp['nome']} - {emp['cidade']}", ln=True)
                pdf.set_font("Arial", size=9)
                pdf.cell(200, 5, f"Telefone: {emp['telefone']} | Cadastro: {emp['data_cadastro'].strftime('%d/%m/%Y')} | Vencimento: {emp['data_vencimento'].strftime('%d/%m/%Y')}", ln=True)
                for ext in emp["extintores"]:
                    pdf.cell(200, 5, f" - {ext['modelo']} {ext['capacidade']}: {ext['quantidade']} un", ln=True)
                pdf.cell(200, 5, f"Mangueiras: {', '.join(emp['mangueiras'])}", ln=True)
                pdf.ln(4)

            st.download_button("📥 Baixar PDF", data=pdf.output(dest="S").encode("latin-1"), file_name="relatorio_vencimentos.pdf")

    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()
