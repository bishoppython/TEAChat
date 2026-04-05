"""
Frontend Flask para o Sistema de IA para Psicopedagogia Clínica
"""
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import requests
import os
from datetime import timedelta
import jwt
import logging

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-this-in-production-flask-key")
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuração da API Backend
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Decorator para rotas que requerem autenticação
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'token' not in session or 'user_id' not in session:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        
        # Verificar se o token ainda é válido
        try:
            jwt.decode(session['token'], options={"verify_signature": False})
        except jwt.ExpiredSignatureError:
            session.clear()
            flash('Sua sessão expirou. Por favor, faça login novamente.', 'warning')
            return redirect(url_for('login'))
        except jwt.InvalidTokenError:
            session.clear()
            flash('Sessão inválida. Por favor, faça login novamente.', 'warning')
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function

def refresh_access_token():
    """Função para atualizar o access token usando o refresh token"""
    if 'refresh_token' not in session:
        return False

    try:
        url = f"{API_BASE_URL}/refresh"
        headers = {'Content-Type': 'application/json'}
        data = {'refresh_token': session['refresh_token']}

        response = requests.post(url, json=data, headers=headers)

        if response and response.status_code == 200:
            tokens = response.json()
            session['token'] = tokens['access_token']
            session['refresh_token'] = tokens['refresh_token']
            return True
        else:
            # Se o refresh token também expirou ou é inválido, limpar a sessão
            session.clear()
            return False
    except Exception as e:
        logger.error(f"Erro ao atualizar token: {str(e)}")
        return False

# Função auxiliar para fazer requisições autenticadas
def make_api_request(method, endpoint, data=None, files=None):
    """Faz requisições para a API com autenticação"""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {}

    if 'token' in session:
        headers['Authorization'] = f"Bearer {session['token']}"

    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        elif method == 'POST':
            if files:
                # Para uploads de arquivos, não definimos Content-Type manualmente
                # pois ele será definido automaticamente pelo requests com boundary
                response = requests.post(url, data=data, files=files, headers=headers)
            else:
                # Adicionar cabeçalhos padrão para segurança e identificação apenas para requisições sem arquivos
                if 'Content-Type' not in headers and method in ['POST', 'PUT', 'PATCH']:
                    headers['Content-Type'] = 'application/json'
                response = requests.post(url, json=data, headers=headers)
        elif method == 'PUT':
            # Adicionar cabeçalhos padrão para segurança e identificação apenas para requisições sem arquivos
            if 'Content-Type' not in headers and method in ['POST', 'PUT', 'PATCH']:
                headers['Content-Type'] = 'application/json'
            response = requests.put(url, json=data, headers=headers)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        else:
            return None

        # Se receber erro 401, tentar atualizar o token e refazer a requisição
        if response.status_code == 401:
            # Tentar atualizar o token
            if refresh_access_token():
                # Se atualizado com sucesso, refazer a requisição com o novo token
                headers['Authorization'] = f"Bearer {session['token']}"

                if method == 'GET':
                    response = requests.get(url, headers=headers)
                elif method == 'POST':
                    if files:
                        # Para uploads de arquivos, não definimos Content-Type manualmente
                        response = requests.post(url, data=data, files=files, headers=headers)
                    else:
                        # Adicionar cabeçalhos padrão para segurança e identificação apenas para requisições sem arquivos
                        temp_headers = headers.copy()
                        if 'Content-Type' not in temp_headers and method in ['POST', 'PUT', 'PATCH']:
                            temp_headers['Content-Type'] = 'application/json'
                        response = requests.post(url, json=data, headers=temp_headers)
                elif method == 'PUT':
                    # Adicionar cabeçalhos padrão para segurança e identificação apenas para requisições sem arquivos
                    temp_headers = headers.copy()
                    if 'Content-Type' not in temp_headers and method in ['POST', 'PUT', 'PATCH']:
                        temp_headers['Content-Type'] = 'application/json'
                    response = requests.put(url, json=data, headers=temp_headers)
                elif method == 'DELETE':
                    response = requests.delete(url, headers=headers)

        return response
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição para {url}: {str(e)}")
        return None

# Rotas de autenticação
@app.route('/')
def index():
    """Página inicial - redireciona baseado no estado de autenticação"""
    if 'token' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Por favor, preencha todos os campos.', 'danger')
            return render_template('login.html')
        
        # Fazer login na API
        response = make_api_request('POST', '/login', {
            'username': username,
            'password': password
        })
        
        if response and response.status_code == 200:
            data = response.json()
            session.permanent = True
            session['token'] = data['access_token']
            session['refresh_token'] = data['refresh_token']  # Armazenar refresh token
            session['username'] = username

            # Decodificar token para obter user_id
            try:
                payload = jwt.decode(data['access_token'], options={"verify_signature": False})
                session['user_id'] = int(payload['sub'])

                # O nome completo do usuário deve estar disponível no contexto de login
                # mas não há uma rota direta para obtê-lo após o login
                # então mantemos o username como fallback
                session['full_name'] = username

                flash(f'Bem-vindo, {username}!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                flash('Erro ao processar autenticação.', 'danger')
        else:
            flash('Nome de usuário ou senha incorretos.', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Página de registro"""
    if request.method == 'POST':
        username = request.form.get('username')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'therapist')  # Pega o papel profissional ou usa 'therapist' como padrão

        if not all([username, full_name, email, password, confirm_password, role]):
            flash('Por favor, preencha todos os campos.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('As senhas não coincidem.', 'danger')
            return render_template('register.html')

        # Registrar na API
        response = make_api_request('POST', '/register', {
            'username': username,
            'full_name': full_name,
            'email': email,
            'password': password,
            'role': role
        })
        
        if response and response.status_code == 200:
            data = response.json()
            session.permanent = True
            session['token'] = data['access_token']
            session['refresh_token'] = data['refresh_token']  # Armazenar refresh token
            session['username'] = username

            # Decodificar token para obter user_id
            try:
                payload = jwt.decode(data['access_token'], options={"verify_signature": False})
                session['user_id'] = int(payload['sub'])

                # Armazenar o nome completo do usuário na sessão
                session['full_name'] = full_name  # O nome completo foi fornecido no formulário de registro

                flash('Registro realizado com sucesso!', 'success')
                return redirect(url_for('dashboard'))
            except Exception as e:
                flash('Erro ao processar registro.', 'danger')
        else:
            error_message = 'Erro ao registrar usuário.'
            if response:
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', error_message)
                except:
                    pass
            flash(error_message, 'danger')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """Faz logout do usuário"""
    session.clear()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('login'))

@app.route('/refresh_user_cache', methods=['POST'])
@login_required
def refresh_user_cache():
    """Endpoint para atualizar o cache de dados do usuário"""
    try:
        response = make_api_request('POST', f'/user/{session["user_id"]}/refresh_cache')
        if response and response.status_code == 200:
            return jsonify({'success': True, 'message': 'Cache atualizado com sucesso'})
        else:
            return jsonify({'success': False, 'message': 'Falha ao atualizar cache'}), 500
    except Exception as e:
        logger.error(f"Erro ao atualizar cache do usuário: {e}")
        return jsonify({'success': False, 'message': 'Erro interno ao atualizar cache'}), 500

@app.route('/refresh_token', methods=['POST'])
@login_required
def refresh_token():
    """Endpoint para atualizar o token manualmente (se necessário)"""
    success = refresh_access_token()
    if success:
        return jsonify({'success': True, 'message': 'Token atualizado com sucesso'})
    else:
        session.clear()
        return jsonify({'success': False, 'message': 'Falha ao atualizar token, faça login novamente'}), 401

# Rotas principais do sistema
@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard principal"""
    # Buscar estatísticas do usuário
    response = make_api_request('GET', f"/api/user/{session['user_id']}/stats")
    stats = {}
    if response and response.status_code == 200:
        stats = response.json().get('statistics', {})

    # Buscar pacientes do usuário
    patients_response = make_api_request('GET', '/patients/list')
    if patients_response and patients_response.status_code == 200:
        patients_data = patients_response.json()
        patients = patients_data.get('patients', [])

        # Processar os pacientes para garantir consistência de formato
        processed_patients = []
        for patient in patients:
            patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
            processed_patients.append({
                'id': patient.get('id'),
                'name': patient_name if patient_name else f"Paciente {patient.get('id', 'N/A')}",
                'first_name': patient.get('first_name', ''),
                'last_name': patient.get('last_name', ''),
                'age': patient.get('age', 'N/A'),
                'diagnosis': patient.get('diagnosis', 'N/A')
            })

        # Adicionar os pacientes ao dicionário de estatísticas
        stats['patients'] = processed_patients
    else:
        stats['patients'] = []

    return render_template('dashboard.html', username=session['username'], stats=stats)

@app.route('/query', methods=['GET', 'POST'])
@login_required
def query():
    """Página de consulta ao sistema"""
    # Obter pacientes diretamente no backend
    patients_response = make_api_request('GET', '/patients/list')
    patients = []
    if patients_response and patients_response.status_code == 200:
        patients_data = patients_response.json()
        patients = patients_data.get('patients', [])

    result = None

    if request.method == 'POST':
        try:
            query_text = request.form.get('query')
            patient_id = request.form.get('patient_id', 'exemplo')

            if not query_text:
                flash('Por favor, digite uma pergunta.', 'warning')
            else:
                # Log para depuração
                logger.info(f"Recebido patient_id na consulta: '{patient_id}' (tipo: {type(patient_id)})")

                # Para a query, se for 'exemplo', envia como string, senão converte para inteiro
                if patient_id == 'exemplo':
                    patient_id_to_send = patient_id  # 'exemplo' é uma string válida para este endpoint
                else:
                    try:
                        patient_id_to_send = int(patient_id)
                        logger.info(f"patient_id convertido com sucesso: {patient_id_to_send}")
                    except ValueError:
                        logger.error(f"Valor inválido para patient_id na consulta: '{patient_id}' (tipo: {type(patient_id)})")
                        flash('ID do paciente inválido. Por favor, selecione um paciente válido.', 'danger')
                        return render_template('query.html', result=result, patients=patients)

                logger.info(f"Enviando para o backend - patient_id: {patient_id_to_send}, owner_id: {session['user_id']}")

                response = make_api_request('POST', '/query', {
                    'query': query_text,
                    'owner_id': session['user_id'],
                    'patient_id': patient_id_to_send,
                    'use_openai': True,
                    'k': 4,
                    'min_similarity': 0.1
                })

                if response and response.status_code == 200:
                    result = response.json()
                else:
                    flash('Erro ao processar consulta.', 'danger')
        except Exception as e:
            logger.error(f"Erro ao processar consulta: {str(e)}")
            flash('Erro ao processar consulta.', 'danger')

    return render_template('query.html', result=result, patients=patients)

@app.route('/documents', methods=['GET', 'POST'])
@login_required
def documents():
    """Página para adicionar documentos"""
    # Obter informações do usuário para passar ao template
    # Usar o nome completo armazenado na sessão, ou o username como fallback
    full_name = session.get('full_name', session.get('username', 'Profissional'))
    user_info = {'full_name': full_name}

    # Obter pacientes diretamente no backend
    patients_response = make_api_request('GET', '/patients/list')
    patients = []
    if patients_response and patients_response.status_code == 200:
        patients_data = patients_response.json()
        patients = patients_data.get('patients', [])

    if request.method == 'POST':
        title = request.form.get('title')
        text = request.form.get('text')
        patient_id = request.form.get('patient_id')

        if not all([title, text, patient_id]):
            flash('Por favor, preencha todos os campos.', 'warning')
        else:
            # Validar que patient_id é um número antes de converter
            try:
                patient_id_int = int(patient_id)
            except ValueError:
                logger.error(f"Valor inválido para patient_id: '{patient_id}' (tipo: {type(patient_id)})")
                flash('ID do paciente inválido. Por favor, selecione um paciente válido.', 'danger')
                return render_template('documents.html', user_info=user_info, patients=patients)

            response = make_api_request('POST', '/add_document', {
                'owner_id': session['user_id'],
                'patient_id': patient_id_int,
                'title': title,
                'text': text,
                'source_type': 'note'
            })

            if response and response.status_code == 200:
                data = response.json()
                flash(f'Documento adicionado com sucesso! {len(data["document_chunk_ids"])} chunks criados.', 'success')
            else:
                flash('Erro ao adicionar documento.', 'danger')

    return render_template('documents.html', user_info=user_info, patients=patients)

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Página para upload de documentos"""
    # Obter pacientes diretamente no backend
    patients_response = make_api_request('GET', '/patients/list')
    patients = []
    if patients_response and patients_response.status_code == 200:
        patients_data = patients_response.json()
        patients = patients_data.get('patients', [])

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Nenhum arquivo selecionado.', 'warning')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('Nenhum arquivo selecionado.', 'warning')
            return redirect(request.url)

        patient_id = request.form.get('patient_id')
        title = request.form.get('title', file.filename)

        if not patient_id:
            flash('Por favor, informe o ID do paciente.', 'warning')
            return render_template('upload.html', patients=patients)

        # Validar que patient_id é um número antes de converter
        try:
            patient_id_int = int(patient_id)
        except ValueError:
            logger.error(f"Valor inválido para patient_id no upload: '{patient_id}' (tipo: {type(patient_id)})")
            flash('ID do paciente inválido. Por favor, selecione um paciente válido.', 'danger')
            return render_template('upload.html', patients=patients)

        # Debug: imprimir o valor convertido
        debug_msg = f"DEBUG FRONTEND: patient_id original: {patient_id}, patient_id_int: {patient_id_int}, tipo: {type(patient_id_int)}"
        print(debug_msg)
        logger.info(debug_msg)  # Adicionando log para garantir que apareça no terminal

        # Preparar dados para upload
        files = {'file': (file.filename, file.stream, file.content_type)}
        # Enviar os dados como formulário em vez de JSON para compatibilidade com upload de arquivos
        data = {
            'owner_id': str(session['user_id']),  # Converter para string explicitamente
            'patient_id': str(patient_id_int),   # Converter para string para o formulário
            'title': title,
            'source_type': 'uploaded_file'  # Definir explicitamente o valor padrão
        }

        debug_msg2 = f"DEBUG FRONTEND: Enviando dados para upload - data: {data}, files: {files}"
        print(debug_msg2)
        logger.info(debug_msg2)

        response = make_api_request('POST', '/upload_document', data=data, files=files)

        if response and response.status_code == 200:
            result = response.json()
            flash(f'Arquivo enviado com sucesso! {len(result["document_chunk_ids"])} chunks criados.', 'success')
        else:
            flash('Erro ao fazer upload do arquivo.', 'danger')

    return render_template('upload.html', patients=patients)

@app.route('/patient/<int:patient_id>')
@login_required
def patient_profile(patient_id):
    """Página de perfil do paciente - atualizado para usar o novo endpoint"""
    try:
        # Usar o novo endpoint que retorna os detalhes completos do paciente
        response = make_api_request('GET', f'/patient/{patient_id}')

        patient_data = None
        if response and response.status_code == 200:
            patient_data = response.json()
            # Converter o paciente para o formato antigo esperado pelo template
            patient = patient_data.get('patient', {})

            # Obter perfil do paciente para informações adicionais
            profile_response = make_api_request('POST', '/patient_profile', {
                'owner_id': session['user_id'],
                'patient_id': patient_id
            })

            profile_data = {'sensitivities': [], 'documents_count': 0, 'patient_info': {}}
            if profile_response and profile_response.status_code == 200:
                profile_data = profile_response.json()

            # Combinar as informações do novo endpoint com o perfil antigo
            full_profile = {
                'patient_info': {
                    'id': patient.get('id'),
                    'name': f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip(),
                    'first_name': patient.get('first_name', ''),
                    'last_name': patient.get('last_name', ''),
                    'age': patient.get('age', 'Não informado'),
                    'birth_date': patient.get('birth_date', 'Não informado'),
                    'diagnosis': patient.get('diagnosis', 'Não informado'),
                    'neurotype': patient.get('neurotype', 'Não informado'),
                    'level': patient.get('level', 'Não informado'),
                    'description': patient.get('description', 'Não informado'),
                    'created_at': patient.get('created_at', 'Não informado')
                },
                'sensitivities': profile_data.get('sensitivities', []),
                'documents_count': profile_data.get('documents_count', 0)
            }
        else:
            flash('Erro ao carregar perfil do paciente.', 'danger')
            return redirect(url_for('dashboard'))

        return render_template('patient_profile.html', patient_id=patient_id, profile=full_profile)
    except Exception as e:
        logger.error(f"Erro ao carregar perfil do paciente {patient_id}: {str(e)}")
        flash('Erro ao carregar perfil do paciente.', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/api/patient/<patient_id>')
@login_required
def get_patient_info(patient_id):
    """API para obter informações básicas do paciente"""
    try:
        # Fazer uma requisição para o backend para obter informações do paciente
        patient_response = make_api_request('POST', '/patient_profile', {
            'owner_id': session['user_id'],
            'patient_id': patient_id
        })

        if patient_response and patient_response.status_code == 200:
            patient_data = patient_response.json()
            patient_info = patient_data.get('patient_info', {})
            return jsonify({
                'id': patient_id,
                'name': patient_info.get('name', f'Paciente {patient_id}'),
                'first_name': patient_info.get('first_name', ''),
                'last_name': patient_info.get('last_name', ''),
                'found': True
            })
        else:
            return jsonify({
                'id': patient_id,
                'name': f'Paciente {patient_id}',
                'found': False
            })
    except Exception as e:
        logger.error(f"Erro ao obter informações do paciente {patient_id}: {str(e)}")
        return jsonify({
            'id': patient_id,
            'name': f'Paciente {patient_id}',
            'found': False
        })

@app.route('/api/user/<user_id>/patients')
@login_required
def get_user_patients(user_id):
    """Rota proxy para obter pacientes do usuário - para uso no frontend"""
    try:
        # Verificar se o usuário está tentando acessar seus próprios dados
        if int(user_id) != session['user_id']:
            return jsonify({'error': 'Acesso não autorizado'}), 403

        # Fazer requisição para o backend para obter lista de pacientes
        response = make_api_request('GET', f'/patients/list')

        if response and response.status_code == 200:
            data = response.json()
            patients = data.get('patients', [])

            # Debug: log para ver a estrutura dos dados retornados
            logger.debug(f"Dados de pacientes retornados para user {user_id}: {patients}")

            # Processar os pacientes para garantir que tenhamos o formato correto
            processed_patients = []
            for patient in patients:
                # Usar os campos diretamente do registro do banco de dados
                patient_id = patient.get('id')
                patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()

                if patient_id is not None:
                    processed_patients.append({
                        'id': patient_id,
                        'name': patient_name if patient_name else f"Paciente {patient_id}",
                        'first_name': patient.get('first_name', ''),
                        'last_name': patient.get('last_name', ''),
                        'age': patient.get('age', 'N/A'),
                        'diagnosis': patient.get('diagnosis', 'N/A')
                    })
                else:
                    logger.warning(f"Paciente sem ID encontrado: {patient}")

            logger.debug(f"Pacientes processados: {processed_patients}")

            return jsonify({
                'patients': processed_patients,
                'total': len(processed_patients)
            })
        else:
            logger.error(f"Erro ao obter lista de pacientes do usuário {user_id}: {response.status_code if response else 'No response'}")
            return jsonify({'error': 'Falha ao obter lista de pacientes'}), 500
    except Exception as e:
        logger.error(f"Erro ao obter pacientes do usuário {user_id}: {str(e)}")
        return jsonify({'error': 'Erro interno'}), 500

@app.route('/assessment', methods=['GET', 'POST'])
@login_required
def assessment():
    """Página de avaliação clínica"""
    # Obter pacientes diretamente no backend
    patients_response = make_api_request('GET', '/patients/list')
    patients = []
    if patients_response and patients_response.status_code == 200:
        patients_data = patients_response.json()
        patients = patients_data.get('patients', [])

    result = None

    if request.method == 'POST':
        query_text = request.form.get('query')
        patient_id = request.form.get('patient_id')
        assessment_type = request.form.get('assessment_type', 'clinical')

        if not all([query_text, patient_id]):
            flash('Por favor, preencha todos os campos.', 'warning')
        else:
            # Log para depuração
            logger.info(f"Recebido patient_id na avaliação: '{patient_id}' (tipo: {type(patient_id)})")

            # Para a avaliação, se for 'exemplo', envia como string, senão converte para inteiro
            if patient_id == 'exemplo':
                patient_id_to_send = patient_id  # 'exemplo' é uma string válida para este endpoint
            else:
                try:
                    patient_id_to_send = int(patient_id)
                    logger.info(f"patient_id convertido com sucesso: {patient_id_to_send}")
                except ValueError:
                    logger.error(f"Valor inválido para patient_id na avaliação: '{patient_id}' (tipo: {type(patient_id)})")
                    flash('ID do paciente inválido. Por favor, selecione um paciente válido.', 'danger')
                    return render_template('assessment.html', result=result, patients=patients)

            logger.info(f"Enviando para o backend - patient_id: {patient_id_to_send}, owner_id: {session['user_id']}")

            response = make_api_request('POST', '/assessment', {
                'query': query_text,
                'owner_id': session['user_id'],
                'patient_id': patient_id_to_send,
                'assessment_type': assessment_type
            })

            if response and response.status_code == 200:
                result = response.json()
            else:
                flash('Erro ao executar avaliação.', 'danger')

    return render_template('assessment.html', result=result, patients=patients)

@app.route('/patient_register', methods=['GET', 'POST'])
@login_required
def patient_register():
    """Página para cadastro de novos pacientes"""
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        date_of_birth = request.form.get('date_of_birth')  # Corrigido para o nome correto
        age = request.form.get('age')
        diagnosis = request.form.get('diagnosis')
        neurotype = request.form.get('neurotype', '')
        level = request.form.get('level', '')
        description = request.form.get('description', '')
        sensitivities_description = request.form.get('sensitivities_description', '')

        if not all([first_name, last_name, date_of_birth, age, diagnosis]):
            flash('Por favor, preencha todos os campos obrigatórios.', 'warning')
            return render_template('patient_register.html')

        # Validar formato da data
        try:
            from datetime import datetime
            # Tenta converter a data para verificar o formato
            datetime.strptime(date_of_birth, '%Y-%m-%d')
        except ValueError:
            flash('Formato de data inválido. Use o formato YYYY-MM-DD.', 'danger')
            return render_template('patient_register.html')

        try:
            age_int = int(age)
            if age_int < 0 or age_int > 150:
                flash('Idade deve ser um número entre 0 e 150.', 'danger')
                return render_template('patient_register.html')
        except ValueError:
            flash('Idade deve ser um número válido.', 'danger')
            return render_template('patient_register.html')

        # Criar paciente no backend
        response = make_api_request('POST', '/patient/create', {
            'owner_id': session['user_id'],
            'first_name': first_name,
            'last_name': last_name,
            'date_of_birth': date_of_birth,  # Corrigido para o nome correto
            'age': age_int,
            'diagnosis': diagnosis,
            'neurotype': neurotype,
            'level': level,
            'description': description
        })

        if response and response.status_code == 200:
            data = response.json()
            patient_id = data["patient_id"]
            flash(f'Paciente {first_name} {last_name} cadastrado com sucesso! ID: {patient_id}', 'success')

            # Processar e adicionar sensibilidades se fornecidas
            sensitivity_types = request.form.getlist('sensitivity_types[]')
            sensitivity_levels = request.form.getlist('sensitivity_levels[]')
            sensitivity_descriptions = request.form.getlist('sensitivity_descriptions[]')

            # Adicionar sensibilidade geral se fornecida
            if sensitivities_description.strip():
                sensitivity_response = make_api_request('POST', '/patient/add_sensitivity', {
                    'owner_id': session['user_id'],
                    'patient_id': patient_id,
                    'sensitivity_type': 'Geral',
                    'sensitivity_level': 'Médio',
                    'description': sensitivities_description
                })
                if sensitivity_response and sensitivity_response.status_code == 200:
                    logger.info(f"Sensibilidade geral adicionada para o paciente {patient_id}")
                else:
                    logger.error(f"Erro ao adicionar sensibilidade geral para o paciente {patient_id}")

            # Processar sensibilidades detalhadas
            for i in range(len(sensitivity_types)):
                if i < len(sensitivity_levels) and i < len(sensitivity_descriptions):
                    sensitivity_type = sensitivity_types[i]
                    sensitivity_level = sensitivity_levels[i]
                    sensitivity_desc = sensitivity_descriptions[i]

                    # Apenas adicionar se todos os campos estiverem preenchidos e não forem valores de teste
                    if sensitivity_type and sensitivity_level and sensitivity_desc:
                        # Filtrar valores indesejados como "Sensibilidade de teste" ou "Não se aplica"
                        if sensitivity_desc.lower() not in ['sensibilidade de teste', 'não se aplica', 'não se aplica.'] and sensitivity_type.lower() != 'não se aplica':
                            sensitivity_response = make_api_request('POST', '/patient/add_sensitivity', {
                                'owner_id': session['user_id'],
                                'patient_id': patient_id,
                                'sensitivity_type': sensitivity_type,
                                'sensitivity_level': sensitivity_level,
                                'description': sensitivity_desc
                            })

                            if sensitivity_response and sensitivity_response.status_code == 200:
                                logger.info(f"Sensibilidade {sensitivity_type} adicionada para o paciente {patient_id}")
                            else:
                                logger.error(f"Erro ao adicionar sensibilidade {sensitivity_type} para o paciente {patient_id}")

            # Atualizar o cache do usuário para garantir que o novo paciente apareça nas listas
            cache_response = make_api_request('POST', f'/user/{session["user_id"]}/refresh_cache')
            if cache_response and cache_response.status_code == 200:
                logger.info("Cache do usuário atualizado após cadastro de paciente")
            else:
                logger.warning("Falha ao atualizar cache do usuário após cadastro de paciente")

            return redirect(url_for('dashboard'))
        else:
            error_message = 'Erro ao cadastrar paciente.'
            if response:
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', error_message)
                except Exception as e:
                    logger.error(f"Erro ao processar resposta do backend: {e}")
                    pass
            flash(error_message, 'danger')

    return render_template('patient_register.html')

@app.route('/history')
@login_required
def history():
    """Página principal de histórico"""
    # Obter estatísticas do histórico usando o novo endpoint otimizado
    try:
        # Obter estatísticas de histórico diretamente do endpoint otimizado
        stats_response = make_api_request('GET', '/history/stats')
        if stats_response and stats_response.status_code == 200:
            stats = stats_response.json().get('stats', {})
        else:
            # Fallback para valores padrão em caso de erro
            stats = {
                'queries_count': 0,
                'assessments_count': 0,
                'uploads_count': 0,
                'documents_count': 0
            }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas do histórico: {e}")
        stats = {
            'queries_count': 0,
            'assessments_count': 0,
            'uploads_count': 0,
            'documents_count': 0
        }

    return render_template('history.html', stats=stats)


@app.route('/history/queries')
@login_required
def history_queries():
    """Página de histórico de consultas"""
    # Obter pacientes do usuário para o filtro
    patients_response = make_api_request('GET', f'/api/user/{session["user_id"]}/patients')
    patients = []
    if patients_response and patients_response.status_code == 200:
        patients = patients_response.json().get('patients', [])

    # Obter parâmetros de filtragem
    patient_id = request.args.get('patient_id', type=int)
    limit = request.args.get('limit', default=10, type=int)
    offset = request.args.get('offset', default=0, type=int)

    # Construir string de consulta para a URL
    query_params = f'?limit={limit}&offset={offset}'
    if patient_id:
        query_params += f'&patient_id={patient_id}'

    # Obter histórico de consultas
    queries_response = make_api_request('GET', f'/history/queries{query_params}')
    queries = []
    total = 0
    if queries_response and queries_response.status_code == 200:
        data = queries_response.json()
        queries = data.get('assessments', [])  # Usando o mesmo nome da resposta do endpoint
        total = data.get('total', len(queries))

    return render_template('history_queries.html',
                           queries=queries,
                           total=total,
                           limit=limit,
                           patients=patients)

@app.route('/history/assessments')
@login_required
def history_assessments():
    """Página de histórico de avaliações clínicas"""
    # Obter pacientes do usuário para o filtro
    patients_response = make_api_request('GET', f'/api/user/{session["user_id"]}/patients')
    patients = []
    if patients_response and patients_response.status_code == 200:
        patients = patients_response.json().get('patients', [])

    # Obter parâmetros de filtragem
    patient_id = request.args.get('patient_id', type=int)
    limit = request.args.get('limit', default=10, type=int)
    offset = request.args.get('offset', default=0, type=int)

    # Construir string de consulta para a URL
    query_params = f'?limit={limit}&offset={offset}'
    if patient_id:
        query_params += f'&patient_id={patient_id}'

    # Obter histórico de avaliações
    assessments_response = make_api_request('GET', f'/history/assessments{query_params}')
    assessments = []
    total = 0
    if assessments_response and assessments_response.status_code == 200:
        data = assessments_response.json()
        assessments = data.get('assessments', [])
        total = data.get('total', len(assessments))

    return render_template('history_assessments.html',
                           assessments=assessments,
                           total=total,
                           limit=limit,
                           patients=patients)

@app.route('/history/uploads')
@login_required
def history_uploads():
    """Página de histórico de uploads"""
    # Obter pacientes do usuário para o filtro
    patients_response = make_api_request('GET', f'/api/user/{session["user_id"]}/patients')
    patients = []
    if patients_response and patients_response.status_code == 200:
        patients = patients_response.json().get('patients', [])

    # Obter parâmetros de filtragem
    patient_id = request.args.get('patient_id', type=int)
    status = request.args.get('status', default='active')
    limit = request.args.get('limit', default=10, type=int)
    offset = request.args.get('offset', default=0, type=int)

    # Construir string de consulta para a URL
    query_params = f'?status={status}&limit={limit}&offset={offset}'
    if patient_id:
        query_params += f'&patient_id={patient_id}'

    # Obter histórico de uploads
    uploads_response = make_api_request('GET', f'/history/uploads{query_params}')
    uploads = []
    total = 0
    if uploads_response and uploads_response.status_code == 200:
        data = uploads_response.json()
        uploads = data.get('uploads', [])
        total = data.get('total', len(uploads))

    return render_template('history_uploads.html',
                           uploads=uploads,
                           total=total,
                           limit=limit,
                           patients=patients)

@app.route('/history/documents')
@login_required
def history_documents():
    """Página de histórico de documentos"""
    # Obter pacientes do usuário para o filtro
    patients_response = make_api_request('GET', f'/api/user/{session["user_id"]}/patients')
    patients = []
    if patients_response and patients_response.status_code == 200:
        patients = patients_response.json().get('patients', [])

    # Obter parâmetros de filtragem
    patient_id = request.args.get('patient_id', type=int)
    action_type = request.args.get('action_type', default='')
    limit = request.args.get('limit', default=10, type=int)
    offset = request.args.get('offset', default=0, type=int)

    # Construir string de consulta para a URL
    query_params = f'?limit={limit}&offset={offset}'
    if patient_id:
        query_params += f'&patient_id={patient_id}'
    if action_type:
        query_params += f'&action_type={action_type}'

    # Obter histórico de documentos
    documents_response = make_api_request('GET', f'/history/documents{query_params}')
    documents = []
    total = 0
    if documents_response and documents_response.status_code == 200:
        data = documents_response.json()
        documents = data.get('documents', [])
        total = data.get('total', len(documents))

    return render_template('history_documents.html',
                           documents=documents,
                           total=total,
                           limit=limit,
                           patients=patients)

@app.route('/api/history/assessments/<int:assessment_id>', methods=['DELETE'])
@login_required
def api_delete_assessment(assessment_id):
    """Endpoint para excluir avaliação via API (chamado pelo JavaScript)"""
    try:
        response = make_api_request('DELETE', f'/history/assessments/{assessment_id}')
        if response and response.status_code == 200:
            return jsonify({'success': True, 'message': 'Avaliação excluída com sucesso'})
        else:
            error_message = 'Erro ao excluir avaliação'
            if response:
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', error_message)
                except:
                    pass
            return jsonify({'success': False, 'message': error_message}), 400
    except Exception as e:
        logger.error(f"Erro ao excluir avaliação via API: {e}")
        return jsonify({'success': False, 'message': 'Erro interno ao excluir avaliação'}), 500

@app.route('/api/history/queries/<int:query_id>', methods=['PUT'])
@login_required
def api_update_query(query_id):
    """Endpoint para atualizar consulta via API (chamado pelo JavaScript)"""
    try:
        query_text = request.form.get('query_text')
        response_text = request.form.get('response')

        # Preparar dados para envio
        data = {}
        if query_text is not None:
            data['query_text'] = query_text
        if response_text is not None:
            data['response'] = response_text

        response = make_api_request('PUT', f'/history/queries/{query_id}', data=data)
        if response and response.status_code == 200:
            return jsonify({'success': True, 'message': 'Consulta atualizada com sucesso'})
        else:
            error_message = 'Erro ao atualizar consulta'
            if response:
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', error_message)
                except:
                    pass
            return jsonify({'success': False, 'message': error_message}), 400
    except Exception as e:
        logger.error(f"Erro ao atualizar consulta via API: {e}")
        return jsonify({'success': False, 'message': 'Erro interno ao atualizar consulta'}), 500

@app.route('/api/history/queries/<int:query_id>', methods=['DELETE'])
@login_required
def api_delete_query(query_id):
    """Endpoint para excluir consulta via API (chamado pelo JavaScript)"""
    try:
        response = make_api_request('DELETE', f'/history/queries/{query_id}')
        if response and response.status_code == 200:
            return jsonify({'success': True, 'message': 'Consulta excluída com sucesso'})
        else:
            error_message = 'Erro ao excluir consulta'
            if response:
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', error_message)
                except:
                    pass
            return jsonify({'success': False, 'message': error_message}), 400
    except Exception as e:
        logger.error(f"Erro ao excluir consulta via API: {e}")
        return jsonify({'success': False, 'message': 'Erro interno ao excluir consulta'}), 500

@app.route('/api/history/uploads/<int:upload_id>', methods=['PUT'])
@login_required
def api_update_upload(upload_id):
    """Endpoint para atualizar upload via API (chamado pelo JavaScript)"""
    try:
        title = request.form.get('title')

        # Preparar dados para envio
        data = {}
        if title:
            data['title'] = title

        response = make_api_request('PUT', f'/history/uploads/{upload_id}', data=data)
        if response and response.status_code == 200:
            return jsonify({'success': True, 'message': 'Upload atualizado com sucesso'})
        else:
            error_message = 'Erro ao atualizar upload'
            if response:
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', error_message)
                except:
                    pass
            return jsonify({'success': False, 'message': error_message}), 400
    except Exception as e:
        logger.error(f"Erro ao atualizar upload via API: {e}")
        return jsonify({'success': False, 'message': 'Erro interno ao atualizar upload'}), 500

@app.route('/api/history/uploads/<int:upload_id>', methods=['DELETE'])
@login_required
def api_delete_upload(upload_id):
    """Endpoint para excluir upload via API (chamado pelo JavaScript)"""
    try:
        response = make_api_request('DELETE', f'/history/uploads/{upload_id}')
        if response and response.status_code == 200:
            return jsonify({'success': True, 'message': 'Upload excluído com sucesso'})
        else:
            error_message = 'Erro ao excluir upload'
            if response:
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', error_message)
                except:
                    pass
            return jsonify({'success': False, 'message': error_message}), 400
    except Exception as e:
        logger.error(f"Erro ao excluir upload via API: {e}")
        return jsonify({'success': False, 'message': 'Erro interno ao excluir upload'}), 500

@app.route('/api/history/documents/<int:doc_id>', methods=['PUT'])
@login_required
def api_update_document(doc_id):
    """Endpoint para atualizar documento via API (chamado pelo JavaScript)"""
    try:
        title = request.form.get('title')

        # Preparar dados para envio
        data = {}
        if title:
            data['title'] = title

        response = make_api_request('PUT', f'/history/documents/{doc_id}', data=data)
        if response and response.status_code == 200:
            return jsonify({'success': True, 'message': 'Documento atualizado com sucesso'})
        else:
            error_message = 'Erro ao atualizar documento'
            if response:
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', error_message)
                except:
                    pass
            return jsonify({'success': False, 'message': error_message}), 400
    except Exception as e:
        logger.error(f"Erro ao atualizar documento via API: {e}")
        return jsonify({'success': False, 'message': 'Erro interno ao atualizar documento'}), 500

@app.route('/api/history/documents/<int:doc_id>', methods=['DELETE'])
@login_required
def api_delete_document(doc_id):
    """Endpoint para excluir documento via API (chamado pelo JavaScript)"""
    try:
        response = make_api_request('DELETE', f'/history/documents/{doc_id}')
        if response and response.status_code == 200:
            return jsonify({'success': True, 'message': 'Documento excluído com sucesso'})
        else:
            error_message = 'Erro ao excluir documento'
            if response:
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', error_message)
                except:
                    pass
            return jsonify({'success': False, 'message': error_message}), 400
    except Exception as e:
        logger.error(f"Erro ao excluir documento via API: {e}")
        return jsonify({'success': False, 'message': 'Erro interno ao excluir documento'}), 500

@app.route('/patient/edit/<int:patient_id>', methods=['GET', 'POST'])
@login_required
def patient_edit(patient_id):
    """Página para edição de pacientes existentes"""

    # Obter informações do paciente existente
    patient_response = make_api_request('GET', f'/patient/{patient_id}')

    if not patient_response or patient_response.status_code != 200:
        flash('Paciente não encontrado.', 'danger')
        return redirect(url_for('patients_list'))

    patient_data = patient_response.json().get('patient', {})

    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        date_of_birth = request.form.get('date_of_birth')
        age = request.form.get('age')
        diagnosis = request.form.get('diagnosis')
        neurotype = request.form.get('neurotype', '')
        level = request.form.get('level', '')
        description = request.form.get('description', '')

        if not all([first_name, last_name, date_of_birth, age, diagnosis]):
            flash('Por favor, preencha todos os campos obrigatórios.', 'warning')
            return render_template('patient_edit.html', patient=patient_data)

        # Validar formato da data
        try:
            from datetime import datetime
            datetime.strptime(date_of_birth, '%Y-%m-%d')
        except ValueError:
            flash('Formato de data inválido. Use o formato YYYY-MM-DD.', 'danger')
            return render_template('patient_edit.html', patient=patient_data)

        try:
            age_int = int(age)
            if age_int < 0 or age_int > 150:
                flash('Idade deve ser um número entre 0 e 150.', 'danger')
                return render_template('patient_edit.html', patient=patient_data)
        except ValueError:
            flash('Idade deve ser um número válido.', 'danger')
            return render_template('patient_edit.html', patient=patient_data)

        # Atualizar paciente no backend
        response = make_api_request('PUT', f'/patient/{patient_id}', {
            'owner_id': session['user_id'],
            'first_name': first_name,
            'last_name': last_name,
            'date_of_birth': date_of_birth,
            'age': age_int,
            'diagnosis': diagnosis,
            'neurotype': neurotype,
            'level': level,
            'description': description
        })

        # Processar sensibilidades se fornecidas
        if response and response.status_code == 200:
            # Processar e atualizar sensibilidades
            sensitivity_types = request.form.getlist('sensitivity_types[]')
            sensitivity_levels = request.form.getlist('sensitivity_levels[]')
            sensitivity_descriptions = request.form.getlist('sensitivity_descriptions[]')

            # Primeiro, remover todas as sensibilidades existentes para este paciente
            try:
                delete_response = make_api_request('DELETE', f'/patient/{patient_id}/sensitivities', {
                    'owner_id': session['user_id']
                })
                if delete_response and delete_response.status_code not in [200, 204]:
                    logger.error(f"Falha ao limpar sensibilidades existentes para paciente {patient_id}")
            except Exception as e:
                logger.error(f"Erro ao tentar limpar sensibilidades existentes: {e}")

            # Adicionar as novas sensibilidades
            for i in range(len(sensitivity_types)):
                if i < len(sensitivity_levels) and i < len(sensitivity_descriptions):
                    sensitivity_type = sensitivity_types[i]
                    sensitivity_level = sensitivity_levels[i]
                    sensitivity_desc = sensitivity_descriptions[i]

                    # Apenas adicionar se todos os campos estiverem preenchidos e não forem valores de teste
                    if sensitivity_type and sensitivity_level and sensitivity_desc:
                        # Filtrar valores indesejados como "Sensibilidade de teste" ou "Não se aplica"
                        if sensitivity_desc.lower() not in ['sensibilidade de teste', 'não se aplica', 'não se aplica.'] and sensitivity_type.lower() != 'não se aplica':
                            sensitivity_response = make_api_request('POST', '/patient/add_sensitivity', {
                                'owner_id': session['user_id'],
                                'patient_id': patient_id,
                                'sensitivity_type': sensitivity_type,
                                'sensitivity_level': sensitivity_level,
                                'description': sensitivity_desc
                            })

                            if sensitivity_response and sensitivity_response.status_code == 200:
                                logger.info(f"Sensibilidade {sensitivity_type} adicionada para o paciente {patient_id}")
                            else:
                                logger.error(f"Erro ao adicionar sensibilidade {sensitivity_type} para o paciente {patient_id}")

        if response and response.status_code == 200:
            data = response.json()
            flash(f'Paciente {first_name} {last_name} atualizado com sucesso!', 'success')

            # Atualizar o cache do usuário para garantir que as alterações apareçam
            cache_response = make_api_request('POST', f'/user/{session["user_id"]}/refresh_cache')
            if cache_response and cache_response.status_code == 200:
                logger.info("Cache do usuário atualizado após edição de paciente")
            else:
                logger.warning("Falha ao atualizar cache do usuário após edição de paciente")

            return redirect(url_for('patients_list'))
        else:
            error_message = 'Erro ao atualizar paciente.'
            if response:
                try:
                    error_data = response.json()
                    error_message = error_data.get('detail', error_message)
                except Exception as e:
                    logger.error(f"Erro ao processar resposta do backend: {e}")
                    pass
            flash(error_message, 'danger')

    # Carregar os dados do paciente para o formulário
    return render_template('patient_edit.html', patient=patient_data)

@app.route('/patients')
@login_required
def patients_list():
    """Página para listar pacientes"""
    response = make_api_request('GET', '/patients/list')

    patients = []
    if response and response.status_code == 200:
        data = response.json()
        patients = data.get('patients', [])
    else:
        flash('Erro ao carregar lista de pacientes.', 'danger')

    return render_template('patients_list.html', patients=patients)

# Rota de API para verificação de saúde
@app.route('/health')
def health():
    """Verifica o status do sistema"""
    response = make_api_request('GET', '/health')
    if response and response.status_code == 200:
        return jsonify(response.json())
    return jsonify({'status': 'error', 'message': 'API não disponível'}), 503

# Tratamento de erros
@app.errorhandler(404)
def not_found(error):
    logger.warning(f"Página não encontrada: {request.url}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Erro interno do servidor: {str(error)}", exc_info=True)
    return render_template('500.html'), 500

if __name__ == '__main__':
    port = int(os.getenv("FLASK_PORT", 5000))
    debug_env = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug_env
    )
