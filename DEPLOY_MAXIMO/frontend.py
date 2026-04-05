import streamlit as st
import requests
import json
from typing import Dict, Any
import jwt
import datetime

# Configurações da página
st.set_page_config(
    page_title="Clinical Psychology AI System",
    page_icon="🧠",
    layout="wide"
)

# Funções auxiliares para autenticação
def login_user(username: str, password: str) -> Dict[str, Any]:
    """Faz login do usuário no sistema"""
    url = "http://localhost:8000/login"
    payload = {
        "username": username,
        "password": password
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Erro {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": f"Erro de conexão: {str(e)}"}

def register_user(username: str, full_name: str, email: str, password: str) -> Dict[str, Any]:
    """Registra um novo usuário no sistema"""
    url = "http://localhost:8000/register"
    payload = {
        "username": username,
        "full_name": full_name,
        "email": email,
        "password": password
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Erro {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": f"Erro de conexão: {str(e)}"}

def is_token_valid(token: str) -> bool:
    """Verifica se o token JWT é válido"""
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get('exp')
        if exp:
            return datetime.datetime.fromtimestamp(exp) > datetime.datetime.utcnow()
        return False
    except jwt.ExpiredSignatureError:
        return False
    except jwt.InvalidTokenError:
        return False

def logout():
    """Faz logout do usuário"""
    if 'token' in st.session_state:
        del st.session_state.token
    if 'username' in st.session_state:
        del st.session_state.username
    if 'user_id' in st.session_state:
        del st.session_state.user_id

# Verificar se o usuário está autenticado
authenticated = False
if 'token' in st.session_state:
    token = st.session_state.token
    if token and is_token_valid(token):
        # Token ainda é válido
        authenticated = True
    else:
        # Token expirou ou é inválido, limpar estado
        logout()

# Tela de login (se não autenticado)
if not authenticated:
    st.title("🧠 Sistema de IA para Psicopedagogia Clínica")
    st.subheader("Acesso ao Sistema")

    # Tabs para login e registro
    login_tab, register_tab = st.tabs(["Login", "Registrar"])

    with login_tab:
        username = st.text_input("Nome de usuário")
        password = st.text_input("Senha", type="password")

        if st.button("Login"):
            if username and password:
                result = login_user(username, password)
                if "error" in result:
                    st.error(result["error"])
                else:
                    # Armazenar informações de autenticação
                    st.session_state.token = result["access_token"]
                    st.session_state.username = username
                    # Decodificar o token para obter o user_id
                    try:
                        payload = jwt.decode(result["access_token"], options={"verify_signature": False})
                        st.session_state.user_id = int(payload["sub"])
                        st.success("Login realizado com sucesso!")
                        # Pequeno delay para garantir a atualização da interface
                        import time
                        time.sleep(1)
                        # Forçar uma atualização mais robusta
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erro ao processar token: {e}")
            else:
                st.warning("Por favor, preencha todos os campos.")

    with register_tab:
        new_username = st.text_input("Novo nome de usuário", key="reg_username")
        full_name = st.text_input("Nome completo", key="reg_full_name")
        email = st.text_input("Email", key="reg_email")
        new_password = st.text_input("Nova senha", type="password", key="reg_password")

        if st.button("Registrar"):
            if new_username and full_name and email and new_password:
                result = register_user(new_username, full_name, email, new_password)
                if "error" in result:
                    st.error(result["error"])
                else:
                    # Armazenar informações de autenticação
                    st.session_state.token = result["access_token"]
                    st.session_state.username = new_username
                    # Decodificar o token para obter o user_id
                    try:
                        payload = jwt.decode(result["access_token"], options={"verify_signature": False})
                        st.session_state.user_id = int(payload["sub"])
                        st.success("Registro realizado com sucesso!")
                        # Pequeno delay para garantir a atualização da interface
                        import time
                        time.sleep(1)
                        # Forçar uma atualização mais robusta
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Erro ao processar token: {e}")
            else:
                st.warning("Por favor, preencha todos os campos.")

else:
    # Interface principal após autenticação
    st.title(f"🧠 Bem-vindo ao Sistema de IA, {st.session_state.username}!")

    # Botão de logout
    if st.sidebar.button("Logout", key="logout_btn"):
        logout()
        st.experimental_rerun()

    # Funções para interagir com a API (atualizadas para incluir token de autenticação)
    def query_system(query: str, owner_id: int, patient_id: int) -> Dict[str, Any]:
        """Consulta o sistema de IA"""
        url = "http://localhost:8000/query"
        payload = {
            "query": query,
            "owner_id": owner_id,  # Este deve ser o user_id do usuário logado
            "patient_id": patient_id,
            "use_openai": True
        }

        headers = {"Authorization": f"Bearer {st.session_state.token}"}

        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Erro {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": f"Erro de conexão: {str(e)}"}

    def add_document(owner_id: int, patient_id: int, title: str, text: str) -> Dict[str, Any]:
        """Adiciona um documento ao sistema"""
        url = "http://localhost:8000/add_document"
        payload = {
            "owner_id": owner_id,  # Este deve ser o user_id do usuário logado
            "patient_id": patient_id,
            "title": title,
            "text": text
        }

        headers = {"Authorization": f"Bearer {st.session_state.token}"}

        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Erro {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": f"Erro de conexão: {str(e)}"}

    def upload_document(owner_id: int, patient_id: int, file, title: str = None) -> Dict[str, Any]:
        """Faz upload de um documento para o sistema"""
        url = "http://localhost:8000/upload_document"

        files = {"file": (file.name, file, file.type)}
        data = {
            "owner_id": owner_id,  # Este deve ser o user_id do usuário logado
            "patient_id": patient_id,
            "title": title or file.name
        }

        headers = {"Authorization": f"Bearer {st.session_state.token}"}

        try:
            response = requests.post(url, files=files, data=data, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Erro {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": f"Erro de conexão: {str(e)}"}

    def get_patient_profile(owner_id: int, patient_id: int) -> Dict[str, Any]:
        """Obtém o perfil do paciente"""
        url = "http://localhost:8000/patient_profile"
        payload = {
            "owner_id": owner_id,  # Este deve ser o user_id do usuário logado
            "patient_id": patient_id
        }

        headers = {"Authorization": f"Bearer {st.session_state.token}"}

        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Erro {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": f"Erro de conexão: {str(e)}"}

    def run_assessment(query: str, owner_id: int, patient_id: int) -> Dict[str, Any]:
        """Executa uma avaliação clínica"""
        url = "http://localhost:8000/assessment"
        payload = {
            "query": query,
            "owner_id": owner_id,  # Este deve ser o user_id do usuário logado
            "patient_id": patient_id,
            "assessment_type": "clinical"
        }

        headers = {"Authorization": f"Bearer {st.session_state.token}"}

        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Erro {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": f"Erro de conexão: {str(e)}"}

    def health_check():
        """Verifica o status do sistema"""
        url = "http://localhost:8000/health"

        try:
            response = requests.get(url)
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Erro {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": f"Erro de conexão: {str(e)}"}

    # Barra lateral para navegação (só aparece após login)
    st.sidebar.title("Navegação")
    option = st.sidebar.selectbox(
        "Selecione uma funcionalidade:",
        ("Status do Sistema", "Consultar", "Adicionar Documento", "Upload de Documento", "Perfil do Paciente", "Avaliação Clínica")
    )

    # Verificar status do sistema
    if option == "Status do Sistema":
        st.header("✅ Status do Sistema")

        if st.button("Verificar Status", key="health_check_btn"):
            status = health_check()
            if "error" in status:
                st.error(f"Erro ao verificar status: {status['error']}")
            else:
                st.success("Sistema operacional!")
                st.json(status)

    # Consulta ao sistema
    elif option == "Consultar":
        st.header("🔍 Consultar Sistema de IA")

        query = st.text_input("Digite sua pergunta:")
        # Agora usar o ID do usuário logado
        owner_id = st.session_state.user_id  # O ID do usuário logado
        patient_id = st.text_input("ID do paciente:", value="exemplo")

        if st.button("Consultar", key="query_btn"):
            if query:
                with st.spinner("Processando consulta..."):
                    result = query_system(query, owner_id, patient_id)
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.subheader("Resposta:")
                        st.write(result.get("response", "Nenhuma resposta recebida"))

                        st.subheader("Detalhes:")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Documentos Recuperados", result.get("retrieved_documents_count", 0))
                        col2.metric("Tempo de Resposta (ms)", result.get("response_time_ms", 0))
                        col3.metric("Modelo Usado", result.get("model_used", "Desconhecido"))
            else:
                st.warning("Por favor, digite uma pergunta.")

    # Adicionar documento
    elif option == "Adicionar Documento":
        st.header("📝 Adicionar Documento Clínico")

        # Usar o ID do usuário logado
        owner_id = st.session_state.user_id  # O ID do usuário logado
        patient_id = st.number_input("ID do paciente:", min_value=1, value=1, step=1)
        title = st.text_input("Título do Documento:", value="Relatório Inicial")
        text = st.text_area("Texto do Documento:", height=200)

        if st.button("Adicionar Documento", key="add_doc_btn"):
            if text and title:
                with st.spinner("Adicionando documento..."):
                    result = add_document(owner_id, patient_id, title, text)
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.success("Documento adicionado com sucesso!")
                        st.json(result)
            else:
                st.warning("Por favor, preencha o título e o texto do documento.")

    # Upload de documento
    elif option == "Upload de Documento":
        st.header("📁 Upload de Documento Clínico")

        # Usar o ID do usuário logado
        owner_id = st.session_state.user_id  # O ID do usuário logado
        patient_id = st.number_input("ID do paciente:", min_value=1, value=1, step=1)
        title = st.text_input("Título do Documento (opcional):", value="")
        uploaded_file = st.file_uploader(
            "Escolha um documento para fazer upload",
            type=['pdf', 'docx', 'doc', 'txt', 'csv'],
            help="Formatos suportados: PDF, DOCX, DOC, TXT, CSV"
        )

        if st.button("Upload Documento", key="upload_doc_btn") and uploaded_file is not None:
            with st.spinner("Processando e adicionando documento..."):
                result = upload_document(owner_id, patient_id, uploaded_file, title)
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.success("Documento enviado e processado com sucesso!")
                    st.json(result)
        elif st.button("Upload Documento", key="upload_doc_btn_warn") and uploaded_file is None:
            st.warning("Por favor, selecione um arquivo para upload.")

    # Perfil do paciente
    elif option == "Perfil do Paciente":
        st.header("👤 Perfil do Paciente")

        # Usar o ID do usuário logado
        owner_id = st.session_state.user_id  # O ID do usuário logado
        patient_id = st.text_input("ID do paciente:", value="exemplo")

        if st.button("Obter Perfil", key="get_profile_btn"):
            with st.spinner("Recuperando perfil..."):
                result = get_patient_profile(owner_id, patient_id)
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.subheader("Informações do Paciente:")
                    st.json(result)

    # Avaliação clínica
    elif option == "Avaliação Clínica":
        st.header("📊 Avaliação Clínica")

        query = st.text_area("Descrição da avaliação:")
        # Usar o ID do usuário logado
        owner_id = st.session_state.user_id  # O ID do usuário logado
        patient_id = st.text_input("ID do paciente:", value="exemplo")

        if st.button("Executar Avaliação", key="run_assessment_btn"):
            if query:
                with st.spinner("Executando avaliação..."):
                    result = run_assessment(query, owner_id, patient_id)
                    if "error" in result:
                        st.error(result["error"])
                    else:
                        st.subheader("Resultado da Avaliação:")
                        st.write(result.get("response", "Nenhuma resposta recebida"))

                        st.subheader("Detalhes:")
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Tipo de Avaliação", result.get("assessment_type", "Desconhecido"))
                        col2.metric("Evidências Recuperadas", result.get("retrieved_evidence", 0))
                        col3.metric("Confiança", f"{result.get('confidence_score', 0):.2f}")
            else:
                st.warning("Por favor, descreva a avaliação.")

    # Informações sobre o sistema
    st.sidebar.markdown("---")
    st.sidebar.info(
        "Este é o frontend para o Sistema de IA para Psicopedagogia Clínica.\n\n"
        "A API deve estar rodando em `http://localhost:8000` para que este frontend funcione corretamente."
    )

    st.sidebar.markdown("---")
    st.sidebar.caption(
        f"Usuário logado: {st.session_state.username}\n\n"
        "Sistema desenvolvido para auxiliar psicopedagogos clínicos "
        "com tecnologia de última geração em IA."
    )