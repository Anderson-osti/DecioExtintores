import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
from fpdf import FPDF
import io

# Conectar ao banco
MONGO_URL = st.secrets["database"]["url"]
client = MongoClient(MONGO_URL)
db = client["extintores_db"]
companies_collection = db["companies"]

# Usuários
USERS = {
    st.secrets["users"]["USUARIO1"]: st.secrets["users"]["SENHA1"],
    st.secrets["users"]["USUARIO2"]: st.secrets["users"]["SENHA2"]
}


# Autenticação
def authenticate(username, password):
    return USERS.get(username) == password


# LOGIN
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

# PÓS LOGIN
if st.session_state.get("logged_in"):
    st.sidebar.title("Navegação")
    pagina = st.sidebar.radio("Ir para", ["Cadastro de Empresa", "Empresas Cadastradas", "Relatório de Vencimento"])

    # Cadastro
    if pagina == "Cadastro de Empresa":
        st.title("Cadastro de Empresa")
        nome_empresa = st.text_input("Nome da Empresa")
        endereco = st.text_area("Endereço Completo")
        cidade = st.text_input("Cidade")
        telefone = st.text_input("Telefone")
        data_manual = st.date_input("Data do Cadastro", datetime.now().date())

        st.subheader("Extintores")
        tipos_modelos = {
            "Pó ABC": ["4kg", "6kg", "10kg"],
            "Pó BC": ["4kg", "6kg", "10kg"],
            "CO2": ["6kg", "10kg"],
            "Água": ["10L", "75L"]
        }

        extintores = []
        for tipo, modelos in tipos_modelos.items():
            for modelo in modelos:
                col1, col2 = st.columns([3, 1])
                with col1:
                    qtd = col1.number_input(f"{tipo} - {modelo}", min_value=0, step=1, key=f"{tipo}_{modelo}")
                if qtd > 0:
                    extintores.append({"tipo": tipo, "modelo": modelo, "quantidade": qtd})

        st.subheader("Mangueiras de Incêndio")
        mang15 = st.number_input("Mangueiras 15m", min_value=0, step=1)
        mang30 = st.number_input("Mangueiras 30m", min_value=0, step=1)
        mangueiras = []
        if mang15 > 0:
            mangueiras.append({"tamanho": "15m", "quantidade": mang15})
        if mang30 > 0:
            mangueiras.append({"tamanho": "30m", "quantidade": mang30})

        if st.button("Cadastrar Empresa"):
            data_cadastro = datetime.combine(data_manual, datetime.min.time())
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

    # Empresas cadastradas
    elif pagina == "Empresas Cadastradas":
        st.title("Empresas Cadastradas")
        empresas = list(companies_collection.find({"usuario": st.session_state["username"]}))
        nomes_empresas = [e["nome"] for e in empresas]
        busca = st.selectbox("Buscar empresa", [""] + nomes_empresas)

        empresa_sel = next((e for e in empresas if e["nome"] == busca), None)
        if empresa_sel:
            st.write(f"📍 **Endereço:** {empresa_sel['endereco']}")
            st.write(f"🏙️ **Cidade:** {empresa_sel['cidade']}")
            st.write(f"📞 **Telefone:** {empresa_sel['telefone']}")
            st.write("🧯 **Extintores:**")
            for ext in empresa_sel["extintores"]:
                st.write(f"- {ext['tipo']} {ext['modelo']} – {ext['quantidade']} un")
            st.write("🚿 **Mangueiras:**")
            for m in empresa_sel["mangueiras"]:
                st.write(f"- {m['tamanho']} – {m['quantidade']} un")
            st.write(f"📅 **Cadastro:** {empresa_sel['data_cadastro'].strftime('%d/%m/%Y')}")

            if st.button("Excluir Empresa"):
                companies_collection.delete_one({"_id": empresa_sel["_id"]})
                st.success("Empresa excluída!")
                st.rerun()

    # Relatório
    elif pagina == "Relatório de Vencimento":
        st.title("Relatório de Vencimento")

        data_ref = st.date_input("Verificar vencimentos até", datetime.now().date() + timedelta(days=365))
        cidade_opcoes = companies_collection.distinct("cidade", {"usuario": st.session_state["username"]})
        cidade = st.selectbox("Filtrar por cidade", ["Todas"] + sorted(cidade_opcoes))

        tipo_filtro = st.text_input("Filtrar por modelo ou tipo de extintor (opcional)").strip().lower()

        filtro = {"usuario": st.session_state["username"]}
        if cidade != "Todas":
            filtro["cidade"] = {"$regex": f"^{cidade}$", "$options": "i"}

        empresas = list(companies_collection.find(filtro))
        empresas_venc = []

        for emp in empresas:
            data_cad = emp.get("data_cadastro")
            if data_cad and data_cad + timedelta(days=365) <= datetime.combine(data_ref, datetime.min.time()):
                if tipo_filtro:
                    if any(tipo_filtro in e["tipo"].lower() or tipo_filtro in e["modelo"].lower() for e in emp["extintores"]):
                        empresas_venc.append(emp)
                else:
                    empresas_venc.append(emp)

        for emp in empresas_venc:
            with st.expander("📋 Empresa com vencimento próximo"):
                st.write("📍 Endereço:", emp["endereco"])
                st.write("🏙️ Cidade:", emp["cidade"])
                st.write("📞 Telefone:", emp["telefone"])
                st.write("🧯 Extintores:")
                for e in emp["extintores"]:
                    st.write(f"- {e['tipo']} {e['modelo']} – {e['quantidade']} un")
                st.write("🚿 Mangueiras:")
                for m in emp["mangueiras"]:
                    st.write(f"- {m['tamanho']} – {m['quantidade']} un")
                st.write(f"📅 Cadastro: {emp['data_cadastro'].strftime('%d/%m/%Y')}")
                st.write(f"⚠️ Vencimento: {(emp['data_cadastro'] + timedelta(days=365)).strftime('%d/%m/%Y')}")

        # PDF
        if st.button("Baixar PDF"):
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=10)
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Relatório de Vencimento", ln=True, align="C")
            pdf.ln(5)

            for emp in empresas_venc:
                pdf.set_font("Arial", "B", 12)
                pdf.cell(0, 10, emp["nome"], ln=True)
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 6, f"Endereço: {emp['endereco']}", ln=True)
                pdf.cell(0, 6, f"Cidade: {emp['cidade']} | Telefone: {emp['telefone']}", ln=True)
                pdf.cell(0, 6, f"Cadastro: {emp['data_cadastro'].strftime('%d/%m/%Y')}", ln=True)
                pdf.cell(0, 6, f"Vencimento: {(emp['data_cadastro'] + timedelta(days=365)).strftime('%d/%m/%Y')}", ln=True)

                pdf.cell(0, 6, "Extintores:", ln=True)
                for e in emp["extintores"]:
                    pdf.cell(0, 6, f"- {e['tipo']} {e['modelo']} – {e['quantidade']} un", ln=True)

                if emp["mangueiras"]:
                    pdf.cell(0, 6, "Mangueiras:", ln=True)
                    for m in emp["mangueiras"]:
                        pdf.cell(0, 6, f"- {m['tamanho']} – {m['quantidade']} un", ln=True)

                pdf.ln(5)

            buffer = io.BytesIO()
            pdf.output(buffer)
            st.download_button("📥 Baixar PDF", buffer.getvalue(), file_name="relatorio_vencimento.pdf")

    # Sair
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()
