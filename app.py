import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from fpdf import FPDF


# Conexão com o MongoDB
MONGO_URL = st.secrets["database"]["url"]
client = MongoClient(MONGO_URL)
db = client["extintores_db"]
companies_collection = db["companies"]

# Autenticação
USERS = {
    st.secrets["users"]["USUARIO1"]: st.secrets["users"]["SENHA1"],
    st.secrets["users"]["USUARIO2"]: st.secrets["users"]["SENHA2"]
}


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
        # Tela de cadastro (mantida conforme pedido)
        st.title("Cadastro de Empresa")
        nome_empresa = st.text_input("Nome da Empresa")
        endereco = st.text_area("Endereço Completo")
        cidade = st.text_input("Cidade")
        telefone = st.text_input("Telefone")
        tipos_extintores = ["ABC 4kg", "ABC 6kg", "ABC 10kg", "BC 4kg", "BC 6kg", "CO2 6kg", "ÁGUA 10L", "ÁGUA 75L"]
        extintores = st.multiselect("Modelos de Extintores", tipos_extintores)
        tipos_mangueiras = ["15m", "30m"]
        mangueiras = st.multiselect("Mangueiras de Incêndio", tipos_mangueiras)

        if st.button("Cadastrar Empresa"):
            data_cadastro = datetime.now()
            empresa = {
                "nome": nome_empresa,
                "endereco": endereco,
                "cidade": cidade,
                "telefone": telefone,
                "extintores": extintores,
                "mangueiras": mangueiras,
                "usuario": st.session_state["username"],
                "data_cadastro": data_cadastro
            }
            companies_collection.insert_one(empresa)
            st.success("Empresa cadastrada com sucesso!")
            st.rerun()

    elif pagina == "Empresas Cadastradas":
        st.title("Empresas Cadastradas")
        busca = st.text_input("Buscar por nome").lower()
        empresas = companies_collection.find({"usuario": st.session_state["username"]})

        nomes = [e["nome"] for e in empresas]
        empresas = companies_collection.find({"usuario": st.session_state["username"]})
        nomes_filtrados = [e["nome"] for e in empresas if busca in e["nome"].lower()]

        nome_selecionado = st.selectbox("Selecione uma empresa", nomes_filtrados if busca else nomes)

        if nome_selecionado:
            empresa = companies_collection.find_one({
                "nome": nome_selecionado,
                "usuario": st.session_state["username"]
            })

            if empresa:
                st.write(f"📍 Endereço: {empresa['endereco']}")
                st.write(f"🏙️ Cidade: {empresa['cidade']}")
                st.write(f"📞 Telefone: {empresa['telefone']}")
                st.write(f"🧯 Extintores: {', '.join(empresa['extintores'])}")
                st.write(f"🚿 Mangueiras: {', '.join(empresa['mangueiras'])}")
                st.write(f"📅 Cadastro: {empresa['data_cadastro'].strftime('%d/%m/%Y')}")

                if st.button("Excluir Empresa"):
                    companies_collection.delete_one({"_id": empresa["_id"]})
                    st.success("Empresa excluída com sucesso.")
                    st.rerun()

    elif pagina == "Relatório de Vencimento":
        st.title("Relatório de Vencimento")

        cidades = companies_collection.distinct("cidade", {"usuario": st.session_state["username"]})
        tipos = ["ABC 4kg", "ABC 6kg", "ABC 10kg", "BC 4kg", "BC 6kg", "CO2 6kg", "ÁGUA 10L", "ÁGUA 75L"]

        cidade_filtro = st.selectbox("Filtrar por cidade", ["Todas"] + sorted(cidades))
        tipo_filtro = st.selectbox("Filtrar por tipo de extintor", ["Todos"] + tipos)

        data_inicio = st.date_input("Data início", datetime.today())
        data_fim = st.date_input("Data fim", datetime.today() + timedelta(days=365))

        filtro = {
            "usuario": st.session_state["username"],
            "data_cadastro": {
                "$gte": datetime.combine(data_inicio, datetime.min.time()),
                "$lte": datetime.combine(data_fim, datetime.max.time())
            }
        }

        if cidade_filtro != "Todas":
            filtro["cidade"] = {"$regex": f"^{cidade_filtro}$", "$options": "i"}

        empresas = list(companies_collection.find(filtro))

        if tipo_filtro != "Todos":
            empresas = [e for e in empresas if tipo_filtro in e["extintores"]]

        st.subheader("Empresas encontradas:")
        st.write(f"Total: {len(empresas)}")

        def gerar_pdf(empresas):
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=10)
            pdf.add_page()
            pdf.set_font("Arial", "B", 12)
            pdf.cell(190, 10, "Relatório de Vencimento", ln=True, align="C")
            pdf.ln(5)

            for emp in empresas:
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 8, f"Empresa: {emp['nome']}", ln=True)
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 6, f"Endereço: {emp['endereco']}", ln=True)
                pdf.cell(0, 6, f"Cidade: {emp['cidade']} | Telefone: {emp['telefone']}", ln=True)
                pdf.cell(0, 6, f"Cadastro: {emp['data_cadastro'].strftime('%d/%m/%Y')}", ln=True)
                if "extintores" in emp:
                    pdf.multi_cell(0, 6, f"Extintores: {', '.join(emp['extintores'])}")
                if "mangueiras" in emp:
                    pdf.multi_cell(0, 6, f"Mangueiras: {', '.join(emp['mangueiras'])}")
                pdf.ln(4)

            return pdf.output(dest='S').encode('latin1')

        if st.button("Baixar Relatório em PDF"):
            pdf_data = gerar_pdf(empresas)
            st.download_button("Clique aqui para baixar", data=pdf_data, file_name="relatorio_vencimento.pdf",
                               mime="application/pdf")

    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()
