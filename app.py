import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from fpdf import FPDF

# Conectar com o MongoDB
MONGO_URL = st.secrets["database"]["url"]
USERS = {
    st.secrets["users"]["USUARIO1"]: st.secrets["users"]["SENHA1"],
    st.secrets["users"]["USUARIO2"]: st.secrets["users"]["SENHA2"]
}

client = MongoClient(MONGO_URL)
db = client["extintores_db"]
companies_collection = db["companies"]


# Autenticação
def authenticate(username, password):
    return USERS.get(username) == password


# Login
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
        nome = st.text_input("Nome da Empresa")
        endereco = st.text_area("Endereço Completo")
        cidade = st.text_input("Cidade")
        telefone = st.text_input("Telefone")
        data_manual = st.date_input("Data do Cadastro", value=datetime.today())

        tipos_modelos = {
            "ABC": ["4kg", "6kg", "10kg"],
            "BC": ["4kg", "6kg", "10kg"],
            "ÁGUA": ["10L", "75L"]
        }

        extintores = []
        for modelo, capacidades in tipos_modelos.items():
            with st.expander(f"{modelo}"):
                for cap in capacidades:
                    qnt = st.number_input(f"{modelo} {cap}", min_value=0, step=1, key=f"{modelo}_{cap}")
                    if qnt > 0:
                        extintores.append({"modelo": modelo, "capacidade": cap, "quantidade": qnt})

        tipos_mangueiras = ["15m", "30m"]
        mangueiras = {}
        for tipo in tipos_mangueiras:
            qnt = st.number_input(f"Mangueiras {tipo}", min_value=0, step=1, key=f"m_{tipo}")
            if qnt > 0:
                mangueiras[tipo] = qnt

        if st.button("Cadastrar Empresa"):
            empresa = {
                "nome": nome,
                "endereco": endereco,
                "cidade": cidade,
                "telefone": telefone,
                "extintores": extintores,
                "mangueiras": mangueiras,
                "usuario": st.session_state["username"],
                "data_cadastro": datetime.combine(data_manual, datetime.min.time()),
            }
            empresa["data_vencimento"] = empresa["data_cadastro"] + timedelta(days=365)
            companies_collection.insert_one(empresa)
            st.success("Empresa cadastrada com sucesso!")
            st.rerun()

    elif pagina == "Empresas Cadastradas":
        st.title("Empresas Cadastradas")
        busca = st.text_input("Buscar Empresa")
        empresas = list(companies_collection.find({"usuario": st.session_state["username"]}))
        if busca:
            empresas = [e for e in empresas if busca.lower() in e["nome"].lower()]

        nomes_empresas = [e["nome"] for e in empresas]
        empresa_selecionada = st.selectbox("Selecionar Empresa", [""] + nomes_empresas)

        if empresa_selecionada:
            empresa = next((e for e in empresas if e["nome"] == empresa_selecionada), None)
            if empresa:
                st.subheader("Informações")
                st.write(f"📍 Endereço: {empresa['endereco']}")
                st.write(f"🏙️ Cidade: {empresa['cidade']}")
                st.write(f"📞 Telefone: {empresa['telefone']}")
                st.write(f"📅 Cadastro: {empresa['data_cadastro'].strftime('%d/%m/%Y')}")
                st.write(f"⚠️ Vencimento: {empresa['data_vencimento'].strftime('%d/%m/%Y')}")

                st.subheader("Extintores")
                for ext in empresa["extintores"]:
                    st.write(f"- {ext['modelo']} {ext['capacidade']} - {ext['quantidade']} unidade(s)")

                st.subheader("Mangueiras")
                for tipo, qnt in empresa["mangueiras"].items():
                    st.write(f"- {tipo}: {qnt} unidade(s)")

                if st.button("Excluir Empresa"):
                    companies_collection.delete_one({"_id": ObjectId(empresa["_id"])})
                    st.success("Empresa excluída com sucesso.")
                    st.rerun()

    elif pagina == "Relatório de Vencimento":
        st.title("Relatório de Vencimento")

        data_inicio = st.date_input("De", datetime.today())
        data_fim = st.date_input("Até", datetime.today() + timedelta(days=30))

        filtro = {
            "usuario": st.session_state["username"],
            "data_vencimento": {
                "$gte": datetime.combine(data_inicio, datetime.min.time()),
                "$lte": datetime.combine(data_fim, datetime.max.time())
            }
        }

        empresas = list(companies_collection.find(filtro))

        for empresa in empresas:
            with st.expander(empresa["nome"]):
                st.write(f"📍 Endereço: {empresa['endereco']}")
                st.write(f"🏙️ Cidade: {empresa['cidade']}")
                st.write(f"📞 Telefone: {empresa['telefone']}")
                st.write(f"📅 Cadastro: {empresa['data_cadastro'].strftime('%d/%m/%Y')}")
                st.write(f"⚠️ Vencimento: {empresa['data_vencimento'].strftime('%d/%m/%Y')}")
                st.write("🧯 Extintores:")
                for ext in empresa["extintores"]:
                    st.write(f"  - {ext['modelo']} {ext['capacidade']} ({ext['quantidade']} un)")
                st.write("🚿 Mangueiras:")
                for tipo, qnt in empresa["mangueiras"].items():
                    st.write(f"  - {tipo}: {qnt} un")

        # Gerar PDF
        if st.button("Baixar Relatório em PDF"):
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=10)
            pdf.add_page()
            pdf.set_font("Arial", size=10)

            for empresa in empresas:
                pdf.set_font("Arial", "B", 11)
                pdf.cell(0, 8, empresa["nome"], ln=True)
                pdf.set_font("Arial", size=10)
                pdf.cell(0, 6, f"Endereço: {empresa['endereco']}", ln=True)
                pdf.cell(0, 6, f"Cidade: {empresa['cidade']} - Telefone: {empresa['telefone']}", ln=True)
                pdf.cell(0, 6,
                         f"Cadastro: {empresa['data_cadastro'].strftime('%d/%m/%Y')} | Venc: {empresa['data_vencimento'].strftime('%d/%m/%Y')}",
                         ln=True)

                pdf.cell(0, 6, "Extintores:", ln=True)
                for ext in empresa["extintores"]:
                    pdf.cell(0, 6, f"  - {ext['modelo']} {ext['capacidade']}: {ext['quantidade']} un", ln=True)

                pdf.cell(0, 6, "Mangueiras:", ln=True)
                for tipo, qnt in empresa["mangueiras"].items():
                    pdf.cell(0, 6, f"  - {tipo}: {qnt} un", ln=True)

                pdf.ln(4)

            st.download_button(
                label="📄 Download do PDF",
                data=pdf.output(dest="S").encode("latin-1"),
                file_name="relatorio_vencimento.pdf",
                mime="application/pdf"
            )

    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()
