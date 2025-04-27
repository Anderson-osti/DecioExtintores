import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
from fpdf import FPDF
from collections import defaultdict

# Conexão com o MongoDB
MONGO_URL = st.secrets["database"]["url"]
client = MongoClient(MONGO_URL)
db = client["extintores_db"]
companies_collection = db["companies"]

# Autenticação (case-insensitive para o usuário)
CREDENCIAIS_USUARIOS = {
    st.secrets["users"]["USUARIO1"].lower(): st.secrets["users"]["SENHA1"],
    st.secrets["users"]["USUARIO2"].lower(): st.secrets["users"]["SENHA2"],
    st.secrets["users"]["USUARIO3"].lower(): st.secrets["users"]["SENHA3"]
}

def autenticar_usuario(input_usuario, input_senha):
    return CREDENCIAIS_USUARIOS.get(input_usuario.lower()) == input_senha

# Função para estilizar o layout
def aplicar_estilo():
    st.markdown("""
        <style>
            .big-title {
                font-size: 32px;
                color: #0D47A1;
                font-weight: bold;
            }
            .sub-title {
                font-size: 24px;
                color: #1E88E5;
                margin-top: 20px;
            }
            .form-container {
                background-color: #f0f4f8;
                padding: 20px;
                border-radius: 8px;
                margin-top: 20px;
            }
            .button {
                background-color: #1E88E5;
                color: white;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 16px;
                border: none;
            }
            .button:hover {
                background-color: #1565C0;
            }
            .info-box {
                background-color: #f9f9f9;
                border: 1px solid #e0e0e0;
                padding: 15px;
                border-radius: 8px;
                margin-top: 20px;
            }
        </style>
    """, unsafe_allow_html=True)

# Tela de login
if "logged_in" not in st.session_state:
    st.title("Login")
    campo_usuario = st.text_input("Usuário")
    campo_senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if autenticar_usuario(campo_usuario, campo_senha):
            st.session_state["logged_in"] = True
            st.session_state["usuario_logado"] = campo_usuario.lower()
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos")

# Aplicação
if st.session_state.get("logged_in"):
    aplicar_estilo()
    st.sidebar.title("Navegação")
    pagina_selecionada = st.sidebar.radio("Ir para", ["Cadastro de Empresa",
                                                      "Empresas Cadastradas", "Relatório de Vencimento"])

    if pagina_selecionada == "Cadastro de Empresa":
        st.markdown('<p class="big-title">Cadastro de Empresa</p>', unsafe_allow_html=True)
        nome_empresa = st.text_input("Nome da Empresa")
        endereco_empresa = st.text_area("Endereço Completo")
        cidade_empresa = st.text_input("Cidade")
        telefone_empresa = st.text_input("Telefone")
        data_manual = st.date_input("Data do Cadastro", value=datetime.today())

        tipos_extintores = ["ABC", "BC", "CO2", "ÁGUA"]
        capacidades = ["1kg", "4kg", "6kg", "8kg", "10kg", "12kg", "20kg", "75kg", "10L", "20L", "75L"]

        extintores_temp = []

        with st.form("form_extintores"):
            tipo_selecionado = st.selectbox("Tipo de extintor", tipos_extintores)
            capacidade_selecionada = st.selectbox("Capacidade", capacidades)
            quantidade_selecionada = st.number_input("Quantidade", min_value=1, step=1)
            adicionar_extintor = st.form_submit_button("Adicionar")

            if adicionar_extintor:
                extintores_temp.append({
                    "tipo": tipo_selecionado,
                    "capacidade": capacidade_selecionada,
                    "quantidade": quantidade_selecionada
                })

        if "extintores_cadastrados" not in st.session_state:
            st.session_state["extintores_cadastrados"] = []

        st.session_state["extintores_cadastrados"] += extintores_temp

        st.subheader("Extintores adicionados")
        for ext in st.session_state["extintores_cadastrados"]:
            st.markdown(f"- {ext['quantidade']}x {ext['tipo']} {ext['capacidade']}")

        st.subheader("Mangueiras de Incêndio")
        tipos_mangueiras = ["15m", "20m", "25m", "30m"]
        mangueiras_adicionadas = {}
        for tipo_m in tipos_mangueiras:
            qtd_m = st.number_input(f"Quantidade de mangueiras de {tipo_m}", min_value=0, step=1, key=f"m_{tipo_m}")
            if qtd_m > 0:
                mangueiras_adicionadas[tipo_m] = qtd_m

        if st.button("Cadastrar Empresa"):
            data_cadastro = datetime.combine(data_manual, datetime.min.time())
            nova_empresa = {
                "nome": nome_empresa,
                "endereco": endereco_empresa,
                "cidade": cidade_empresa,
                "telefone": telefone_empresa,
                "extintores": st.session_state["extintores_cadastrados"],
                "mangueiras": mangueiras_adicionadas,
                "usuario": st.session_state["usuario_logado"],
                "data_cadastro": data_cadastro
            }
            companies_collection.insert_one(nova_empresa)
            st.success("Empresa cadastrada com sucesso!")
            st.session_state["extintores_cadastrados"] = []
            st.rerun()

    elif pagina_selecionada == "Empresas Cadastradas":
        st.markdown('<p class="big-title">Empresas Cadastradas</p>', unsafe_allow_html=True)
        termo_busca = st.text_input("Buscar por nome").lower()
        empresas_encontradas = list(companies_collection.find({"usuario": st.session_state["usuario_logado"]}))
        nomes_empresas = [e["nome"] for e in empresas_encontradas]
        nomes_filtrados = [e["nome"] for e in empresas_encontradas if termo_busca in e["nome"].lower()]
        empresa_selecionada = st.selectbox("Selecione uma empresa", nomes_filtrados if termo_busca else nomes_empresas)

        if empresa_selecionada:
            empresa = companies_collection.find_one({
                "nome": empresa_selecionada,
                "usuario": st.session_state["usuario_logado"]
            })

            if empresa:
                st.markdown('<div class="info-box">', unsafe_allow_html=True)
                col1, col2, col3 = st.columns([2, 2, 2])
                with col1:
                    st.write(f"📍 Endereço: {empresa['endereco']}")
                    st.write(f"🏙️ Cidade: {empresa['cidade']}")
                with col2:
                    st.write(f"📞 Telefone: {empresa['telefone']}")
                    st.write(f"📅 Cadastro: {empresa['data_cadastro'].strftime('%d/%m/%Y')}")
                with col3:
                    st.write("🧯 Extintores:")
                    for ext in empresa['extintores']:
                        st.write(f"- {ext['quantidade']}x {ext['tipo']} {ext['capacidade']}")
                    if empresa.get("mangueiras"):
                        for tipo_m, qtd_m in empresa["mangueiras"].items():
                            st.write(f"- {qtd_m}x Mangueira {tipo_m}")
                st.markdown('</div>', unsafe_allow_html=True)

                if st.button("Excluir Empresa"):
                    companies_collection.delete_one({"_id": empresa["_id"]})
                    st.success("Empresa excluída com sucesso.")
                    st.rerun()

    elif pagina_selecionada == "Relatório de Vencimento":
        st.markdown('<p class="big-title">Relatório de Vencimento</p>', unsafe_allow_html=True)
        cidades_disponiveis = companies_collection.distinct("cidade", {"usuario": st.session_state["usuario_logado"]})
        tipos_disp = ["ABC", "BC", "CO2", "ÁGUA"]
        cidade_filtro = st.selectbox("Filtrar por cidade", ["Todas"] + sorted(cidades_disponiveis))
        tipo_filtro = st.selectbox("Filtrar por tipo de extintor", ["Todos"] + tipos_disp)
        mes_ano = st.date_input("Selecione o mês", datetime.today())

        empresas_usuario = list(companies_collection.find({"usuario": st.session_state["usuario_logado"]}))

        lista_empresas = []
        for empresa in empresas_usuario:
            data_vencimento = empresa["data_cadastro"] + timedelta(days=365)
            if data_vencimento.month == mes_ano.month:
                if cidade_filtro == "Todas" or empresa.get("cidade", "").lower() == cidade_filtro.lower():
                    if tipo_filtro == "Todos" or any(ext.get("tipo") == tipo_filtro for
                                                     ext in empresa.get("extintores", [])):
                        lista_empresas.append(empresa)

        st.subheader("Empresas encontradas:")
        st.write(f"Total: {len(lista_empresas)}")

        def gerar_pdf(empresas_pdf):
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=10)
            pdf.add_page()

            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, "Relatório de Vencimento", ln=True, align="C")
            pdf.ln(4)

            pdf.set_font("Arial", "", 9)
            totais = defaultdict(int)

            for emp in empresas_pdf:
                linha = (
                    f"{emp['nome']} | "
                    f"{emp['cidade']} | "
                    f"{emp['telefone']} | "
                    f"{emp['data_cadastro'].strftime('%d/%m/%Y')} | "
                    f"{emp['endereco']}"
                )
                pdf.multi_cell(0, 5, linha)
                if "extintores" in emp:
                    for ext in emp['extintores']:
                        chave = f"{ext['tipo']} {ext['capacidade']}"
                        totais[chave] += ext["quantidade"]
                        pdf.cell(0, 5, f"- {ext['quantidade']}x {chave}", ln=True)
                if "mangueiras" in emp and emp["mangueiras"]:
                    for tipo_m, qtd_m in emp["mangueiras"].items():
                        pdf.cell(0, 5, f"- {qtd_m}x Mangueira {tipo_m}", ln=True)
                pdf.ln(2)

            pdf.add_page()
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Totais por Tipo e Capacidade de Extintor", ln=True)
            pdf.ln(2)

            pdf.set_font("Arial", "", 10)
            for chave, total in sorted(totais.items()):
                pdf.cell(0, 6, f"- {total}x {chave}", ln=True)

            return pdf.output(dest='S').encode('latin1')

        if st.button("Baixar Relatório"):
            pdf_content = gerar_pdf(lista_empresas)
            st.download_button(label="Baixar PDF", data=pdf_content, file_name="relatorio_vencimento.pdf")

    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()
