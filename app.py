import streamlit as st
import pymongo
import pandas as pd
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from fpdf import FPDF

# Conexão com MongoDB usando secrets
client = pymongo.MongoClient(st.secrets["database"]["url"])
db = client["extintores"]
empresas_collection = db["empresas"]

# Autenticação
users = {
    st.secrets["users"]["USUARIO1"].lower(): st.secrets["users"]["SENHA1"],
    st.secrets["users"]["USUARIO2"].lower(): st.secrets["users"]["SENHA2"],
}

if "usuario" not in st.session_state:
    with st.form("login"):
        st.title("Login")
        usuario = st.text_input("Usuário").lower()
        senha = st.text_input("Senha", type="password")
        submit = st.form_submit_button("Entrar")

        if submit:
            if usuario in users and senha == users[usuario]:
                st.session_state.usuario = usuario
                st.rerun()
            else:
                st.error("Usuário ou senha inválidos")
else:
    menu = st.sidebar.radio("Menu", ["Cadastrar Empresa", "Empresas Cadastradas", "Relatório de Vencimento"])

    def normalizar(texto):
        return texto.strip().lower() if isinstance(texto, str) else texto

    if menu == "Cadastrar Empresa":
        st.title("Cadastro de Empresa")
        with st.form("form_empresa"):
            nome = st.text_input("Nome da Empresa")
            cidade = st.text_input("Cidade")
            endereco = st.text_input("Endereço")
            telefone = st.text_input("Telefone")
            data_cadastro = st.date_input("Data de Cadastro", value=datetime.today())

            st.markdown("### Extintores")
            extintores = []
            adicionar = st.checkbox("Adicionar extintor")
            while adicionar:
                tipo = st.selectbox("Tipo de Extintor", ["ABC", "BC", "CO2", "Água"])
                capacidade = st.selectbox("Capacidade", ["4kg", "6kg", "10kg", "10L", "75L"])
                quantidade = st.number_input("Quantidade", min_value=1, step=1)
                extintores.append({"tipo": tipo, "capacidade": capacidade, "quantidade": quantidade})
                adicionar = st.checkbox("Adicionar outro extintor", key=f"add_{len(extintores)}")

            st.markdown("### Mangueiras")
            quantidade_15m = st.number_input("Mangueiras 15m", min_value=0, step=1)
            quantidade_30m = st.number_input("Mangueiras 30m", min_value=0, step=1)

            submitted = st.form_submit_button("Cadastrar")
            if submitted:
                empresa = {
                    "usuario": st.session_state.usuario,
                    "nome": nome,
                    "cidade": cidade,
                    "endereco": endereco,
                    "telefone": telefone,
                    "data_cadastro": data_cadastro.strftime("%Y-%m-%d"),
                    "extintores": extintores,
                    "mangueiras": {
                        "15m": quantidade_15m,
                        "30m": quantidade_30m
                    }
                }
                empresas_collection.insert_one(empresa)
                st.success("Empresa cadastrada com sucesso!")
                st.rerun()

    elif menu == "Empresas Cadastradas":
        st.title("Empresas Cadastradas")
        empresas = list(empresas_collection.find({"usuario": st.session_state.usuario}))

        opcoes = [empresa["nome"] for empresa in empresas]
        selecionada = st.selectbox("Buscar empresa", opcoes)

        if selecionada:
            empresa = next(e for e in empresas if e["nome"] == selecionada)
            st.write(f"**Nome:** {empresa['nome']}")
            st.write(f"**Cidade:** {empresa.get('cidade', '')}")
            st.write(f"**Endereço:** {empresa.get('endereco', '')}")
            st.write(f"**Telefone:** {empresa.get('telefone', '')}")
            st.write(f"**Data Cadastro:** {empresa.get('data_cadastro', '')}")

            st.markdown("#### Extintores")
            for ext in empresa["extintores"]:
                st.write(f"- {ext['quantidade']}x {ext['tipo']} {ext['capacidade']}")

            st.markdown("#### Mangueiras")
            st.write(f"15m: {empresa['mangueiras'].get('15m', 0)}")
            st.write(f"30m: {empresa['mangueiras'].get('30m', 0)}")

            if st.button("Excluir Empresa"):
                empresas_collection.delete_one({"_id": ObjectId(empresa["_id"])})
                st.success("Empresa excluída.")
                st.rerun()

    elif menu == "Relatório de Vencimento":
        st.title("Relatório de Vencimento")

        cidades = empresas_collection.distinct("cidade", {"usuario": st.session_state.usuario})
        cidade_filtro = st.selectbox("Filtrar por Cidade", ["Todas"] + cidades)

        capacidades = set()
        for empresa in empresas_collection.find({"usuario": st.session_state.usuario}):
            for ext in empresa.get("extintores", []):
                capacidades.add(ext.get("capacidade"))
        capacidades = list(capacidades)

        capacidade_filtro = st.selectbox("Filtrar por Capacidade de Extintor", ["Todas"] + capacidades)
        data_inicio = st.date_input("Data Inicial")
        data_fim = st.date_input("Data Final")

        consulta = {"usuario": st.session_state.usuario}
        empresas = empresas_collection.find(consulta)

        resultados = []
        for empresa in empresas:
            data_cadastro = datetime.strptime(empresa["data_cadastro"], "%Y-%m-%d")
            vencimento = data_cadastro + timedelta(days=365)
            if data_inicio <= vencimento.date() <= data_fim:
                if cidade_filtro != "Todas" and normalizar(empresa.get("cidade")) != normalizar(cidade_filtro):
                    continue
                if capacidade_filtro != "Todas":
                    if not any(normalizar(ext["capacidade"]) ==
                               normalizar(capacidade_filtro) for ext in empresa.get("extintores", [])):
                        continue
                resultados.append({
                    "Empresa": empresa["nome"],
                    "Cidade": empresa.get("cidade", ""),
                    "Telefone": empresa.get("telefone", ""),
                    "Vencimento": vencimento.strftime("%d/%m/%Y")
                })

        df = pd.DataFrame(resultados)
        st.dataframe(df)

        if not df.empty:
            if st.button("Baixar PDF"):
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.cell(200, 10, txt="Relatório de Vencimento", ln=True, align="C")
                for i, row in df.iterrows():
                    texto = (f"Empresa: {row['Empresa']} | Cidade: {row['Cidade']} | Tel: {row['Telefone']}"
                             f" | Vencimento: {row['Vencimento']}")
                    pdf.multi_cell(0, 10, txt=texto)
                pdf.output("relatorio_vencimento.pdf")
                with open("relatorio_vencimento.pdf", "rb") as file:
                    st.download_button("Download PDF", file, file_name="relatorio_vencimento.pdf")
