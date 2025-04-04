import streamlit as st
from pymongo import MongoClient
import datetime
import pdfkit
import tempfile
import os

# Conexão segura com o MongoDB via secrets
mongo_url = st.secrets["database"]["url"]
client = MongoClient(mongo_url)
db = client["extintores"]
empresas_collection = db["empresas"]
usuarios_collection = db["usuarios"]


# Autenticação
def autenticar_usuario():
    if "usuario" not in st.session_state:
        with st.form("login"):
            st.title("Login")
            usuario = st.text_input("Usuário")
            senha = st.text_input("Senha", type="password")
            submitted = st.form_submit_button("Entrar")
            if submitted:
                user = usuarios_collection.find_one({"usuario": usuario, "senha": senha})
                if user:
                    st.session_state.usuario = usuario
                    st.rerun()
                else:
                    st.error("Usuário ou senha inválidos")
        st.stop()


autenticar_usuario()


# Funções auxiliares
def normalizar(texto):
    return texto.strip().lower()


def cadastrar_empresa():
    st.header("Cadastro de Empresa")

    with st.form("form_empresa"):
        nome = st.text_input("Nome da Empresa")
        cidade = st.text_input("Cidade")
        endereco = st.text_input("Endereço completo")
        telefone = st.text_input("Telefone")
        data_cadastro = st.date_input("Data do cadastro", value=datetime.date.today())

        # Extintores
        st.subheader("Extintores")
        tipo_extintor = st.selectbox("Tipo", ["ABC", "BC", "CO2", "Água"])
        capacidade = st.selectbox("Capacidade", ["4kg", "6kg", "10kg", "75L"])
        quantidade = st.number_input("Quantidade", min_value=1, step=1)

        if "extintores" not in st.session_state:
            st.session_state.extintores = []

        if st.form_submit_button("Adicionar Extintor"):
            st.session_state.extintores.append({
                "tipo": tipo_extintor,
                "capacidade": capacidade,
                "quantidade": quantidade
            })
            st.rerun()

        if st.session_state.extintores:
            st.write("Extintores adicionados:")
            for i, ext in enumerate(st.session_state.extintores):
                st.write(f"{i + 1}. {ext['tipo']} - {ext['capacidade']} - {ext['quantidade']} unidades")
                if st.button(f"Remover {i + 1}", key=f"remover_ext_{i}"):
                    del st.session_state.extintores[i]
                    st.rerun()

        # Mangueiras
        st.subheader("Mangueiras")
        tipo_mangueira = st.selectbox("Comprimento", ["15m", "30m"])
        quantidade_mangueira = st.number_input("Quantidade de Mangueiras", min_value=0, step=1, key="mangueira")

        if st.form_submit_button("Cadastrar Empresa"):
            empresa = {
                "nome": nome,
                "cidade": cidade,
                "endereco": endereco,
                "telefone": telefone,
                "data_cadastro": str(data_cadastro),
                "usuario": st.session_state.usuario,
                "extintores": st.session_state.extintores.copy(),
                "mangueiras": {
                    "tipo": tipo_mangueira,
                    "quantidade": quantidade_mangueira
                }
            }
            empresas_collection.insert_one(empresa)
            st.success("Empresa cadastrada com sucesso!")
            del st.session_state.extintores
            st.rerun()


def listar_empresas():
    st.header("Empresas Cadastradas")
    empresas = empresas_collection.find({"usuario": st.session_state.usuario})

    nomes = [e["nome"] for e in empresas]
    empresas = list(empresas_collection.find({"usuario": st.session_state.usuario}))

    nome_busca = st.text_input("Buscar Empresa")
    if nome_busca:
        empresas = [e for e in empresas if nome_busca.lower() in e["nome"].lower()]

    for empresa in empresas:
        with st.expander(empresa["nome"]):
            st.write(f"📍 Cidade: {empresa.get('cidade', '')}")
            st.write(f"🏠 Endereço: {empresa.get('endereco', '')}")
            st.write(f"📞 Telefone: {empresa.get('telefone', '')}")
            st.write(f"📅 Cadastro: {empresa.get('data_cadastro')}")
            st.write("🔴 Extintores:")
            for ext in empresa.get("extintores", []):
                st.write(f"- {ext['tipo']} | {ext['capacidade']} | {ext['quantidade']} unidades")
            st.write("🟦 Mangueiras:")
            st.write(f"- {empresa['mangueiras']['tipo']} | {empresa['mangueiras']['quantidade']} unidades")
            if st.button("Excluir Empresa", key=str(empresa["_id"])):
                empresas_collection.delete_one({"_id": empresa["_id"]})
                st.success("Empresa excluída.")
                st.rerun()


def relatorio_vencimento():
    st.header("Relatório de Vencimentos")

    cidades = list(empresas_collection.distinct("cidade"))
    cidade_filtro = st.selectbox("Filtrar por cidade", ["Todas"] + cidades)

    tipos_modelos = []
    for e in empresas_collection.find():
        for ext in e.get("extintores", []):
            modelo = f"{ext['tipo']} - {ext['capacidade']}"
            if modelo not in tipos_modelos:
                tipos_modelos.append(modelo)
    tipo_filtro = st.selectbox("Filtrar por extintor", ["Todos"] + tipos_modelos)

    data_referencia = st.date_input("Data de referência", value=datetime.date.today())

    empresas = empresas_collection.find()

    empresas_filtradas = []
    for e in empresas:
        data = datetime.datetime.strptime(e["data_cadastro"], "%Y-%m-%d").date()
        vencimento = data + datetime.timedelta(days=365)
        if vencimento.month == data_referencia.month and vencimento.year == data_referencia.year:
            if cidade_filtro != "Todas" and normalizar(e["cidade"]) != normalizar(cidade_filtro):
                continue
            if tipo_filtro != "Todos":
                encontrado = any(
                    normalizar(f"{ext['tipo']} - {ext['capacidade']}") == normalizar(tipo_filtro)
                    for ext in e.get("extintores", [])
                )
                if not encontrado:
                    continue
            empresas_filtradas.append(e)

    for e in empresas_filtradas:
        with st.expander(e["nome"]):
            st.write(f"📍 Cidade: {e.get('cidade')}")
            st.write(f"🏠 Endereço: {e.get('endereco')}")
            st.write(f"📞 Telefone: {e.get('telefone')}")
            st.write(f"📅 Cadastro: {e['data_cadastro']}")
            st.write("🔴 Extintores:")
            for ext in e.get("extintores", []):
                st.write(f"- {ext['tipo']} | {ext['capacidade']} | {ext['quantidade']} unidades")

    if empresas_filtradas and st.button("Gerar PDF"):
        html = "<h1>Relatório de Vencimentos</h1><ul>"
        for e in empresas_filtradas:
            html += f"<li><b>{e['nome']}</b><br>Cidade: {e['cidade']}<br>Telefone: {e['telefone']}<br>Endereço: {e['endereco']}<br>Cadastro: {e['data_cadastro']}</li><br>"
        html += "</ul>"

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            pdfkit.from_string(html, tmp_file.name)
            with open(tmp_file.name, "rb") as f:
                st.download_button("Baixar PDF", f, file_name="relatorio_vencimento.pdf")
            os.remove(tmp_file.name)


# Navegação
st.sidebar.title("Menu")
menu = st.sidebar.radio("Navegar", ["Cadastrar Empresa", "Empresas Cadastradas", "Relatório de Vencimento", "Sair"])

if menu == "Cadastrar Empresa":
    cadastrar_empresa()
elif menu == "Empresas Cadastradas":
    listar_empresas()
elif menu == "Relatório de Vencimento":
    relatorio_vencimento()
elif menu == "Sair":
    st.session_state.clear()
    st.rerun()
