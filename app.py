"""
Ponto de entrada principal para o Sistema de Psicologia Clínica RAG + LoRA
"""
import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
import uvicorn
from dotenv import load_dotenv
from passlib.context import CryptContext
from psycopg2.extras import RealDictCursor

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

from core.clinical_ai_system import ClinicalAISystem
from database.db_manager import DatabaseManager
from utils.embedding_generator import CachedEmbeddingGenerator

# Importar funções de anonimização
from anonimizer_functions import process_anonymization

# Importar o calculador de métricas
from utils.metrics_calculator import metrics_calculator

# Importar os novos módulos de análise
from analysis import ClinicalIntelligenceSystem

# Configurações de segurança
# Configurar múltiplos esquemas para lidar com diferentes tipos de hashes
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt"],
    deprecated="auto"
)

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Aumentado de 30 para 60 minutos
REFRESH_TOKEN_EXPIRE_DAYS = 7  # Refresh token expira em 7 dias

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Inicializar aplicação FastAPI
app = FastAPI(
    title="Sistema de IA para Psicologia Clínica",
    description="Sistema RAG + LoRA para aplicações de psicologia clínica",
    version="1.0.0"
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, substitua por domínios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instância global do sistema
clinical_system: Optional[ClinicalAISystem] = None

# Modelos Pydantic para requisições/respostas da API
class QueryRequest(BaseModel):
    query: str
    owner_id: int
    patient_id: Optional[int] = None
    use_openai: bool = True
    model: Optional[str] = None
    k: int = 4
    min_similarity: float = 0.1  # Reduzido para funcionar melhor com embeddings locais

class QueryResponse(BaseModel):
    query: str
    response: str
    retrieved_documents_count: int
    response_time_ms: int
    model_used: str
    # Métricas detalhadas
    latency_seconds: Optional[float] = None
    total_cost_usd: Optional[float] = None
    retrieval_precision: Optional[float] = None
    retrieval_recall: Optional[float] = None
    faithfulness_score: Optional[float] = None
    answer_relevance_score: Optional[float] = None
    ndcg_score: Optional[float] = None
    flesch_reading_ease: Optional[float] = None

class DocumentRequest(BaseModel):
    owner_id: int
    patient_id: int
    title: str
    text: str
    source_type: str = "note"
    metadata: Optional[dict] = {}

class DocumentResponse(BaseModel):
    document_chunk_ids: list
    success: bool
    message: str

class PatientProfileRequest(BaseModel):
    owner_id: int
    patient_id: int


class PatientSensitivityRequest(BaseModel):
    owner_id: int
    patient_id: int
    sensitivity_type: str
    sensitivity_level: str
    description: str

class PatientProfileResponse(BaseModel):
    patient_info: dict
    sensitivities: list
    documents_count: int

class AssessmentRequest(BaseModel):
    query: str
    owner_id: int
    patient_id: int
    assessment_type: str = "general"

class AssessmentResponse(BaseModel):
    assessment_type: str
    patient_id: int #str
    query: str
    response: str
    retrieved_evidence: int
    confidence_score: float
    processing_time: float
    model_used: str
    # Métricas detalhadas
    latency_seconds: Optional[float] = None
    total_cost_usd: Optional[float] = None
    retrieval_precision: Optional[float] = None
    retrieval_recall: Optional[float] = None
    faithfulness_score: Optional[float] = None
    answer_relevance_score: Optional[float] = None
    ndcg_score: Optional[float] = None
    flesch_reading_ease: Optional[float] = None

class UserLogin(BaseModel):
    username: str
    password: str

# Modelos Pydantic para histórico
class ClinicalAssessmentHistory(BaseModel):
    id: int
    user_id: int
    patient_id: int
    query: str = ""
    response: str = ""
    assessment_type: str = "clinical"
    confidence_score: float = 0.0
    processing_time: float = 0.0
    model_used: str = "N/A"
    tokens_used: int = 0
    created_at: datetime

class ClinicalAssessmentHistoryList(BaseModel):
    assessments: List[ClinicalAssessmentHistory]
    total: int

class FileUploadHistory(BaseModel):
    id: int
    user_id: int
    patient_id: int
    title: str = ""
    original_filename: str = ""
    file_path: Optional[str] = None
    file_size: int = 0
    file_type: str = ""
    upload_date: datetime
    status: str = "active"
    metadata: Dict = {}

class FileUploadHistoryList(BaseModel):
    uploads: List[FileUploadHistory]
    total: int

class DocumentHistory(BaseModel):
    id: int
    document_id: Optional[int] = None
    action_type: str = "unknown"
    user_id: int
    patient_id: int
    title: str = ""
    text_content: str = ""
    source_type: str = "note"
    metadata: Dict = {}
    action_date: datetime
    status: str = "active"
    old_values: Optional[Dict] = {}
    new_values: Optional[Dict] = {}

class DocumentHistoryList(BaseModel):
    documents: List[DocumentHistory]
    total: int

class UserRegister(BaseModel):
    username: str
    full_name: str
    email: str
    password: str
    role: str = "therapist"

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60

class TokenData(BaseModel):
    username: str = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class PatientCreateRequest(BaseModel):
    owner_id: int
    patient_id: Optional[str] = None  # Identificador personalizado opcional
    first_name: str
    last_name: str
    date_of_birth: str
    age: int
    diagnosis: str
    neurotype: Optional[str] = ""
    level: Optional[str] = ""
    description: Optional[str] = ""

class PatientCreateResponse(BaseModel):
    patient_id: int
    success: bool
    message: str

def get_clinical_system():
    """Dependência para obter a instância do sistema clínico"""
    if clinical_system is None:
        raise HTTPException(status_code=500, detail="Sistema clínico não inicializado")
    return clinical_system

# Função para verificar senha com múltiplos formatos
def verify_password(plain_password, hashed_password):
    try:
        if not hashed_password:
            return False

        # Verificar se é um hash bcrypt (começa com $2b$, $2a$ ou $2y$)
        if hashed_password.startswith(('$2b$', '$2a$', '$2y$')):
            # Para hashes bcrypt antigos, vamos tentar verificar usando uma configuração diferente
            temp_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            return temp_context.verify(plain_password, hashed_password)
        else:
            # Usar o esquema configurado (atualmente pbkdf2_sha256)
            return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Erro ao verificar senha: {e}")
        return False

# Função para gerar hash da senha
def get_password_hash(password):
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Erro ao gerar hash de senha: {e}")
        raise e

# Função para autenticar usuário
def authenticate_user(username: str, password: str):
    with clinical_system.db_manager.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT id, username, password_hash FROM users
                WHERE username = %s
            """, (username,))
            user = cursor.fetchone()

            # Verificar se o usuário existe e tem um hash de senha
            if user:
                password_hash = user['password_hash']

                # Se o hash de senha for None ou vazio, o usuário não pode fazer login
                if not password_hash:
                    logger.warning(f"Usuário {username} existe mas não tem senha definida")
                    return None

                # Verificar a senha usando a função verify_password
                try:
                    if verify_password(password, password_hash):
                        return {'id': user['id'], 'username': user['username']}
                    else:
                        logger.warning(f"Senha incorreta para o usuário {username}")
                        return None
                except Exception as e:
                    logger.error(f"Erro fatal ao verificar senha para usuário {username}: {e}")
                    return None

            logger.warning(f"Usuário {username} não encontrado")
            return None

# Função para criar token JWT
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Função para criar refresh token
def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Função para obter o usuário atual a partir do token JWT
security = HTTPBearer()

def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        username: str = payload.get("username")

        if user_id is None or username is None:
            raise credentials_exception
    except Exception as e:
        # Tratar qualquer erro de JWT (expirado, inválido, etc.)
        logger.error(f"Erro ao decodificar token JWT: {e}")
        raise credentials_exception

    # Verificar se usuário ainda existe no banco
    with clinical_system.db_manager.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id, username FROM users WHERE id = %s", (int(user_id),))
            user = cursor.fetchone()
            if user is None:
                raise credentials_exception

    return {"id": int(user_id), "username": username}

# Função para verificar se usuário tem permissão específica
def require_user_access(current_user: dict = Depends(get_current_user)):
    """Middleware que garante que o usuário está autenticado"""
    return current_user

# Endpoint de login
@app.post("/login", response_model=Token)
async def login_for_access_token(form_data: UserLogin):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(
        data={"sub": str(user['id']), "username": user['username']},
        expires_delta=access_token_expires
    )

    refresh_token = create_refresh_token(
        data={"sub": str(user['id']), "username": user['username']},
        expires_delta=refresh_token_expires
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

# Endpoint de registro
@app.post("/register", response_model=Token)
async def register_user(user_data: UserRegister):
    # Verificar se usuário já existe
    with clinical_system.db_manager.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id FROM users WHERE username = %s", (user_data.username,))
            existing_user = cursor.fetchone()

            if existing_user:
                raise HTTPException(status_code=400, detail="Username already registered")

    # Criar hash da senha e registrar usuário
    hashed_password = get_password_hash(user_data.password)

    user_id = clinical_system.db_manager.create_user(
        username=user_data.username,
        full_name=user_data.full_name,
        email=user_data.email,
        role=user_data.role
    )

    # Atualizar a senha hash no banco usando a função do DatabaseManager
    clinical_system.db_manager.update_user_password(user_id, hashed_password)

    # Criar e retornar tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    access_token = create_access_token(
        data={"sub": str(user_id), "username": user_data.username},
        expires_delta=access_token_expires
    )

    refresh_token = create_refresh_token(
        data={"sub": str(user_id), "username": user_data.username},
        expires_delta=refresh_token_expires
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

# Endpoint para renovar o token de acesso usando o refresh token
@app.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decodificar o refresh token
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("username")
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        # Verificar se é realmente um refresh token
        if token_type != "refresh":
            raise credentials_exception

        if username is None or user_id is None:
            raise credentials_exception
    except Exception as e:
        logger.error(f"Erro ao decodificar refresh token: {e}")
        raise credentials_exception

    # Verificar se o usuário ainda existe no banco
    with clinical_system.db_manager.get_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT id, username FROM users WHERE id = %s", (int(user_id),))
            user = cursor.fetchone()
            if user is None:
                raise credentials_exception

    # Gerar novos tokens
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    new_access_token = create_access_token(
        data={"sub": str(user['id']), "username": user['username']},
        expires_delta=access_token_expires
    )

    new_refresh_token = create_refresh_token(
        data={"sub": str(user['id']), "username": user['username']},
        expires_delta=refresh_token_expires
    )

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

# Endpoint de logout (cliente-side, apenas invalida o token no frontend)
@app.post("/logout")
async def logout():
    # Este endpoint é mais conceitual - o logout real ocorre no frontend
    # onde o token JWT é removido do armazenamento local
    return {"message": "Logged out successfully"}

@app.on_event("startup")
async def startup_event():
    """Inicializar o sistema de IA clínica na inicialização"""
    global clinical_system

    try:
        # Inicializar gerenciador de banco de dados
        db_manager = DatabaseManager()

        # Inicializar gerador de embeddings com chaves de API
        embedder = CachedEmbeddingGenerator()

        # Inicializar sistema de IA clínica
        clinical_system = ClinicalAISystem(
            db_manager=db_manager,
            embedding_generator=embedder,
            default_model=os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")
        )

        # Garantir que as tabelas de histórico existam
        clinical_system.db_manager.ensure_history_tables_exist()

        logger.info("Sistema de IA Clínica inicializado com sucesso")

    except Exception as e:
        logger.error(f"Falha ao inicializar sistema clínico: {e}")
        logger.warning("A aplicação iniciará em modo degradado. Verifique DATABASE_URL e as chaves de API.")
        # Não re-levanta a exceção para permitir que o uvicorn abra a porta 8080
        # O endpoint /health reportará que o sistema não está inicializado

@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "message": "API do Sistema de IA para Psicologia Clínica",
        "status": "running",
        "endpoints": [
            "/query",
            "/add_document",
            "/patient_profile",
            "/assessment"
        ]
    }

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest, current_user: dict = Depends(require_user_access)):
    """Consultar o sistema de IA clínica - protegido por autenticação"""
    # Verificar se o usuário tem permissão para acessar este owner_id
    if request.owner_id != current_user['id']:
        raise HTTPException(status_code=403, detail="Access denied to this resource")

    # Validação para garantir que um paciente foi selecionado
    if request.patient_id is None or request.patient_id == "":
        raise HTTPException(status_code=400, detail="É necessário selecionar um paciente para realizar a consulta")

    logger.info(f"Recebendo consulta: '{request.query}' para owner_id: {request.owner_id}, patient_id: {request.patient_id}, user_id: {current_user['id']}")
    try:
        result = clinical_system.query_clinical_system(
            query=request.query,
            owner_id=request.owner_id,
            patient_id=request.patient_id,
            use_openai=request.use_openai,
            model=request.model,
            k=request.k,
            min_similarity=request.min_similarity
        )

        logger.info(f"Consulta processada com sucesso. Documentos recuperados: {len(result['rag_result']['retrieved_documents'])}")

        # Extrair métricas detalhadas se estiverem disponíveis
        quality_metrics = result.get("quality_metrics", {})
        latency_metrics = quality_metrics.get("latency_metrics", {})
        cost_metrics = quality_metrics.get("cost_metrics", {})
        retrieval_metrics = quality_metrics.get("retrieval_metrics", {})
        faithfulness_metrics = quality_metrics.get("faithfulness", {})
        answer_relevance_metrics = quality_metrics.get("answer_relevance", {})
        ndcg_metrics = quality_metrics.get("ndcg_at_k", {})
        readability_metrics = quality_metrics.get("readability", {})

        return QueryResponse(
            query=result["query"],
            response=result["response"],
            retrieved_documents_count=len(result["rag_result"]["retrieved_documents"]),
            response_time_ms=result["response_time_ms"],
            model_used=result["model_used"],
            # Métricas detalhadas
            latency_seconds=latency_metrics.get('latency_seconds'),
            total_cost_usd=cost_metrics.get('total_cost_usd'),
            retrieval_precision=retrieval_metrics.get('precision'),
            retrieval_recall=retrieval_metrics.get('recall'),
            faithfulness_score=faithfulness_metrics.get('faithfulness_score'),
            answer_relevance_score=answer_relevance_metrics.get('relevance_score'),
            ndcg_score=ndcg_metrics.get('ndcg_score'),
            flesch_reading_ease=readability_metrics.get('flesch_reading_ease')
        )
    except Exception as e:
        logger.error(f"Erro ao processar consulta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add_document", response_model=DocumentResponse)
async def add_document_endpoint(request: DocumentRequest, current_user: dict = Depends(require_user_access)):
    """Adicionar um documento clínico ao sistema - protegido por autenticação"""
    # Verificar se o usuário tem permissão para adicionar documento para este owner_id
    if request.owner_id != current_user['id']:
        raise HTTPException(status_code=403, detail="Access denied to this resource")

    try:
        # Anonimizar o conteúdo do documento antes de adicioná-lo
        anonymized_text = process_anonymization("TEXT", request.text)

        chunk_ids = clinical_system.add_clinical_document(
            owner_id=request.owner_id,
            patient_id=request.patient_id,
            title=request.title,
            text=anonymized_text,
            source_type=request.source_type,
            metadata=request.metadata
        )

        return DocumentResponse(
            document_chunk_ids=chunk_ids,
            success=True,
            message=f"Documento adicionado com sucesso com {len(chunk_ids)} chunks"
        )
    except Exception as e:
        logger.error(f"Erro ao adicionar documento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/patient_profile", response_model=PatientProfileResponse)
async def patient_profile_endpoint(request: PatientProfileRequest, current_user: dict = Depends(require_user_access)):
    """Obter informações do perfil do paciente - protegido por autenticação"""
    # Verificar se o usuário tem permissão para acessar este owner_id
    if request.owner_id != current_user['id']:
        raise HTTPException(status_code=403, detail="Access denied to this resource")

    try:
        profile = clinical_system.get_patient_profile(
            request.owner_id,
            request.patient_id
        )

        if not profile:
            raise HTTPException(status_code=404, detail="Paciente não encontrado")

        # Contar documentos para este paciente (isso exigiria um método no gerenciador de BD)
        # Por enquanto, retornaremos o que temos
        return PatientProfileResponse(
            patient_info=profile,
            sensitivities=profile.get('sensitivities', []),
            documents_count=0  # Isso viria de uma consulta de contagem
        )
    except Exception as e:
        logger.error(f"Erro ao obter perfil do paciente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/patient/add_sensitivity")
async def add_patient_sensitivity_endpoint(
    request: PatientSensitivityRequest,
    current_user: dict = Depends(require_user_access)
):
    """Adicionar uma sensibilidade para um paciente - protegido por autenticação"""
    # Verificar se o usuário tem permissão para acessar este owner_id
    if request.owner_id != current_user['id']:
        raise HTTPException(status_code=403, detail="Access denied to this resource")

    try:
        sensitivity_id = clinical_system.add_patient_sensitivity(
            owner_id=request.owner_id,
            patient_id=request.patient_id,
            sensitivity_type=request.sensitivity_type,
            sensitivity_level=request.sensitivity_level,
            description=request.description
        )

        logger.info(f"Sensibilidade adicionada com ID {sensitivity_id} para paciente {request.patient_id}")
        return {"success": True, "sensitivity_id": sensitivity_id}
    except Exception as e:
        logger.error(f"Erro ao adicionar sensibilidade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/patient/{patient_id}/sensitivities")
async def delete_patient_sensitivities_endpoint(
    patient_id: int,
    owner_id: int,
    current_user: dict = Depends(require_user_access)
):
    """Remover todas as sensibilidades de um paciente - protegido por autenticação"""
    # Verificar se o usuário tem permissão para acessar este owner_id
    if owner_id != current_user['id']:
        raise HTTPException(status_code=403, detail="Access denied to this resource")

    try:
        deleted_count = clinical_system.delete_patient_sensitivities(
            owner_id=owner_id,
            patient_id=patient_id
        )

        logger.info(f"Removidas {deleted_count} sensibilidades para paciente {patient_id}")
        return {"success": True, "deleted_count": deleted_count}
    except Exception as e:
        logger.error(f"Erro ao remover sensibilidades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/assessment", response_model=AssessmentResponse)
async def assessment_endpoint(request: AssessmentRequest, current_user: dict = Depends(require_user_access)):
    """Executar uma avaliação clínica - protegido por autenticação"""
    # Verificar se o usuário tem permissão para acessar este owner_id
    if request.owner_id != current_user['id']:
        raise HTTPException(status_code=403, detail="Access denied to this resource")

    # Validação para garantir que um paciente foi selecionado
    if request.patient_id is None or request.patient_id == "":
        raise HTTPException(status_code=400, detail="É necessário selecionar um paciente para realizar a avaliação")

    try:
        result = clinical_system.run_clinical_assessment(
            query=request.query,
            owner_id=request.owner_id,
            patient_id=request.patient_id,
            assessment_type=request.assessment_type
        )

        # Extrair métricas detalhadas se estiverem disponíveis
        quality_metrics = result.get("quality_metrics", {})
        latency_metrics = quality_metrics.get("latency_metrics", {})
        cost_metrics = quality_metrics.get("cost_metrics", {})
        retrieval_metrics = quality_metrics.get("retrieval_metrics", {})
        faithfulness_metrics = quality_metrics.get("faithfulness", {})
        answer_relevance_metrics = quality_metrics.get("answer_relevance", {})
        ndcg_metrics = quality_metrics.get("ndcg_at_k", {})
        readability_metrics = quality_metrics.get("readability", {})

        return AssessmentResponse(
            assessment_type=result["assessment_type"],
            patient_id=result["patient_id"],
            query=result["query"],
            response=result["response"],
            retrieved_evidence=result["retrieved_evidence"],
            confidence_score=result["confidence_score"],
            processing_time=result["processing_time"],
            model_used=result["model_used"],
            # Métricas detalhadas
            latency_seconds=latency_metrics.get('latency_seconds'),
            total_cost_usd=cost_metrics.get('total_cost_usd'),
            retrieval_precision=retrieval_metrics.get('precision'),
            retrieval_recall=retrieval_metrics.get('recall'),
            faithfulness_score=faithfulness_metrics.get('faithfulness_score'),
            answer_relevance_score=answer_relevance_metrics.get('relevance_score'),
            ndcg_score=ndcg_metrics.get('ndcg_score'),
            flesch_reading_ease=readability_metrics.get('flesch_reading_ease')
        )
    except Exception as e:
        logger.error(f"Erro ao executar avaliação: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Endpoint de verificação de saúde"""
    return {
        "status": "healthy",
        "timestamp": str(clinical_system.db_manager.get_connection if clinical_system else "not initialized")
    }

# Modelos Pydantic para métricas
class MetricsResponse(BaseModel):
    overall_quality_score: float
    latency_metrics: Dict[str, Any]
    cost_metrics: Dict[str, Any]
    retrieval_metrics: Dict[str, Any]
    faithfulness: Dict[str, Any]
    answer_relevance: Dict[str, float]
    context_relevance: Dict[str, float]
    ndcg_at_k: Dict[str, Any]
    readability: Dict[str, Any]

class AggregatedMetricsResponse(BaseModel):
    total_queries: int
    avg_quality_score: float
    avg_latency: float
    avg_f1_score: float
    avg_faithfulness: float
    avg_answer_relevance: float
    avg_context_relevance: float
    avg_ndcg: float
    total_cost: float

@app.get("/metrics/quality/{query_id}")
async def get_query_metrics(query_id: int, current_user: dict = Depends(require_user_access)):
    """Obter métricas de qualidade para uma consulta específica"""
    # Este endpoint requer acesso direto ao banco de dados para buscar métricas
    # Por segurança, vamos verificar se o usuário tem acesso a esta consulta
    # Na implementação real, você precisaria verificar se a query_id pertence ao usuário

    with clinical_system.db_manager.get_connection() as conn:
        with conn.cursor() as cursor:
            # Verificar se o usuário tem acesso a esta consulta
            cursor.execute("""
                SELECT al.id FROM audit_log al
                JOIN query_quality_metrics qqm ON al.id = qqm.query_id
                WHERE qqm.query_id = %s AND al.user_id = %s
            """, (query_id, current_user['id']))
            result = cursor.fetchone()

            if not result:
                raise HTTPException(status_code=403, detail="Acesso negado a esta consulta")

    # A implementação real dependeria de como você estrutura o acesso às métricas
    # Por enquanto, retornamos uma resposta de exemplo
    return {
        "message": "Endpoint para obter métricas de qualidade implementado",
        "query_id": query_id
    }

@app.get("/metrics/aggregated")
async def get_aggregated_metrics(
    start_date: str = None,
    end_date: str = None,
    model_name: str = None,
    current_user: dict = Depends(require_user_access)
):
    """Obter métricas agregadas para um período"""
    try:
        metrics = clinical_system.db_manager.get_aggregated_metrics(
            start_date=start_date,
            end_date=end_date,
            model_name=model_name
        )
        return AggregatedMetricsResponse(**metrics)
    except Exception as e:
        logger.error(f"Erro ao obter métricas agregadas: {e}")
        raise HTTPException(status_code=500, detail="Erro ao obter métricas agregadas")

@app.post("/metrics/evaluate_response")
async def evaluate_response_quality(request: QueryRequest, current_user: dict = Depends(require_user_access)):
    """Avaliar a qualidade de uma resposta (endpoint para testes e validação humana)"""
    try:
        # Calcular métricas para a resposta fornecida
        metrics = metrics_calculator.calculate_comprehensive_metrics(
            query=request.query,
            response="Resposta de exemplo para fins de avaliação",
            retrieved_docs=[],
            context="Contexto de exemplo",
            embedding_func=clinical_system.embedding_generator.generate_single_embedding if clinical_system.embedding_generator else None
        )

        return {"metrics": metrics}
    except Exception as e:
        logger.error(f"Erro ao avaliar qualidade da resposta: {e}")
        raise HTTPException(status_code=500, detail="Erro ao avaliar qualidade da resposta")

@app.get("/metrics/leaderboard")
async def get_model_leaderboard(current_user: dict = Depends(require_user_access)):
    """Obter classificação de modelos por qualidade"""
    try:
        # Obter métricas agregadas por modelo
        with clinical_system.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                query = """
                    SELECT
                        model_name,
                        COUNT(*) as total_queries,
                        AVG(overall_quality_score) as avg_quality_score,
                        AVG(latency_seconds) as avg_latency,
                        AVG(retrieval_f1) as avg_f1_score,
                        AVG(faithfulness_score) as avg_faithfulness,
                        SUM(total_cost_usd) as total_cost
                    FROM query_quality_metrics qqm
                    JOIN audit_log al ON qqm.query_id = al.id
                    WHERE al.user_id = %s
                    GROUP BY model_name
                    ORDER BY avg_quality_score DESC
                """

                cursor.execute(query, (current_user['id'],))
                results = cursor.fetchall()

                leaderboard = []
                for row in results:
                    leaderboard.append({
                        "model_name": row[0],
                        "total_queries": row[1],
                        "avg_quality_score": float(row[2]) if row[2] is not None else 0.0,
                        "avg_latency": float(row[3]) if row[3] is not None else 0.0,
                        "avg_f1_score": float(row[4]) if row[4] is not None else 0.0,
                        "avg_faithfulness": float(row[5]) if row[5] is not None else 0.0,
                        "total_cost": float(row[6]) if row[6] is not None else 0.0
                    })

                return {"leaderboard": leaderboard}
    except Exception as e:
        logger.error(f"Erro ao obter classificação de modelos: {e}")
        raise HTTPException(status_code=500, detail="Erro ao obter classificação de modelos")

@app.get("/models")
async def list_models():
    """Listar modelos disponíveis (apenas informativo, OpenAI tratado via API)"""
    if clinical_system and clinical_system.openai_client:
        return {"models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"], "message": "Modelos OpenAI disponíveis via API"}
    else:
        return {"models": [], "message": "Cliente OpenAI não disponível"}

@app.get("/api/user/{owner_id}/stats")
async def get_user_stats(owner_id: int, current_user: dict = Depends(require_user_access)):
    """
    Obtém estatísticas da base de conhecimento do usuário
    Similar ao Guru TI - mostra todos os documentos e pacientes do usuário
    """
    # Verificar se o usuário tem permissão para acessar estatísticas deste owner_id
    if owner_id != current_user['id']:
        raise HTTPException(status_code=403, detail="Access denied to this resource")

    try:
        stats = clinical_system.get_user_statistics(owner_id)
        return {
            "owner_id": owner_id,
            "statistics": stats,
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas do usuário: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/{owner_id}/context")
async def get_user_context(owner_id: int, patient_id: int = None, current_user: dict = Depends(require_user_access)):
    """
    Obtém contexto completo do usuário (todos os documentos)
    Similar ao Guru TI que tem toda a base sempre disponível
    """
    # Verificar se o usuário tem permissão para acessar contexto deste owner_id
    if owner_id != current_user['id']:
        raise HTTPException(status_code=403, detail="Access denied to this resource")

    try:
        context = clinical_system.user_kb.get_user_context(owner_id, patient_id)
        return {
            "owner_id": owner_id,
            "patient_id": patient_id,
            "context": context,
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        logger.error(f"Erro ao obter contexto do usuário: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload_document")
async def upload_document(
    file: UploadFile = File(...),
    owner_id: str = Form(...),
    patient_id: str = Form(...),
    title: str = Form(None),
    source_type: str = Form("uploaded_file"),
    current_user: dict = Depends(require_user_access)
):
    """Fazer upload e processar um arquivo de documento (PDF, DOCX, TXT, etc.) - protegido por autenticação"""

    # Converter owner_id e patient_id para inteiro com tratamento de erro
    try:
        owner_id_int = int(owner_id)
        patient_id_int = int(patient_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="owner_id e patient_id devem ser números inteiros válidos")

    # Verificar se o usuário tem permissão para fazer upload para este owner_id
    if owner_id_int != current_user['id']:
        raise HTTPException(status_code=403, detail="Access denied to this resource")

    # Logs adicionais para depuração
    debug_msg = f"DEBUG BACKEND: Recebendo upload - file: {file.filename}, size: {file.size}, content_type: {file.content_type}"
    print(debug_msg)
    logger.info(debug_msg)

    debug_msg2 = f"DEBUG BACKEND: owner_id: {owner_id_int} (tipo: {type(owner_id_int)}), patient_id: {patient_id_int} (tipo: {type(patient_id_int)}), title: {title}, source_type: {source_type}"
    print(debug_msg2)
    logger.info(debug_msg2)

    logger.info(f"Iniciando upload do arquivo: {file.filename} para owner_id: {owner_id_int}, patient_id: {patient_id_int}, user_id: {current_user['id']}")

    # Obter o tamanho do arquivo original antes de ler o conteúdo
    file.file.seek(0, 2)  # Vai para o final do arquivo
    original_file_size = file.file.tell()  # Obtém o tamanho
    file.file.seek(0)  # Retorna ao início

    # Verificar tamanho máximo (10MB)
    max_file_size = 10 * 1024 * 1024  # 10MB
    if original_file_size > max_file_size:
        raise HTTPException(status_code=413, detail=f"Arquivo muito grande. Tamanho máximo permitido: {max_file_size} bytes")

    try:
        # Criar um arquivo temporário para salvar o conteúdo enviado para processamento
        import tempfile
        import os
        from utils.text_processor import ClinicalDataProcessor

        # Criar arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file.filename.split('.')[-1]}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # Usar ClinicalDataProcessor para lidar com a extração e limpeza de arquivos
            processor = ClinicalDataProcessor()

            # Processar o arquivo para extrair e limpar texto
            # Este método lida com todos os tipos de arquivos e remove caracteres NUL
            chunks = processor.process_clinical_document(temp_file_path, title or file.filename)

            if not chunks:
                raise ValueError(f"Nenhum texto extraído de {file.filename}")

            # Obter o texto completo do primeiro chunk (ou combinar todos os chunks se necessário)
            # Neste caso usaremos o texto completo que foi processado e limpo
            full_text = ""
            for chunk in chunks:
                full_text += chunk['text'] + "\n"

            # Definir título como nome do arquivo se não for fornecido
            if not title:
                title = file.filename

            # Adicionar documento ao sistema
            chunk_ids = clinical_system.add_clinical_document(
                owner_id=owner_id_int,
                patient_id=patient_id_int,
                title=title,
                text=full_text,
                source_type=source_type,
                metadata={"original_filename": file.filename, "file_type": file.filename.split('.')[-1].lower()}
            )
        # Registrar o upload na tabela de histórico
            try:
                clinical_system.db_manager.add_file_upload(
                    user_id=owner_id_int,
                    patient_id=patient_id_int,
                    title=title,
                    original_filename=file.filename,
                    file_path="upload_front",  # Não armazenamos o caminho físico do arquivo
                    file_size=original_file_size,  # Usar o tamanho original do arquivo
                    file_type=file.content_type,
                    metadata={
                        "original_filename": file.filename,
                        "file_type": file.filename.split('.')[-1].lower(),
                        "chunks_created": len(chunk_ids),
                        "original_file_size": original_file_size  # Adicionar tamanho original aos metadados
                    }
                )
            except Exception as e:
                logger.error(f"Falha ao registrar upload de arquivo no histórico: {e}")

        finally:
            # Limpar o arquivo temporário
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

        logger.info(f"Documento processado e armazenado com {len(chunk_ids)} chunks")
        return DocumentResponse(
            document_chunk_ids=chunk_ids,
            success=True,
            message=f"Successfully uploaded and processed {file.filename} with {len(chunk_ids)} chunks"
        )
    except Exception as e:
        logger.error(f"Error processing uploaded file: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/patient/create", response_model=PatientCreateResponse)
async def create_patient(request: PatientCreateRequest, current_user: dict = Depends(require_user_access)):
    """Criar novo paciente - protegido por autenticação"""
    # Verificar se o usuário tem permissão para criar paciente para este owner_id
    if request.owner_id != current_user['id']:
        raise HTTPException(status_code=403, detail="Access denied to this resource")

    try:
        # Anonimizar dados sensíveis antes de criar o paciente
        anonymized_first_name = process_anonymization("TEXT", request.first_name)
        anonymized_last_name = process_anonymization("TEXT", request.last_name)
        anonymized_description = process_anonymization("TEXT", request.description)

        # Criar paciente no banco de dados usando a função do DB Manager
        patient_db_id = clinical_system.db_manager.create_patient(
            patient_id=request.patient_id if hasattr(request, 'patient_id') and request.patient_id else None,
            owner_id=request.owner_id,
            first_name=anonymized_first_name,
            last_name=anonymized_last_name,
            date_of_birth=request.date_of_birth,
            age=request.age,
            diagnosis=request.diagnosis,
            neurotype=request.neurotype,
            level=request.level,
            description=anonymized_description
        )

        logger.info(f"Paciente {request.first_name} {request.last_name} criado com ID: {patient_db_id}")

        # Atualizar índice do usuário após adicionar paciente
        try:
            clinical_system.user_kb.refresh_user_index(request.owner_id)
            logger.info(f"Índice do usuário {request.owner_id} atualizado após adicionar paciente")
        except Exception as e:
            logger.warning(f"Erro ao atualizar índice do usuário: {e}")

        return PatientCreateResponse(
            patient_id=patient_db_id,
            success=True,
            message=f"Paciente {request.first_name} {request.last_name} cadastrado com sucesso"
        )
    except Exception as e:
        logger.error(f"Erro ao criar paciente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/patient/{patient_id}", response_model=PatientCreateResponse)
async def update_patient(
    patient_id: int,
    request: PatientCreateRequest,
    current_user: dict = Depends(require_user_access)
):
    """Atualizar informações de um paciente existente - protegido por autenticação"""
    try:
        # Verificar se o usuário tem permissão para atualizar este paciente (mesmo owner)
        with clinical_system.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT owner_id FROM patients
                    WHERE id = %s
                """, (patient_id,))
                result = cursor.fetchone()

                if not result:
                    raise HTTPException(status_code=404, detail="Paciente não encontrado")

                if result[0] != current_user['id']:
                    raise HTTPException(status_code=403, detail="Access denied to this resource")

        # Anonimizar dados sensíveis antes de atualizar o paciente
        anonymized_first_name = process_anonymization("TEXT", request.first_name)
        anonymized_last_name = process_anonymization("TEXT", request.last_name)
        anonymized_description = process_anonymization("TEXT", request.description)

        # Atualizar paciente no banco de dados
        with clinical_system.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE patients
                    SET first_name = %s, last_name = %s, date_of_birth = %s, age = %s,
                        diagnosis = %s, neurotype = %s, level = %s, description = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND owner_id = %s
                    RETURNING id
                """, (
                    anonymized_first_name, anonymized_last_name, request.date_of_birth, request.age,
                    request.diagnosis, request.neurotype, request.level, anonymized_description,
                    patient_id, current_user['id']
                ))

                result = cursor.fetchone()
                conn.commit()

                if not result:
                    raise HTTPException(status_code=404, detail="Paciente não encontrado para atualização")

                updated_patient_id = result[0]

        logger.info(f"Paciente {request.first_name} {request.last_name} atualizado com ID: {updated_patient_id}")

        # Atualizar índice do usuário após atualizar paciente
        try:
            clinical_system.user_kb.refresh_user_index(current_user['id'])
            logger.info(f"Índice do usuário {current_user['id']} atualizado após atualizar paciente")
        except Exception as e:
            logger.warning(f"Erro ao atualizar índice do usuário: {e}")

        return PatientCreateResponse(
            patient_id=updated_patient_id,
            success=True,
            message=f"Paciente {request.first_name} {request.last_name} atualizado com sucesso"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao atualizar paciente: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/user/{owner_id}/refresh_cache")
async def refresh_user_cache(owner_id: int, current_user: dict = Depends(require_user_access)):
    """Atualizar o cache de dados do usuário"""
    # Verificar se o usuário tem permissão para atualizar cache para este owner_id
    if owner_id != current_user['id']:
        raise HTTPException(status_code=403, detail="Access denied to this resource")

    try:
        # Atualizar índice do usuário
        clinical_system.user_kb.refresh_user_index(owner_id)

        # Atualizar estatísticas do usuário
        stats = clinical_system.get_user_statistics(owner_id)

        logger.info(f"Cache do usuário {owner_id} atualizado com sucesso")

        return {
            "success": True,
            "message": "Cache atualizado com sucesso",
            "timestamp": str(datetime.now()),
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Erro ao atualizar cache do usuário: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/queries", response_model=ClinicalAssessmentHistoryList)
async def get_query_history(
    patient_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(require_user_access)
):
    """Obter histórico de consultas do usuário (das avaliações clínicas)"""
    try:
        queries = clinical_system.db_manager.get_query_history(
            user_id=current_user['id'],
            patient_id=patient_id,
            limit=limit,
            offset=offset
        )

        return ClinicalAssessmentHistoryList(
            assessments=[ClinicalAssessmentHistory(
                id=query['id'],
                user_id=query['user_id'],
                patient_id=query['patient_id'],
                query=query.get('query', ''),
                response=query.get('response', ''),
                assessment_type=query.get('assessment_type', 'query'),
                confidence_score=query.get('confidence_score', 0.0),
                processing_time=query.get('processing_time', 0.0),
                model_used=query.get('model_used', 'N/A'),
                tokens_used=query.get('tokens_used', 0),
                created_at=query['created_at']
            ) for query in queries],
            total=len(queries)
        )
    except Exception as e:
        logger.error(f"Erro ao obter histórico de consultas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/history/queries/{query_id}")
async def update_query(
    query_id: int,
    query_text: str = Form(None),
    response: str = Form(None),
    current_user: dict = Depends(require_user_access)
):
    """Atualizar uma consulta existente"""
    try:
        success = clinical_system.db_manager.update_query_history(
            query_id=query_id,
            user_id=current_user['id'],
            query_text=query_text,
            response=response
        )

        if success:
            return {"success": True, "message": "Consulta atualizada com sucesso"}
        else:
            raise HTTPException(status_code=404, detail="Consulta não encontrada ou você não tem permissão para editá-la")
    except Exception as e:
        logger.error(f"Erro ao atualizar consulta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/history/queries/{query_id}")
async def delete_query(
    query_id: int,
    current_user: dict = Depends(require_user_access)
):
    """Excluir uma consulta"""
    try:
        success = clinical_system.db_manager.delete_query_history(
            query_id=query_id,
            user_id=current_user['id']
        )

        if success:
            return {"success": True, "message": "Consulta excluída com sucesso"}
        else:
            raise HTTPException(status_code=404, detail="Consulta não encontrada ou você não tem permissão para excluí-la")
    except Exception as e:
        logger.error(f"Erro ao excluir consulta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/assessments", response_model=ClinicalAssessmentHistoryList)
async def get_assessment_history(
    patient_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(require_user_access)
):
    """Obter histórico de avaliações clínicas do usuário (excluindo consultas)"""
    try:
        assessments = clinical_system.db_manager.get_clinical_assessments(
            user_id=current_user['id'],
            patient_id=patient_id,
            limit=limit,
            offset=offset
        )

        # Obter total de registros para paginação (necessita de uma nova consulta)
        # Para simplificar, retornamos apenas os resultados atuais
        # Em um sistema real, faríamos uma consulta separada para o total

        return ClinicalAssessmentHistoryList(
            assessments=[ClinicalAssessmentHistory(
                id=assessment['id'],
                user_id=assessment['user_id'],
                patient_id=assessment['patient_id'],
                query=assessment.get('query', ''),
                response=assessment.get('response', ''),
                assessment_type=assessment.get('assessment_type', 'clinical'),
                confidence_score=assessment.get('confidence_score', 0.0),
                processing_time=assessment.get('processing_time', 0.0),
                model_used=assessment.get('model_used', 'N/A'),
                tokens_used=assessment.get('tokens_used', 0),
                created_at=assessment['created_at']
            ) for assessment in assessments],
            total=len(assessments)  # Isso é apenas para simplificar - num sistema real seria uma consulta separada
        )
    except Exception as e:
        logger.error(f"Erro ao obter histórico de avaliações: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/history/assessments/{assessment_id}")
async def update_assessment(
    assessment_id: int,
    request: AssessmentRequest,  # Reutilizando o modelo existente
    current_user: dict = Depends(require_user_access)
):
    """Atualizar uma avaliação clínica existente"""
    try:
        success = clinical_system.db_manager.update_clinical_assessment(
            assessment_id=assessment_id,
            user_id=current_user['id'],
            query=request.query,
            assessment_type=request.assessment_type
        )

        if success:
            return {"success": True, "message": "Avaliação atualizada com sucesso"}
        else:
            raise HTTPException(status_code=404, detail="Avaliação não encontrada ou você não tem permissão para editá-la")
    except Exception as e:
        logger.error(f"Erro ao atualizar avaliação: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/history/assessments/{assessment_id}")
async def delete_assessment(
    assessment_id: int,
    current_user: dict = Depends(require_user_access)
):
    """Excluir uma avaliação clínica"""
    try:
        success = clinical_system.db_manager.delete_clinical_assessment(
            assessment_id=assessment_id,
            user_id=current_user['id']
        )

        if success:
            return {"success": True, "message": "Avaliação excluída com sucesso"}
        else:
            raise HTTPException(status_code=404, detail="Avaliação não encontrada ou você não tem permissão para excluí-la")
    except Exception as e:
        logger.error(f"Erro ao excluir avaliação: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/uploads", response_model=FileUploadHistoryList)
async def get_upload_history(
    patient_id: Optional[int] = None,
    status: str = "active",
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(require_user_access)
):
    """Obter histórico de uploads de arquivos do usuário"""
    try:
        uploads = clinical_system.db_manager.get_file_uploads(
            user_id=current_user['id'],
            patient_id=patient_id,
            status=status,
            limit=limit,
            offset=offset
        )

        return FileUploadHistoryList(
            uploads=[FileUploadHistory(
                id=upload['id'],
                user_id=upload['user_id'],
                patient_id=upload['patient_id'],
                title=upload.get('title', ''),
                original_filename=upload.get('original_filename', ''),
                file_path=upload.get('file_path'),
                file_size=upload.get('file_size', 0),
                file_type=upload.get('file_type', ''),
                upload_date=upload['upload_date'],
                status=upload.get('status', 'active'),
                metadata=upload.get('metadata', {})
            ) for upload in uploads],
            total=len(uploads)
        )
    except Exception as e:
        logger.error(f"Erro ao obter histórico de uploads: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/history/uploads/{upload_id}")
async def update_upload(
    upload_id: int,
    title: str = Form(None),
    status: str = Form(None),
    current_user: dict = Depends(require_user_access)
):
    """Atualizar um upload de arquivo existente"""
    try:
        success = clinical_system.db_manager.update_file_upload(
            upload_id=upload_id,
            user_id=current_user['id'],
            title=title,
            status=status
        )

        if success:
            return {"success": True, "message": "Upload atualizado com sucesso"}
        else:
            raise HTTPException(status_code=404, detail="Upload não encontrado ou você não tem permissão para editá-lo")
    except Exception as e:
        logger.error(f"Erro ao atualizar upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/history/uploads/{upload_id}")
async def delete_upload_history(
    upload_id: int,
    current_user: dict = Depends(require_user_access)
):
    """Marcar upload como excluído (soft delete)"""
    try:
        success = clinical_system.db_manager.delete_file_upload(
            upload_id=upload_id,
            user_id=current_user['id']
        )

        if success:
            return {"success": True, "message": "Upload marcado como excluído com sucesso"}
        else:
            raise HTTPException(status_code=404, detail="Upload não encontrado ou você não tem permissão para excluí-lo")
    except Exception as e:
        logger.error(f"Erro ao excluir upload do histórico: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/documents", response_model=DocumentHistoryList)
async def get_document_history(
    patient_id: Optional[int] = None,
    action_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(require_user_access)
):
    """Obter histórico de documentos do usuário"""
    try:
        documents = clinical_system.db_manager.get_document_history(
            user_id=current_user['id'],
            patient_id=patient_id,
            action_type=action_type,
            limit=limit,
            offset=offset
        )

        return DocumentHistoryList(
            documents=[DocumentHistory(
                id=doc['id'],
                document_id=doc.get('document_id'),
                action_type=doc.get('action_type', 'unknown'),
                user_id=doc['user_id'],
                patient_id=doc['patient_id'],
                title=doc.get('title', ''),
                text_content=doc.get('text_content', ''),
                source_type=doc.get('source_type', 'note'),
                metadata=doc.get('metadata', {}),
                action_date=doc['action_date'],
                status=doc.get('status', 'active'),
                old_values=doc.get('old_values', {}),
                new_values=doc.get('new_values', {})
            ) for doc in documents],
            total=len(documents)
        )
    except Exception as e:
        logger.error(f"Erro ao obter histórico de documentos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history/stats")
async def get_history_stats(
    patient_id: Optional[int] = None,
    current_user: dict = Depends(require_user_access)
):
    """Obter estatísticas de histórico para o usuário (contagem de consultas, avaliações, uploads e documentos)"""
    try:
        stats = clinical_system.db_manager.get_history_statistics(
            user_id=current_user['id'],
            patient_id=patient_id
        )

        return {
            "stats": stats,
            "user_id": current_user['id'],
            "patient_id": patient_id,
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas de histórico: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/history/documents/{history_id}")
async def update_document_history(
    history_id: int,
    title: str = Form(None),
    text_content: str = Form(None),
    source_type: str = Form(None),
    status: str = Form(None),
    current_user: dict = Depends(require_user_access)
):
    """Atualizar um registro de histórico de documento existente"""
    try:
        success = clinical_system.db_manager.update_document_history(
            history_id=history_id,
            user_id=current_user['id'],
            title=title,
            text_content=text_content,
            source_type=source_type,
            status=status
        )

        if success:
            return {"success": True, "message": "Histórico de documento atualizado com sucesso"}
        else:
            raise HTTPException(status_code=404, detail="Registro de histórico não encontrado ou você não tem permissão para editá-lo")
    except Exception as e:
        logger.error(f"Erro ao atualizar histórico de documento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/history/documents/{history_id}")
async def delete_document_history(
    history_id: int,
    current_user: dict = Depends(require_user_access)
):
    """Excluir um registro de histórico de documento"""
    try:
        success = clinical_system.db_manager.delete_document_history(
            history_id=history_id,
            user_id=current_user['id']
        )

        if success:
            return {"success": True, "message": "Registro de histórico excluído com sucesso"}
        else:
            raise HTTPException(status_code=404, detail="Registro de histórico não encontrado ou você não tem permissão para excluí-lo")
    except Exception as e:
        logger.error(f"Erro ao excluir histórico de documento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/patients/list")
async def list_patients(current_user: dict = Depends(require_user_access)):
    """Listar todos os pacientes do usuário logado"""
    try:
        with clinical_system.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, first_name, last_name, date_of_birth, age, diagnosis,
                           neurotype, level, created_at
                    FROM patients
                    WHERE owner_id = %s
                    ORDER BY created_at DESC
                """, (current_user['id'],))

                patients = cursor.fetchall()

                return {
                    "patients": patients,
                    "total": len(patients),
                    "timestamp": str(datetime.now())
                }
    except Exception as e:
        logger.error(f"Erro ao listar pacientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/patient/{patient_id}")
async def get_patient_details(patient_id: int, current_user: dict = Depends(require_user_access)):
    """Obter detalhes completos de um paciente"""
    try:
        with clinical_system.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT *
                    FROM patients
                    WHERE id = %s AND owner_id = %s
                """, (patient_id, current_user['id']))

                patient = cursor.fetchone()

                if not patient:
                    raise HTTPException(status_code=404, detail="Paciente não encontrado")

                return {
                    "patient": patient,
                    "timestamp": str(datetime.now())
                }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do paciente: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/{user_id}/patients")
async def get_user_patients(user_id: int, current_user: dict = Depends(require_user_access)):
    """Obter pacientes do usuário específico (usado pelo frontend Flask)"""
    # Verificar se o usuário está tentando acessar seus próprios dados
    if user_id != current_user['id']:
        raise HTTPException(status_code=403, detail="Access denied to this resource")

    try:
        with clinical_system.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, first_name, last_name, date_of_birth, age, diagnosis,
                           neurotype, level, created_at
                    FROM patients
                    WHERE owner_id = %s
                    ORDER BY created_at DESC
                """, (user_id,))

                patients = cursor.fetchall()

                # Processar os pacientes para garantir consistência de formato
                processed_patients = []
                for patient in patients:
                    patient_name = f"{patient.get('first_name', '')} {patient.get('last_name', '')}".strip()
                    processed_patients.append({
                        'id': patient['id'],
                        'name': patient_name if patient_name else f"Paciente {patient['id']}",
                        'first_name': patient['first_name'],
                        'last_name': patient['last_name'],
                        'age': patient.get('age', 'N/A'),
                        'diagnosis': patient.get('diagnosis', 'N/A')
                    })

                logger.debug(f"Pacientes retornados para user {user_id}: {len(processed_patients)} pacientes")

                return {
                    "patients": processed_patients,
                    "total": len(processed_patients),
                    "timestamp": str(datetime.now())
                }
    except Exception as e:
        logger.error(f"Erro ao obter pacientes do usuário {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Modelos Pydantic para os novos endpoints de análise de evolução
from pydantic import BaseModel
from typing import List, Dict, Optional

class PatientEvolutionRequest(BaseModel):
    patient_id: int
    owner_id: int
    session_count: int = 4

class SmartAlertResponse(BaseModel):
    id: Optional[int]
    patient_id: int
    owner_id: int
    alert_type: str
    severity: str
    title: str
    description: str
    recommendations: List[str]
    is_resolved: bool
    generated_at: Optional[str]
    resolved_at: Optional[str]
    metadata: Dict

class EvolutionAnalysisResponse(BaseModel):
    patient_id: int
    owner_id: int
    analysis_result: Dict
    alerts_generated: List[Dict]
    alert_ids_saved: List[int]
    recommendations: List[Dict]
    all_recommendations_count: int
    timestamp: str

class PatientAlertsResponse(BaseModel):
    alerts: List[SmartAlertResponse]
    total: int

@app.post("/analysis/patient_evolution", response_model=EvolutionAnalysisResponse)
async def analyze_patient_evolution(
    request: PatientEvolutionRequest,
    current_user: dict = Depends(require_user_access)
):
    """Analisa a evolução do paciente ao longo das sessões e gera alertas e recomendações"""
    # Verificar se o usuário tem permissão para acessar este paciente
    if request.owner_id != current_user['id']:
        raise HTTPException(status_code=403, detail="Access denied to this resource")

    try:
        # Criar instância do sistema de inteligência clínica
        intelligence_system = ClinicalIntelligenceSystem(
            db_manager=clinical_system.db_manager,
            embedding_generator=clinical_system.embedding_generator,
            openai_interface=clinical_system.openai_interface,
            gemini_interface=clinical_system.gemini_interface
        )

        # Executar análise de evolução
        result = intelligence_system.analyze_patient_evolution_and_alert(
            patient_id=request.patient_id,
            owner_id=request.owner_id,
            session_count=request.session_count
        )

        return EvolutionAnalysisResponse(**result)
    except Exception as e:
        logger.error(f"Erro ao analisar evolução do paciente: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/alerts/patient/{patient_id}", response_model=PatientAlertsResponse)
async def get_patient_alerts(
    patient_id: int,
    current_user: dict = Depends(require_user_access)
):
    """Obtém alertas inteligentes ativos para um paciente"""
    try:
        # Criar instância do sistema de inteligência clínica
        intelligence_system = ClinicalIntelligenceSystem(
            db_manager=clinical_system.db_manager,
            embedding_generator=clinical_system.embedding_generator,
            openai_interface=clinical_system.openai_interface,
            gemini_interface=clinical_system.gemini_interface
        )

        # Obter alertas do paciente
        alerts = intelligence_system.get_patient_alerts(
            patient_id=patient_id,
            owner_id=current_user['id']
        )

        return PatientAlertsResponse(
            alerts=[SmartAlertResponse(**alert.to_dict()) for alert in alerts],
            total=len(alerts)
        )
    except Exception as e:
        logger.error(f"Erro ao obter alertas do paciente: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    current_user: dict = Depends(require_user_access)
):
    """Marca um alerta como resolvido"""
    try:
        # Criar instância do sistema de inteligência clínica
        intelligence_system = ClinicalIntelligenceSystem(
            db_manager=clinical_system.db_manager,
            embedding_generator=clinical_system.embedding_generator,
            openai_interface=clinical_system.openai_interface,
            gemini_interface=clinical_system.gemini_interface
        )

        # Resolver alerta
        success = intelligence_system.resolve_alert(
            alert_id=alert_id,
            owner_id=current_user['id']
        )

        if success:
            return {"success": True, "message": "Alerta resolvido com sucesso"}
        else:
            raise HTTPException(status_code=404, detail="Alerta não encontrado ou já resolvido")
    except Exception as e:
        logger.error(f"Erro ao resolver alerta: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analysis/patient/{patient_id}/summary")
async def get_patient_evolution_summary(
    patient_id: int,
    current_user: dict = Depends(require_user_access)
):
    """Obtém um sumário da evolução do paciente"""
    try:
        # Criar instância do sistema de inteligência clínica
        intelligence_system = ClinicalIntelligenceSystem(
            db_manager=clinical_system.db_manager,
            embedding_generator=clinical_system.embedding_generator,
            openai_interface=clinical_system.openai_interface,
            gemini_interface=clinical_system.gemini_interface
        )

        # Obter sumário de evolução
        summary = intelligence_system.get_patient_evolution_summary(
            patient_id=patient_id,
            owner_id=current_user['id']
        )

        return {"summary": summary}
    except Exception as e:
        logger.error(f"Erro ao obter sumário de evolução do paciente: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analysis/patient/{patient_id}/complete_assessment")
async def get_complete_clinical_assessment(
    patient_id: int,
    current_user: dict = Depends(require_user_access)
):
    """Executa uma avaliação clínica completa com análise de evolução, alertas e recomendações"""
    try:
        # Criar instância do sistema de inteligência clínica
        intelligence_system = ClinicalIntelligenceSystem(
            db_manager=clinical_system.db_manager,
            embedding_generator=clinical_system.embedding_generator,
            openai_interface=clinical_system.openai_interface,
            gemini_interface=clinical_system.gemini_interface
        )

        # Executar avaliação completa
        assessment = intelligence_system.run_complete_clinical_assessment(
            patient_id=patient_id,
            owner_id=current_user['id']
        )

        return {"assessment": assessment}
    except Exception as e:
        logger.error(f"Erro ao executar avaliação clínica completa: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Run the application
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting Clinical Psychology AI System on {host}:{port}")

    uvicorn.run(
        "app:app",  # This is correct since the file is named app.py
        host=host,
        port=port,
        reload=False,  # Disabled for stability
        log_level="info"
    )