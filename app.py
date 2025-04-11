import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
from fpdf import FPDF

# Conectar ao MongoDB
client = MongoClient(st.secrets["mongo"]["url"])
db = client["sistema_extintores"]
users_collection = db["usuarios"]
companies_collection = db["empresas"]

# Autenticação
def autenticar_usuario(username, senha):
    usuario = users_collection.find_one({"usuario": {"$regex": f"^{username}$", "$options": "i"}})
    if usuario and usuario["senha"] == senha:
        return usuario
    return None

# Tela de login
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Login")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        usuario = autenticar_usuario(username, password)
        if usuario:
            st.session_state.logged_in = True
            st.session_state.usuario_logado = usuario["usuario"]
            st.success("Login realizado com sucesso!")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

# Aplicação
if st.session_state.get("logged_in"):
    st.sidebar.title("Navegação")
    pagina_selecionada = st.sidebar.radio("Ir para", ["Cadastro de Empresa",
                                                      "Empresas Cadastradas", "Relatório de Vencimento"])

    if pagina_selecionada == "Cadastro de Empresa":
        st.title("Cadastro de Empresa")
        nome_empresa = st.text_input("Nome da empresa")
        endereco = st.text_input("Endereço")
        cidade = st.text_input("Cidade")
        telefone = st.text_input("Telefone")
        data_cadastro = st.date_input("Data de cadastro", value=datetime.today())
        st.subheader("Cadastro de Extintores")
        tipos_extintores = ["ABC", "BC", "CO2", "ÁGUA"]
        capacidades_extintores = ["1kg", "4kg", "6kg", "8kg", "10kg", "12kg", "20kg", "10L", "20L", "75L"]

        extintores = []
        if "extintores" not in st.session_state:
            st.session_state.extintores = []

        tipo_extintor = st.selectbox("Tipo de extintor", tipos_extintores)
        capacidade_extintor = st.selectbox("Capacidade", capacidades_extintores)
        quantidade_extintor = st.number_input("Quantidade", min_value=1, step=1)

        if st.button("Adicionar Extintor"):
            st.session_state.extintores.append({
                "tipo": tipo_extintor,
                "capacidade": capacidade_extintor,
                "quantidade": quantidade_extintor
            })

        if st.session_state.extintores:
            st.subheader("Extintores Adicionados")
            for i, ext in enumerate(st.session_state.extintores):
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                with col1:
                    st.markdown(f"**Tipo:** {ext['tipo']}")
                with col2:
                    st.markdown(f"**Capacidade:** {ext['capacidade']}")
                with col3:
                    st.markdown(f"**Quantidade:** {ext['quantidade']}")
                with col4:
                    if st.button("❌", key=f"del_ext_{i}"):
                        st.session_state.extintores.pop(i)
                        st.rerun()

        st.subheader("Cadastro de Mangueiras")
        tipos_mangueiras = ["15m", "20m", "25m", "30m"]
        mangueiras = {}
        for tipo in tipos_mangueiras:
            qtd = st.number_input(f"Quantidade de mangueiras de {tipo}", min_value=0, step=1)
            if qtd > 0:
                mangueiras[tipo] = qtd

        if st.button("Salvar Empresa"):
            nova_empresa = {
                "usuario": st.session_state["usuario_logado"],
                "nome": nome_empresa,
                "endereco": endereco,
                "cidade": cidade,
                "telefone": telefone,
                "data_cadastro": datetime.combine(data_cadastro, datetime.min.time()),
                "extintores": st.session_state.extintores.copy(),
                "mangueiras": mangueiras
            }
            companies_collection.insert_one(nova_empresa)
            st.success("Empresa cadastrada com sucesso!")
            st.session_state.extintores = []
            st.rerun()

    elif pagina_selecionada == "Empresas Cadastradas":
        st.title("Empresas Cadastradas")
        empresas = list(companies_collection.find({"usuario": st.session_state["usuario_logado"]}))
        nomes_empresas = [e["nome"] for e in empresas]
        nome_busca = st.text_input("Buscar empresa pelo nome")
        empresas_filtradas = [e for e in empresas if nome_busca.lower() in e["nome"].lower()]
        empresa_selecionada = st.selectbox("Selecione uma empresa", [""] + [e["nome"] for e in empresas_filtradas])
        if empresa_selecionada:
            empresa = next((e for e in empresas_filtradas if e["nome"] == empresa_selecionada), None)
            if empresa:
                st.subheader("Informações da Empresa")
                st.write(f"**Endereço:** {empresa['endereco']}")
                st.write(f"**Cidade:** {empresa['cidade']}")
                st.write(f"**Telefone:** {empresa['telefone']}")
                st.write(f"**Data de Cadastro:** {empresa['data_cadastro'].strftime('%d/%m/%Y')}")
                st.write("**Extintores:**")
                for ext in empresa.get("extintores", []):
                    st.write(f"- {ext['quantidade']}x {ext['tipo']} {ext['capacidade']}")
                if "mangueiras" in empresa and empresa["mangueiras"]:
                    st.write("**Mangueiras:**")
                    for tipo, qtd in empresa["mangueiras"].items():
                        st.write(f"- {qtd}x Mangueira {tipo}")
                if st.button("Excluir Empresa"):
                    companies_collection.delete_one({"_id": empresa["_id"]})
                    st.success("Empresa excluída com sucesso!")
                    st.rerun()

    elif pagina_selecionada == "Relatório de Vencimento":
        st.title("Relatório de Vencimento")
        cidades_disponiveis = companies_collection.distinct("cidade", {"usuario": st.session_state["usuario_logado"]})
        tipos_disp = ["ABC", "BC", "CO2", "ÁGUA"]

        cidade_filtro = st.selectbox("Filtrar por cidade", ["Todas"] + sorted(cidades_disponiveis))
        tipo_filtro = st.selectbox("Filtrar por tipo de extintor", ["Todos"] + tipos_disp)
        data_inicio = st.date_input("Data de vencimento (início)", datetime.today())
        data_fim = st.date_input("Data de vencimento (fim)", datetime.today() + timedelta(days=30))

        data_inicio_cadastro = datetime(data_inicio.year - 1, data_inicio.month, data_inicio.day)
        data_fim_cadastro = datetime(data_fim.year - 1, data_fim.month, data_fim.day, 23, 59, 59)

        filtro_busca = {
            "usuario": st.session_state["usuario_logado"],
            "data_cadastro": {"$gte": data_inicio_cadastro, "$lte": data_fim_cadastro}
        }

        if cidade_filtro != "Todas":
            filtro_busca["cidade"] = {"$regex": f"^{cidade_filtro}$", "$options": "i"}

        empresas_filtradas = list(companies_collection.find(filtro_busca))

        if tipo_filtro != "Todos":
            empresas_filtradas = [
                emp for emp in empresas_filtradas
                if any(ext.get("tipo") == tipo_filtro for ext in emp.get("extintores", []))
            ]

        st.subheader("Empresas encontradas:")
        st.write(f"Total: {len(empresas_filtradas)}")

        def gerar_pdf(empresas_pdf):
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=10)
            pdf.add_page()
            pdf.set_font("Arial", "B", 12)
            pdf.cell(190, 10, "Relatório de Vencimento", ln=True, align="C")
            pdf.ln(5)

            for emp in empresas_pdf:
                pdf.set_font("Arial", "B", 10)
                pdf.cell(0, 8, f"Empresa: {emp['nome']}", ln=True)
                pdf.set_font("Arial", "", 10)
                pdf.cell(0, 6, f"Endereço: {emp['endereco']}", ln=True)
                pdf.cell(0, 6, f"Cidade: {emp['cidade']} | Telefone: {emp['telefone']}", ln=True)
                pdf.cell(0, 6, f"Cadastro: {emp['data_cadastro'].strftime('%d/%m/%Y')}", ln=True)
                if "extintores" in emp:
                    for ext in emp['extintores']:
                        pdf.cell(0, 6, f"- {ext['quantidade']}x {ext['tipo']} {ext['capacidade']}", ln=True)
                if "mangueiras" in emp and emp["mangueiras"]:
                    for tipo_m, qtd_m in emp["mangueiras"].items():
                        pdf.cell(0, 6, f"- {qtd_m}x Mangueira {tipo_m}", ln=True)
                pdf.ln(4)

            return pdf.output(dest='S').encode('latin1')

        if st.button("Baixar Relatório em PDF"):
            pdf_bytes = gerar_pdf(empresas_filtradas)
            st.download_button("Clique aqui para baixar", data=pdf_bytes,
                               file_name="relatorio_vencimento.pdf", mime="application/pdf")

    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()
