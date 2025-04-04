import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from io import BytesIO
import uuid


# Conectar ao MongoDB usando secrets
client = MongoClient(st.secrets["database"]["url"])
db = client.extintores
empresas_collection = db.empresas
usuarios = {
    st.secrets["users"]["USUARIO1"]: st.secrets["users"]["SENHA1"],
    st.secrets["users"]["USUARIO2"]: st.secrets["users"]["SENHA2"]
}

if "logado" not in st.session_state:
    st.session_state.logado = False
if "usuario" not in st.session_state:
    st.session_state.usuario = ""


def login():
    st.title("Login")
    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar"):
        if usuario in usuarios and senha == usuarios[usuario]:
            st.session_state.logado = True
            st.session_state.usuario = usuario
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")


if not st.session_state.logado:
    login()
else:
    menu = st.sidebar.selectbox("Menu", [
        "Cadastrar Empresa", "Empresas Cadastradas", "Relatório de Vencimento", "Sair"])

    if menu == "Sair":
        st.session_state.logado = False
        st.session_state.usuario = ""
        st.rerun()

    elif menu == "Cadastrar Empresa":
        st.title("Cadastro de Empresa")
        nome = st.text_input("Nome da Empresa")
        cidade = st.text_input("Cidade")
        endereco = st.text_input("Endereço Completo")
        telefone = st.text_input("Telefone")
        data_cadastro = st.date_input("Data de Cadastro", value=datetime.today())

        st.subheader("Adicionar Extintores")
        tipo_extintor = st.selectbox("Tipo", ["Pó ABC", "Pó BC", "CO2", "Água"])
        capacidade = st.selectbox("Capacidade", ["4kg", "6kg", "10kg", "10L", "75L"])
        quantidade = st.number_input("Quantidade", min_value=1, value=1)

        if "extintores" not in st.session_state:
            st.session_state.extintores = []

        if st.button("Adicionar Extintor"):
            st.session_state.extintores.append({
                "tipo": tipo_extintor,
                "capacidade": capacidade,
                "quantidade": quantidade
            })
            st.rerun()

        st.write("Extintores Adicionados:")
        for i, ext in enumerate(st.session_state.extintores):
            st.write(f"{ext['quantidade']}x {ext['tipo']} ({ext['capacidade']})")

        st.subheader("Mangueiras de Incêndio")
        quantidade_15m = st.number_input("Mangueiras de 15m", min_value=0, value=0)
        quantidade_30m = st.number_input("Mangueiras de 30m", min_value=0, value=0)

        if st.button("Cadastrar Empresa"):
            vencimento = data_cadastro + timedelta(days=365)
            empresa = {
                "_id": str(uuid.uuid4()),
                "nome": nome,
                "cidade": cidade,
                "endereco": endereco,
                "telefone": telefone,
                "data_cadastro": data_cadastro.strftime("%Y-%m-%d"),
                "vencimento": vencimento.strftime("%Y-%m-%d"),
                "extintores": st.session_state.extintores,
                "mangueiras": {
                    "15m": quantidade_15m,
                    "30m": quantidade_30m
                },
                "usuario": st.session_state.usuario
            }
            empresas_collection.insert_one(empresa)
            st.success("Empresa cadastrada com sucesso!")
            st.session_state.extintores = []
            st.rerun()

    elif menu == "Empresas Cadastradas":
        st.title("Empresas Cadastradas")
        empresas = list(empresas_collection.find({"usuario": st.session_state.usuario}))
        nomes = [e["nome"] for e in empresas]
        selecionada = st.selectbox("Buscar Empresa", nomes if nomes else ["Nenhuma"])

        for empresa in empresas:
            if empresa["nome"] == selecionada:
                st.markdown(f"### {empresa['nome']}")
                st.write(f"Cidade: {empresa.get('cidade', '')}")
                st.write(f"Telefone: {empresa.get('telefone', '')}")
                st.write(f"Endereço: {empresa.get('endereco', '')}")
                st.write(f"Data Cadastro: {empresa.get('data_cadastro', '')}")
                st.write(f"Vencimento: {empresa.get('vencimento', '')}")
                st.markdown("**Extintores:**")
                for ext in empresa.get("extintores", []):
                    st.write(f"- {ext['quantidade']}x {ext['tipo']} ({ext['capacidade']})")
                st.markdown("**Mangueiras:**")
                st.write(f"- 15m: {empresa.get('mangueiras', {}).get('15m', 0)}")
                st.write(f"- 30m: {empresa.get('mangueiras', {}).get('30m', 0)}")

                if st.button("Excluir Empresa"):
                    empresas_collection.delete_one({"_id": empresa["_id"]})
                    st.success("Empresa excluída!")
                    st.rerun()

    elif menu == "Relatório de Vencimento":
        st.title("Relatório de Vencimento")
        cidades = empresas_collection.distinct("cidade")
        cidade_filtro = st.selectbox("Filtrar por Cidade", ["Todas"] + sorted(cidades))
        capacidades_disponiveis = ["4kg", "6kg", "10kg", "10L", "75L"]
        capacidade_filtro = st.multiselect("Filtrar por Capacidade", capacidades_disponiveis)
        data_inicio = st.date_input("Data de Vencimento a partir de:", value=datetime.today())
        data_fim = st.date_input("Até a data:", value=datetime.today() + timedelta(days=30))

        filtro = {
            "usuario": st.session_state.usuario,
            "vencimento": {
                "$gte": data_inicio.strftime("%Y-%m-%d"),
                "$lte": data_fim.strftime("%Y-%m-%d")
            }
        }
        if cidade_filtro != "Todas":
            filtro["cidade"] = cidade_filtro

        empresas = list(empresas_collection.find(filtro))

        if capacidade_filtro:
            empresas_filtradas = []
            for empresa in empresas:
                ext_validos = [ext for ext in empresa.get("extintores", []) if ext["capacidade"] in capacidade_filtro]
                if ext_validos:
                    empresa["extintores"] = ext_validos
                    empresas_filtradas.append(empresa)
        else:
            empresas_filtradas = empresas

        st.markdown("### Empresas com vencimento dentro do período:")
        if not empresas_filtradas:
            st.info("Nenhuma empresa encontrada com os filtros selecionados.")
        else:
            for empresa in empresas_filtradas:
                st.markdown(f"**📌 {empresa['nome']}**")
                st.write(f"📍 Cidade: {empresa.get('cidade', '')}")
                st.write(f"📞 Telefone: {empresa.get('telefone', '')}")
                st.write(f"🗓️ Vencimento: {empresa['vencimento']}")
                st.markdown("**Extintores:**")
                for ext in empresa["extintores"]:
                    st.write(f"- {ext['quantidade']}x {ext['tipo']} ({ext['capacidade']})")
                st.markdown("---")

            def gerar_pdf(empresas_filtradas):
                buffer = BytesIO()
                c = canvas.Canvas(buffer, pagesize=A4)
                largura, altura = A4
                y = altura - 40
                c.setFont("Helvetica-Bold", 16)
                c.drawString(50, y, "Relatório de Vencimento de Extintores")
                y -= 30
                c.setFont("Helvetica", 12)
                for empresa in empresas_filtradas:
                    if y < 100:
                        c.showPage()
                        y = altura - 40
                    c.drawString(50, y, f"Empresa: {empresa['nome']}")
                    y -= 18
                    c.drawString(50, y, f"Cidade: {empresa.get('cidade', '')}  |  Telefone: {empresa.get('telefone', '')}")
                    y -= 18
                    c.drawString(50, y, f"Vencimento: {empresa['vencimento']}")
                    y -= 18
                    c.drawString(50, y, "Extintores:")
                    for ext in empresa["extintores"]:
                        c.drawString(70, y, f"- {ext['quantidade']}x {ext['tipo']} ({ext['capacidade']})")
                        y -= 15
                    y -= 15
                c.save()
                buffer.seek(0)
                return buffer

            if st.button("Gerar PDF do Relatório"):
                pdf_buffer = gerar_pdf(empresas_filtradas)
                st.download_button(
                    label="📄 Baixar PDF",
                    data=pdf_buffer,
                    file_name="relatorio_vencimento.pdf",
                    mime="application/pdf"
                )
