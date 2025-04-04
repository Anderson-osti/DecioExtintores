import streamlit as st
import pymongo
import pdfkit
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from jinja2 import Template
import base64


# ------ SEGREDOS (Streamlit Secrets) ------
MONGO_URL = st.secrets["database"]["url"]
USUARIOS = {
    st.secrets["users"]["USUARIO1"].lower(): st.secrets["users"]["SENHA1"],
    st.secrets["users"]["USUARIO2"].lower(): st.secrets["users"]["SENHA2"]
}

# ------ CONEXÃO COM MONGODB ------
cliente = pymongo.MongoClient(MONGO_URL)
banco = cliente["extintores"]
colecao_empresas = banco["empresas"]


# ------ FUNÇÕES AUXILIARES ------
def gerar_pdf_html(empresas):
    html_template = Template("""
    <h1>Relatório de Vencimento</h1>
    {% for empresa in empresas %}
        <h2>{{ empresa.nome }}</h2>
        <p><strong>Cidade:</strong> {{ empresa.cidade }}</p>
        <p><strong>Telefone:</strong> {{ empresa.telefone }}</p>
        <ul>
        {% for item in empresa.extintores %}
            <li>{{ item.modelo }} - {{ item.tipo }} - {{ item.capacidade }} - Quantidade: {{ item.quantidade }}
             - Cadastro: {{ item.data_cadastro }}</li>
        {% endfor %}
        </ul>
        <hr>
    {% endfor %}
    """)
    return html_template.render(empresas=empresas)


def salvar_pdf(html):
    pdf = pdfkit.from_string(html, False)
    b64 = base64.b64encode(pdf).decode('utf-8')
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="relatorio.pdf">📄 Baixar PDF</a>'
    return href


# ------ LOGIN ------
if "logado" not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if usuario.lower() in USUARIOS and senha == USUARIOS[usuario.lower()]:
            st.session_state.usuario = usuario
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")
    st.stop()

# ------ MENU PRINCIPAL ------
opcao = st.sidebar.selectbox("Menu", [
    "Cadastrar Empresa",
    "Empresas Cadastradas",
    "Relatório de Vencimento"
])

# ------ CADASTRAR EMPRESA ------
if opcao == "Cadastrar Empresa":
    st.title("Cadastro de Empresa")
    nome = st.text_input("Nome da empresa")
    cidade = st.text_input("Cidade")
    endereco = st.text_input("Endereço completo")
    telefone = st.text_input("Telefone")
    data_cadastro_manual = st.date_input("Data do cadastro")

    st.subheader("Cadastrar Extintores")
    extintores = []

    if "extintores_temp" not in st.session_state:
        st.session_state.extintores_temp = []

    with st.form("form_extintor"):
        modelo = st.selectbox("Modelo", ["Pó ABC", "Pó BC", "CO2", "Água"])
        capacidade = st.selectbox("Capacidade", ["4kg", "6kg", "10kg", "10L", "75L"])
        quantidade = st.number_input("Quantidade", min_value=1, step=1)
        submitted = st.form_submit_button("Adicionar Extintor")
        if submitted:
            st.session_state.extintores_temp.append({
                "modelo": modelo,
                "capacidade": capacidade,
                "quantidade": quantidade,
                "tipo": "Extintor",
                "data_cadastro": data_cadastro_manual.strftime("%Y-%m-%d")
            })

    st.subheader("Cadastrar Mangueiras")
    col1, col2 = st.columns(2)
    with col1:
        qtd_15 = st.number_input("Mangueiras 15m", min_value=0, step=1)
    with col2:
        qtd_30 = st.number_input("Mangueiras 30m", min_value=0, step=1)

    if st.button("Salvar Empresa"):
        produtos = st.session_state.extintores_temp.copy()
        if qtd_15 > 0:
            produtos.append({
                "modelo": "Mangueira 15m",
                "quantidade": qtd_15,
                "tipo": "Mangueira",
                "data_cadastro": data_cadastro_manual.strftime("%Y-%m-%d")
            })
        if qtd_30 > 0:
            produtos.append({
                "modelo": "Mangueira 30m",
                "quantidade": qtd_30,
                "tipo": "Mangueira",
                "data_cadastro": data_cadastro_manual.strftime("%Y-%m-%d")
            })

        colecao_empresas.insert_one({
            "usuario": st.session_state.usuario,
            "nome": nome,
            "cidade": cidade,
            "endereco": endereco,
            "telefone": telefone,
            "extintores": produtos
        })
        st.success("Empresa cadastrada com sucesso!")
        st.session_state.extintores_temp = []
        st.rerun()

    if st.session_state.extintores_temp:
        st.subheader("Extintores adicionados")
        for item in st.session_state.extintores_temp:
            st.write(f"{item['modelo']} - {item['capacidade']} - Quantidade: {item['quantidade']}")

# ------ EMPRESAS CADASTRADAS ------
elif opcao == "Empresas Cadastradas":
    st.title("Empresas Cadastradas")
    termo = st.text_input("Buscar empresa por nome")

    resultados = colecao_empresas.find({"usuario": st.session_state.usuario})
    if termo:
        resultados = filter(lambda e: termo.lower() in e["nome"].lower(), resultados)

    for empresa in resultados:
        with st.expander(empresa["nome"]):
            st.write(f"Cidade: {empresa.get('cidade', '')}")
            st.write(f"Endereço: {empresa.get('endereco', '')}")
            st.write(f"Telefone: {empresa.get('telefone', '')}")
            for item in empresa["extintores"]:
                st.write(f"{item['tipo']}: {item['modelo']} - {item.get('capacidade', '')}"
                         f" - Quantidade: {item['quantidade']}")
            if st.button("Excluir", key=str(empresa["_id"])):
                colecao_empresas.delete_one({"_id": ObjectId(empresa["_id"])})
                st.success("Empresa excluída!")
                st.rerun()

# ------ RELATÓRIO DE VENCIMENTO ------
elif opcao == "Relatório de Vencimento":
    st.title("Relatório de Vencimento")
    filtro_cidade = st.text_input("Filtrar por cidade")
    filtro_modelo = st.text_input("Filtrar por modelo de extintor (ex: ABC, CO2, Água)")
    data_inicial = st.date_input("Data inicial", datetime.today())
    data_final = st.date_input("Data final", datetime.today() + timedelta(days=30))

    empresas = colecao_empresas.find({"usuario": st.session_state.usuario})
    vencidas = []

    for empresa in empresas:
        produtos_vencidos = []
        for item in empresa["extintores"]:
            data = datetime.strptime(item["data_cadastro"], "%Y-%m-%d") + timedelta(days=365)
            if data_inicial <= data.date() <= data_final:
                if item["tipo"] == "Extintor":
                    if (not filtro_modelo or filtro_modelo.lower() in item["modelo"].lower()) and \
                       (not filtro_cidade or filtro_cidade.lower() in empresa.get("cidade", "").lower()):
                        produtos_vencidos.append(item)
        if produtos_vencidos:
            vencidas.append({"nome": empresa["nome"], "cidade": empresa.get("cidade", ""),
                             "telefone": empresa.get("telefone", ""), "extintores": produtos_vencidos})

    if vencidas:
        html = gerar_pdf_html(vencidas)
        st.markdown(salvar_pdf(html), unsafe_allow_html=True)

        for emp in vencidas:
            with st.expander(emp["nome"]):
                st.write(f"Cidade: {emp['cidade']}")
                st.write(f"Telefone: {emp['telefone']}")
                for item in emp["extintores"]:
                    venc = datetime.strptime(item["data_cadastro"], "%Y-%m-%d") + timedelta(days=365)
                    st.write(f"{item['modelo']} - {item['capacidade']} - Quantidade: {item['quantidade']}"
                             f" - Vence em: {venc.strftime('%d/%m/%Y')}")
    else:
        st.info("Nenhuma empresa com extintores vencendo nesse período.")
