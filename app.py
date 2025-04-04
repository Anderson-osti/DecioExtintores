import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from fpdf import FPDF

# Conexão com MongoDB via secrets
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


# PDF
class PDF(FPDF):
    def header(self):
        self.set_font("Arial", "B", 12)
        self.cell(0, 10, "Relatório de Vencimentos", ln=True, align="C")
        self.ln(5)

    def company_info(self, empresa):
        self.set_font("Arial", "", 10)
        self.cell(0, 5, f"Empresa: {empresa['nome']}", ln=True)
        self.cell(0, 5, f"Cidade: {empresa['cidade']} | Telefone: {empresa['telefone']}", ln=True)
        self.cell(0, 5, f"Endereço: {empresa['endereco']}", ln=True)
        self.cell(0, 5, f"Cadastro: {empresa['data_cadastro'].strftime('%d/%m/%Y')}"
                        f" | Vencimento: {empresa['data_vencimento'].strftime('%d/%m/%Y')}", ln=True)
        extintores_lista = [f"{e['tipo']} - {e['quantidade']}x" for e in empresa.get('extintores', [])]
        self.cell(0, 5, f"Extintores: {', '.join(extintores_lista)}", ln=True)
        self.cell(0, 5, f"Mangueiras: {', '.join(empresa.get('mangueiras', []))}", ln=True)
        self.ln(4)


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
        # CADASTRO - NÃO ALTERADO, conforme solicitado
        st.title("Cadastro de Empresa")
        nome_empresa = st.text_input("Nome da Empresa")
        endereco = st.text_area("Endereço Completo")
        cidade = st.text_input("Cidade")
        telefone = st.text_input("Telefone")

        tipos_extintores = ["ABC", "BC", "ÁGUA"]
        capacidade_opcoes = {
            "ABC": ["4kg", "6kg", "10kg"],
            "BC": ["4kg", "6kg", "10kg"],
            "ÁGUA": ["10L", "75L"]
        }

        extintores = []
        tipo = st.selectbox("Tipo de Extintor", tipos_extintores)
        capacidade = st.selectbox("Capacidade", capacidade_opcoes[tipo])
        quantidade = st.number_input("Quantidade", min_value=1, step=1)

        if "extintores_temp" not in st.session_state:
            st.session_state["extintores_temp"] = []

        if st.button("Adicionar Extintor"):
            st.session_state["extintores_temp"].append({
                "tipo": f"{tipo} {capacidade}",
                "quantidade": quantidade
            })

        if st.session_state["extintores_temp"]:
            st.subheader("Extintores Adicionados")
            for i, e in enumerate(st.session_state["extintores_temp"]):
                st.write(f"{e['quantidade']}x {e['tipo']}")
                if st.button("Remover", key=f"remover_{i}"):
                    st.session_state["extintores_temp"].pop(i)
                    st.rerun()

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
                "extintores": st.session_state["extintores_temp"],
                "mangueiras": mangueiras,
                "usuario": st.session_state["username"],
                "data_cadastro": data_cadastro,
                "data_vencimento": data_vencimento
            }

            companies_collection.insert_one(empresa)
            st.session_state["extintores_temp"] = []
            st.success("Empresa cadastrada com sucesso!")
            st.rerun()

    elif pagina == "Empresas Cadastradas":
        st.title("Empresas Cadastradas")
        busca = st.text_input("Buscar Empresa")

        empresas = list(companies_collection.find({"usuario": st.session_state["username"]}))
        empresas_filtradas = [e for e in empresas if busca.lower() in e["nome"].lower()] if busca else empresas

        nomes_empresas = [e["nome"] for e in empresas_filtradas]
        selecionada = st.selectbox("Selecionar Empresa", [""] + nomes_empresas)

        if selecionada:
            empresa = next(e for e in empresas_filtradas if e["nome"] == selecionada)
            st.subheader(f"Empresa: {empresa['nome']}")
            st.write(f"📍 {empresa['endereco']}")
            st.write(f"🏙️ {empresa['cidade']}")
            st.write(f"📞 {empresa['telefone']}")
            st.write(f"🧯 Extintores:")
            for e in empresa["extintores"]:
                st.write(f"• {e['quantidade']}x {e['tipo']}")
            st.write(f"🚿 Mangueiras: {', '.join(empresa.get('mangueiras', []))}")
            st.write(f"📅 Cadastro: {empresa['data_cadastro'].strftime('%d/%m/%Y')}")
            st.write(f"⚠️ Vencimento: {empresa['data_vencimento'].strftime('%d/%m/%Y')}")
            if st.button("Excluir Empresa"):
                companies_collection.delete_one({"_id": empresa["_id"]})
                st.success("Empresa excluída com sucesso.")
                st.rerun()

    elif pagina == "Relatório de Vencimento":
        st.title("Relatório de Vencimento")

        data_inicio = st.date_input("Data inicial", datetime.now())
        data_fim = st.date_input("Data final", datetime.now() + timedelta(days=365))

        filtro = {
            "usuario": st.session_state["username"],
            "data_vencimento": {
                "$gte": datetime.combine(data_inicio, datetime.min.time()),
                "$lte": datetime.combine(data_fim, datetime.max.time())
            }
        }

        empresas = list(companies_collection.find(filtro))

        st.write(f"Empresas encontradas: {len(empresas)}")
        if st.button("Baixar PDF"):
            pdf = PDF()
            pdf.add_page()
            for empresa in empresas:
                pdf.company_info(empresa)
            pdf_file = "relatorio_vencimento.pdf"
            pdf.output(pdf_file)
            with open(pdf_file, "rb") as f:
                st.download_button("📄 Download do PDF", f, file_name=pdf_file)

    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()
