import streamlit as st
from pymongo import MongoClient
from datetime import datetime, timedelta
from fpdf import FPDF
import os

# Conectar ao banco de dados
client = MongoClient(st.secrets["mongodb_url"])
db = client["extintores"]
colecao_empresas = db["empresas"]


# Função para calcular vencimento
def calcular_vencimento(data_cadastro):
    if isinstance(data_cadastro, str):
        data_cadastro = datetime.strptime(data_cadastro, "%Y-%m-%d")
    return data_cadastro + timedelta(days=365)


# Cadastro de empresas
def cadastrar_empresa():
    st.title("Cadastro de Empresa")
    nome = st.text_input("Nome da Empresa")
    endereco = st.text_input("Endereço Completo")
    cidade = st.text_input("Cidade")
    telefone = st.text_input("Telefone")
    data_cadastro = st.date_input("Data de Cadastro", datetime.today())

    if st.button("Cadastrar"):
        nova_empresa = {
            "nome": nome,
            "endereco": endereco,
            "cidade": cidade,
            "telefone": telefone,
            "data_cadastro": data_cadastro.strftime("%Y-%m-%d")
        }
        colecao_empresas.insert_one(nova_empresa)
        st.success("Empresa cadastrada com sucesso!")
        st.rerun()


# Listar empresas cadastradas
def listar_empresas():
    st.title("Empresas Cadastradas")
    empresas = colecao_empresas.find()
    for emp in empresas:
        vencimento = calcular_vencimento(emp["data_cadastro"])
        st.write(f"Empresa: {emp['nome']} - Vencimento: {vencimento.strftime('%d/%m/%Y')}")


# Relatório de vencimentos
def relatorio_vencimentos():
    st.title("Relatório de Vencimentos")
    filtro_cidade = st.text_input("Filtrar por Cidade")
    filtro_data = st.date_input("Filtrar por Data de Vencimento", datetime.today())
    empresas = colecao_empresas.find()
    for emp in empresas:
        vencimento = calcular_vencimento(emp["data_cadastro"])
        if filtro_cidade.lower() in emp["cidade"].lower() and vencimento >= filtro_data:
            st.write(
                f"Empresa: {emp['nome']} - Cidade: {emp['cidade']} - Vencimento: {vencimento.strftime('%d/%m/%Y')}")


# Navegação no app
def main():
    menu = ["Cadastrar Empresa", "Empresas Cadastradas", "Relatório de Vencimentos"]
    escolha = st.sidebar.selectbox("Menu", menu)

    if escolha == "Cadastrar Empresa":
        cadastrar_empresa()
    elif escolha == "Empresas Cadastradas":
        listar_empresas()
    elif escolha == "Relatório de Vencimentos":
        relatorio_vencimentos()


if __name__ == "__main__":
    main()
