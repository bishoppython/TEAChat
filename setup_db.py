#!/usr/bin/env python3
"""
Script to set up the PostgreSQL database for the clinical AI system
"""
import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import RealDictCursor

def setup_database():
    # Get database configuration from environment
    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:bispo2026@localhost:5432/clinica_ai")
    
    # Parse the database URL to extract components
    # Format: postgresql://user:password@host:port/database
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
    if not match:
        raise ValueError("Invalid DATABASE_URL format")
    
    user, password, host, port, database = match.groups()
    port = int(port)
    
    print(f"Connecting to PostgreSQL at {host}:{port} with user {user}")
    
    # Connect to PostgreSQL server (default database)
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database='postgres'  # Connect to default postgres database first
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    except psycopg2.OperationalError as e:
        print(f"Failed to connect to PostgreSQL: {e}")
        print("Make sure PostgreSQL is running and credentials are correct")
        return False
    
    # Create the database if it doesn't exist
    with conn.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s", (database,))
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Creating database '{database}'...")
            cursor.execute(f"CREATE DATABASE {database}")
            print(f"Database '{database}' created successfully")
        else:
            print(f"Database '{database}' already exists")
    
    conn.close()
    
    # Now connect to the specific database to set up extensions and tables
    try:
        db_conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
    except psycopg2.OperationalError as e:
        print(f"Failed to connect to database '{database}': {e}")
        return False
    
    print(f"Connected to database '{database}'")
    
    # Enable pgvector extension
    with db_conn.cursor() as cursor:
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            db_conn.commit()
            print("pgvector extension enabled successfully")
        except psycopg2.Error as e:
            print(f"Failed to enable pgvector extension: {e}")
            db_conn.rollback()
            # Try alternative approach
            try:
                cursor.execute("SELECT extname FROM pg_extension;")
                extensions = [row[0] for row in cursor.fetchall()]
                if 'vector' in extensions:
                    print("pgvector extension is already installed")
                else:
                    print("pgvector extension is not available in this PostgreSQL installation")
                    return False
            except:
                print("Could not verify extensions")
                return False
    
    # Create tables by executing schema
    try:
        with open('database/schema.sql', 'r') as schema_file:
            schema_sql = schema_file.read()

        # Split by sample data and take only the schema part
        schema_parts = schema_sql.split('-- Sample insertions for initial setup')
        schema_only = schema_parts[0]

        with db_conn.cursor() as cursor:
            cursor.execute(schema_only)
            db_conn.commit()
            print("Database tables created successfully")
    except FileNotFoundError:
        print("Schema file not found. Creating minimal schema...")
        with db_conn.cursor() as cursor:
            # Create minimal required tables based on schema.sql
            cursor.execute("""
                -- Enable pgvector extension
                CREATE EXTENSION IF NOT EXISTS vector;

                -- Users table for multi-tenant support
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    full_name VARCHAR(255),
                    email VARCHAR(255) UNIQUE,
                    role VARCHAR(50) DEFAULT 'therapist',
                    password_hash VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Index for faster user lookups
                CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

                -- Patients table to track patient information
                CREATE TABLE IF NOT EXISTS patients (
                    id SERIAL PRIMARY KEY,  -- ID primário do paciente
                    patient_id VARCHAR(100),  -- Identificador personalizado opcional do paciente
                    owner_id INTEGER NOT NULL,  -- therapist who owns this patient
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    date_of_birth DATE,
                    diagnosis TEXT,
                    age INTEGER,
                    neurotype VARCHAR(100) DEFAULT '',
                    level VARCHAR(50) DEFAULT '',
                    description TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Index for faster patient lookups by owner
                CREATE INDEX IF NOT EXISTS idx_patients_owner_id ON patients(owner_id);
                CREATE INDEX IF NOT EXISTS idx_patients_patient_id ON patients(patient_id);

                -- Sensitivity profiles for patients
                CREATE TABLE IF NOT EXISTS patient_sensitivities (
                    id SERIAL PRIMARY KEY,
                    patient_id INTEGER NOT NULL,  -- FK para patients.id
                    sensitivity_type VARCHAR(50) NOT NULL,  -- e.g., 'noise', 'touch', 'light'
                    sensitivity_level VARCHAR(20),          -- e.g., 'low', 'medium', 'high'
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Index for sensitivity lookups
                CREATE INDEX IF NOT EXISTS idx_patient_sensitivities_patient_id ON patient_sensitivities(patient_id);

                -- Documents table with vector embeddings
                CREATE TABLE IF NOT EXISTS documents (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    owner_id INTEGER NOT NULL,  -- who owns this doc
                    patient_id INTEGER NOT NULL,  -- FK para patients.id
                    title VARCHAR(500),
                    text TEXT NOT NULL,
                    source_type VARCHAR(50) DEFAULT 'note',  -- note, assessment, questionnaire, etc.
                    chunk_order INTEGER DEFAULT 0,  -- order of chunks if document was split
                    chunk_id VARCHAR(100),  -- identifier for this chunk
                    embedding vector(768),  -- Gemini text-embedding-004 is 768-dim
                    metadata JSONB DEFAULT '{}',  -- extra metadata like tags, flags, etc.
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Indexes for fast retrieval
                CREATE INDEX IF NOT EXISTS idx_documents_owner_id ON documents(owner_id);
                CREATE INDEX IF NOT EXISTS idx_documents_patient_id ON documents(patient_id);
                CREATE INDEX IF NOT EXISTS idx_documents_chunk_id ON documents(chunk_id);

                -- Vector index for similarity search (IVFFlat with 100 lists)
                -- Adjust the number of lists based on your data size and performance needs
                CREATE INDEX IF NOT EXISTS idx_documents_embedding ON documents USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

                -- Index for chronological document access
                CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at);

                -- Audit log table for tracking RAG queries and responses
                CREATE TABLE IF NOT EXISTS audit_log (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    patient_id INTEGER,
                    query TEXT NOT NULL,
                    response TEXT,
                    model_used VARCHAR(100),  -- e.g., 'gemini', 'openai', 'hybrid'
                    tokens_used INTEGER,
                    response_time_ms INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Indexes for audit log
                CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON audit_log(user_id);
                CREATE INDEX IF NOT EXISTS idx_audit_log_patient_id ON audit_log(patient_id);
                CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);

                -- Tabela para armazenar histórico de avaliações clínicas
                CREATE TABLE IF NOT EXISTS clinical_assessments (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    patient_id INTEGER NOT NULL,
                    query TEXT NOT NULL,
                    response TEXT NOT NULL,
                    assessment_type VARCHAR(100) DEFAULT 'clinical',
                    confidence_score FLOAT DEFAULT 0.0,
                    processing_time FLOAT,
                    model_used VARCHAR(100),
                    tokens_used INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Índices para histórico de avaliações
                CREATE INDEX IF NOT EXISTS idx_clinical_assessments_user_id ON clinical_assessments(user_id);
                CREATE INDEX IF NOT EXISTS idx_clinical_assessments_patient_id ON clinical_assessments(patient_id);
                CREATE INDEX IF NOT EXISTS idx_clinical_assessments_created_at ON clinical_assessments(created_at);

                -- Tabela para armazenar histórico de uploads de arquivos
                CREATE TABLE IF NOT EXISTS file_uploads (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    patient_id INTEGER NOT NULL,
                    title VARCHAR(500),
                    original_filename VARCHAR(255) NOT NULL,
                    file_path VARCHAR(500),
                    file_size BIGINT,
                    file_type VARCHAR(100),
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(50) DEFAULT 'active', -- active, deleted, processed, etc.
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Índices para histórico de uploads
                CREATE INDEX IF NOT EXISTS idx_file_uploads_user_id ON file_uploads(user_id);
                CREATE INDEX IF NOT EXISTS idx_file_uploads_patient_id ON file_uploads(patient_id);
                CREATE INDEX IF NOT EXISTS idx_file_uploads_upload_date ON file_uploads(upload_date);
                CREATE INDEX IF NOT EXISTS idx_file_uploads_status ON file_uploads(status);

                -- Tabela para manter histórico de documentos (edições, exclusões)
                CREATE TABLE IF NOT EXISTS document_history (
                    id SERIAL PRIMARY KEY,
                    action_type VARCHAR(50) NOT NULL, -- 'created', 'updated', 'deleted'
                    user_id INTEGER NOT NULL,
                    patient_id INTEGER NOT NULL,
                    title VARCHAR(500),
                    text_content TEXT,
                    source_type VARCHAR(50) DEFAULT 'note',
                    metadata JSONB DEFAULT '{}',
                    action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    action_performed_by INTEGER,
                    old_values JSONB, -- Valores antigos antes da atualização
                    new_values JSONB, -- Novos valores após a atualização
                    status VARCHAR(50) -- active, deleted, archived
                );

                -- Índices para histórico de documentos
                CREATE INDEX IF NOT EXISTS idx_document_history_user_id ON document_history(user_id);
                CREATE INDEX IF NOT EXISTS idx_document_history_patient_id ON document_history(patient_id);
                CREATE INDEX IF NOT EXISTS idx_document_history_action_type ON document_history(action_type);
                CREATE INDEX IF NOT EXISTS idx_document_history_action_date ON document_history(action_date);
            """)
            db_conn.commit()
            print("Minimal database schema created successfully")
    
    db_conn.close()
    print("Database setup completed successfully!")
    return True

if __name__ == "__main__":
    setup_database()