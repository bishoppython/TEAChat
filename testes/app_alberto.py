"""
Main application entry point for the Clinical Psychology RAG + LoRA System
"""
import os
import logging
from typing import Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Depends, File, UploadFile, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

# Configurações de segurança
# Configurar múltiplos esquemas para lidar com diferentes tipos de hashes
pwd_context = CryptContext(
    schemes=["pbkdf2_sha256", "bcrypt"],
    deprecated="auto"
)

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Clinical Psychology AI System",
    description="RAG + LoRA system for clinical psychology applications",
    version="1.0.0"
)

# Global system instance
clinical_system: Optional[ClinicalAISystem] = None

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
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
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

# Modelos Pydantic para requisições/respostas da API
class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    full_name: str
    email: str
    password: str
    role: str = "therapist"

class Token(BaseModel):
    access_token: str
    token_type: str

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
    access_token = create_access_token(
        data={"sub": str(user['id']), "username": user['username']},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

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

    # Criar e retornar token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user_id), "username": user_data.username},
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

# Endpoint de logout (cliente-side, apenas invalida o token no frontend)
@app.post("/logout")
async def logout():
    # Este endpoint é mais conceitual - o logout real ocorre no frontend
    # onde o token JWT é removido do armazenamento local
    return {"message": "Logged out successfully"}

# Pydantic models for API requests/responses
class QueryRequest(BaseModel):
    query: str
    owner_id: int
    patient_id: Optional[str] = None
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
    patient_id: str

class PatientProfileResponse(BaseModel):
    patient_info: dict
    sensitivities: list
    documents_count: int

class AssessmentRequest(BaseModel):
    query: str
    owner_id: int
    patient_id: str
    assessment_type: str = "general"

class AssessmentResponse(BaseModel):
    assessment_type: str
    patient_id: str
    query: str
    response: str
    retrieved_evidence: int
    confidence_score: float
    processing_time: float
    model_used: str

class PatientCreateRequest(BaseModel):
    owner_id: int
    first_name: str
    last_name: str
    birth_date: str
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
    """Dependency to get the clinical system instance"""
    if clinical_system is None:
        raise HTTPException(status_code=500, detail="Clinical system not initialized")
    return clinical_system

@app.on_event("startup")
async def startup_event():
    """Initialize the clinical AI system on startup"""
    global clinical_system
    
    try:
        # Initialize database manager
        db_manager = DatabaseManager()
        
        # Initialize embedding generator with API keys
        embedder = CachedEmbeddingGenerator()
        
        # Initialize clinical AI system
        clinical_system = ClinicalAISystem(
            db_manager=db_manager,
            embedding_generator=embedder,
            default_model=os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo")
        )
        
        logger.info("Clinical AI System initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize clinical system: {e}")
        raise

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Clinical Psychology AI System API",
        "status": "running",
        "endpoints": [
            "/query",
            "/add_document", 
            "/patient_profile",
            "/assessment"
        ]
    }

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    """Query the clinical AI system"""
    logger.info(f"Recebendo consulta: '{request.query}' para owner_id: {request.owner_id}, patient_id: {request.patient_id}")
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
        return QueryResponse(
            query=result["query"],
            response=result["response"],
            retrieved_documents_count=len(result["rag_result"]["retrieved_documents"]),
            response_time_ms=result["response_time_ms"],
            model_used=result["model_used"]
        )
    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/add_document", response_model=DocumentResponse)
async def add_document_endpoint(request: DocumentRequest):
    """Add a clinical document to the system"""
    try:
        chunk_ids = clinical_system.add_clinical_document(
            owner_id=request.owner_id,
            patient_id=request.patient_id,
            title=request.title,
            text=request.text,
            source_type=request.source_type,
            metadata=request.metadata
        )
        
        return DocumentResponse(
            document_chunk_ids=chunk_ids,
            success=True,
            message=f"Successfully added document with {len(chunk_ids)} chunks"
        )
    except Exception as e:
        logger.error(f"Error adding document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/patient_profile", response_model=PatientProfileResponse)
async def patient_profile_endpoint(request: PatientProfileRequest):
    """Get patient profile information"""
    try:
        profile = clinical_system.get_patient_profile(
            request.owner_id,
            request.patient_id
        )
        
        if not profile:
            raise HTTPException(status_code=404, detail="Patient not found")
        
        # Count documents for this patient (this would require a method in the DB manager)
        # For now, we'll return what we have
        return PatientProfileResponse(
            patient_info=profile,
            sensitivities=profile.get('sensitivities', []),
            documents_count=0  # This would come from a count query
        )
    except Exception as e:
        logger.error(f"Error getting patient profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/assessment", response_model=AssessmentResponse)
async def assessment_endpoint(request: AssessmentRequest):
    """Run a clinical assessment"""
    try:
        result = clinical_system.run_clinical_assessment(
            query=request.query,
            owner_id=request.owner_id,
            patient_id=request.patient_id,
            assessment_type=request.assessment_type
        )
        
        return AssessmentResponse(
            assessment_type=result["assessment_type"],
            patient_id=result["patient_id"],
            query=result["query"],
            response=result["response"],
            retrieved_evidence=result["retrieved_evidence"],
            confidence_score=result["confidence_score"],
            processing_time=result["processing_time"],
            model_used=result["model_used"]
        )
    except Exception as e:
        logger.error(f"Error running assessment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": str(clinical_system.db_manager.get_connection if clinical_system else "not initialized")
    }

@app.get("/models")
async def list_models():
    """List available models (informational only, OpenAI handled via API)"""
    if clinical_system and clinical_system.openai_client:
        return {"models": ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"], "message": "OpenAI models available via API"}
    else:
        return {"models": [], "message": "OpenAI client not available"}

@app.get("/api/user/{owner_id}/stats")
async def get_user_stats(owner_id: int):
    """
    Obtém estatísticas da base de conhecimento do usuário
    Similar ao Guru TI - mostra todos os documentos e pacientes do usuário
    """
    try:
        stats = clinical_system.get_user_statistics(owner_id)
        return {
            "owner_id": owner_id,
            "statistics": stats,
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/user/{owner_id}/context")
async def get_user_context(owner_id: int, patient_id: int = None):
    """
    Obtém contexto completo do usuário (todos os documentos)
    Similar ao Guru TI que tem toda a base sempre disponível
    """
    try:
        context = clinical_system.user_kb.get_user_context(owner_id, patient_id)
        return {
            "owner_id": owner_id,
            "patient_id": patient_id,
            "context": context,
            "timestamp": str(datetime.now())
        }
    except Exception as e:
        logger.error(f"Error getting user context: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/upload_document")
async def upload_document(
    file: UploadFile = File(...),
    owner_id: int = Form(...),
    patient_id: int = Form(...),
    title: str = Form(None),
    source_type: str = Form("uploaded_file"),
    current_user: dict = Depends(require_user_access)
):
    """Upload and process a document file (PDF, DOCX, TXT, etc.) - protected by authentication"""
    logger.info(f"Iniciando upload do arquivo: {file.filename} para owner_id: {owner_id}, patient_id: {patient_id}")
    try:
        # Verificar se o paciente pertence ao owner_id informado
        patient_owner = clinical_system.db_manager.get_patient_owner_id(patient_id)
        if patient_owner is None:
            raise HTTPException(status_code=404, detail=f"Paciente com ID {patient_id} não encontrado")
        if patient_owner != owner_id:
            logger.warning(f"Owner mismatch: documento owner_id={owner_id}, paciente owner_id={patient_owner}. Usando owner_id do paciente.")
            # Usar o owner_id correto do paciente para evitar erro na trigger
            owner_id = patient_owner
        
        # Read file content
        content = await file.read()

        # Get file extension
        file_extension = file.filename.split('.')[-1].lower()
        logger.info(f"Formato do arquivo detectado: {file_extension}")

        # Process content based on file type
        text_content = ""

        if file_extension == 'pdf':
            from PyPDF2 import PdfReader
            import io
            pdf_reader = PdfReader(io.BytesIO(content))
            text_content = ""
            for page in pdf_reader.pages:
                text_content += page.extract_text()
            # Remover caracteres NUL
            text_content = text_content.replace('\x00', '')

        elif file_extension in ['doc', 'docx']:
            from docx import Document
            import io
            doc = Document(io.BytesIO(content))
            text_content = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            # Remover caracteres NUL
            text_content = text_content.replace('\x00', '')

        elif file_extension in ['csv']:
            import pandas as pd
            import io
            df = pd.read_csv(io.BytesIO(content))
            text_content = df.to_string()
            # Remover caracteres NUL
            text_content = text_content.replace('\x00', '')

        elif file_extension in ['txt', 'text']:
            text_content = content.decode('utf-8')
            # Remover caracteres NUL
            text_content = text_content.replace('\x00', '')

        else:
            # For any other format, try to decode as text
            try:
                text_content = content.decode('utf-8')
            except:
                # If that fails, try with error handling
                text_content = content.decode('utf-8', errors='ignore')

        # IMPORTANTE: Remover caracteres NUL (0x00) que o PostgreSQL não aceita
        text_content = text_content.replace('\x00', '')
        
        logger.info(f"Conteúdo do arquivo extraído. Tamanho: {len(text_content)} caracteres")

        # Set title to filename if not provided
        if not title:
            title = file.filename

        # Add document to the system
        chunk_ids = clinical_system.add_clinical_document(
            owner_id=owner_id,
            patient_id=patient_id,
            title=title,
            text=text_content,
            source_type=source_type,
            metadata={"original_filename": file.filename, "file_type": file_extension}
        )

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
        # Criar paciente no banco de dados
        with clinical_system.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # Inserir paciente
                cursor.execute("""
                    INSERT INTO patients
                    (owner_id, first_name, last_name, birth_date, age, diagnosis,
                     neurotype, level, description, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    RETURNING id
                """, (
                    request.owner_id,
                    request.first_name,
                    request.last_name,
                    request.birth_date,
                    request.age,
                    request.diagnosis,
                    request.neurotype,
                    request.level,
                    request.description
                ))

                patient_id = cursor.fetchone()[0]
                conn.commit()

        logger.info(f"Paciente {request.first_name} {request.last_name} criado com ID: {patient_id}")

        return PatientCreateResponse(
            patient_id=patient_id,
            success=True,
            message=f"Paciente {request.first_name} {request.last_name} cadastrado com sucesso"
        )
    except Exception as e:
        logger.error(f"Erro ao criar paciente: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/patients/list")
async def list_patients(current_user: dict = Depends(require_user_access)):
    """Listar todos os pacientes do usuário logado"""
    try:
        with clinical_system.db_manager.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, first_name, last_name, birth_date, age, diagnosis,
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
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do paciente: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Run the application
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info(f"Starting Clinical Psychology AI System on {host}:{port}")

    uvicorn.run(
        "app_alberto:app",  # This is correct since the file is named app_alberto.py
        host=host,
        port=port,
        reload=False,  # Disabled for stability
        log_level="info"
    )