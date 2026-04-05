-- PostgreSQL schema for clinical psychology RAG system with pgvector
-- Requires pgvector extension to be installed

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Users table for multi-tenant support
CREATE TABLE users (
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
CREATE INDEX idx_users_username ON users(username);

-- Patients table to track patient information
CREATE TABLE patients (
    id SERIAL PRIMARY KEY,  -- ID primário do paciente
    patient_id VARCHAR(100),  -- Identificador personalizado opcional do paciente
    owner_id INTEGER NOT NULL REFERENCES users(id),  -- therapist who owns this patient
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    diagnosis TEXT,
    age INTEGER,
    neurotype VARCHAR(100) DEFAULT '',
    level VARCHAR(50) DEFAULT '',
    description TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ensure only the owner can access their patients
    CONSTRAINT fk_patient_owner FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Index for faster patient lookups by owner
CREATE INDEX idx_patients_owner_id ON patients(owner_id);
CREATE INDEX idx_patients_patient_id ON patients(patient_id);

-- Sensitivity profiles for patients
CREATE TABLE patient_sensitivities (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,  -- FK para patients.id
    sensitivity_type VARCHAR(50) NOT NULL,  -- e.g., 'noise', 'touch', 'light'
    sensitivity_level VARCHAR(20),          -- e.g., 'low', 'medium', 'high'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for sensitivity lookups
CREATE INDEX idx_patient_sensitivities_patient_id ON patient_sensitivities(patient_id);

-- Documents table with vector embeddings (multiple columns for different dimensions)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,  -- who owns this doc
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,  -- FK para patients.id
    title VARCHAR(500),
    text TEXT NOT NULL,
    source_type VARCHAR(50) DEFAULT 'note',  -- note, assessment, questionnaire, etc.
    chunk_order INTEGER DEFAULT 0,  -- order of chunks if document was split
    chunk_id VARCHAR(100),  -- identifier for this chunk
    embedding_768 vector(768),  -- For Google Gemini embeddings
    embedding_1536 vector(1536), -- For OpenAI embeddings
    embedding_3072 vector(3072), -- For embeddings
    metadata JSONB DEFAULT '{}',  -- extra metadata like tags, flags, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ensure only owner can access their documents
    CONSTRAINT fk_document_owner FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_document_patient FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE
);

-- Indexes for fast retrieval
CREATE INDEX idx_documents_owner_id ON documents(owner_id);
CREATE INDEX idx_documents_patient_id ON documents(patient_id);
CREATE INDEX idx_documents_chunk_id ON documents(chunk_id);

-- Vector indexes for similarity search (IVFFlat with 100 lists) - optimized for each dimension
CREATE INDEX idx_documents_embedding_768 ON documents USING ivfflat (embedding_768 vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_documents_embedding_1536 ON documents USING ivfflat (embedding_1536 vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_documents_embedding_3072 ON documents USING ivfflat (embedding_3072 vector_cosine_ops) WITH (lists = 100);

-- Index for chronological document access
CREATE INDEX idx_documents_created_at ON documents(created_at);

-- Audit log table for tracking RAG queries and responses
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    patient_id INTEGER REFERENCES patients(id) ON DELETE SET NULL,  -- FK para patients.id
    query TEXT NOT NULL,
    response TEXT,
    model_used VARCHAR(100),  -- e.g., 'gemini', 'openai', 'hybrid'
    tokens_used INTEGER,
    response_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for audit log
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_patient_id ON audit_log(patient_id);
CREATE INDEX idx_audit_log_created_at ON audit_log(created_at);

-- Function to ensure document owner matches patient owner
CREATE OR REPLACE FUNCTION check_document_patient_ownership()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT owner_id FROM patients WHERE id = NEW.patient_id) != NEW.owner_id THEN
        RAISE EXCEPTION 'Document owner must match patient owner';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to enforce ownership constraint
CREATE TRIGGER trigger_check_document_patient_ownership
    BEFORE INSERT OR UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION check_document_patient_ownership();

-- Tabela para armazenar histórico de avaliações clínicas
CREATE TABLE clinical_assessments (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
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
CREATE INDEX idx_clinical_assessments_user_id ON clinical_assessments(user_id);
CREATE INDEX idx_clinical_assessments_patient_id ON clinical_assessments(patient_id);
CREATE INDEX idx_clinical_assessments_created_at ON clinical_assessments(created_at);

-- Tabela para armazenar histórico de uploads de arquivos
CREATE TABLE file_uploads (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
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
CREATE INDEX idx_file_uploads_user_id ON file_uploads(user_id);
CREATE INDEX idx_file_uploads_patient_id ON file_uploads(patient_id);
CREATE INDEX idx_file_uploads_upload_date ON file_uploads(upload_date);
CREATE INDEX idx_file_uploads_status ON file_uploads(status);

-- Tabela para manter histórico de documentos (edições, exclusões)
CREATE TABLE document_history (
    id SERIAL PRIMARY KEY,
    action_type VARCHAR(50) NOT NULL, -- 'created', 'updated', 'deleted'
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    title VARCHAR(500),
    text_content TEXT,
    source_type VARCHAR(50) DEFAULT 'note',
    metadata JSONB DEFAULT '{}',
    action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    action_performed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    old_values JSONB, -- Valores antigos antes da atualização
    new_values JSONB, -- Novos valores após a atualização
    status VARCHAR(50) --DEFAULT 'active' -- active, deleted, archived
);

-- Índices para histórico de documentos
CREATE INDEX idx_document_history_user_id ON document_history(user_id);
CREATE INDEX idx_document_history_patient_id ON document_history(patient_id);
CREATE INDEX idx_document_history_action_type ON document_history(action_type);
CREATE INDEX idx_document_history_action_date ON document_history(action_date);

-- Tabela para armazenar métricas de qualidade por consulta
CREATE TABLE IF NOT EXISTS query_quality_metrics (
    id SERIAL PRIMARY KEY,
    query_id INTEGER REFERENCES audit_log(id),  -- Vincular à consulta original
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Métricas de latência
    latency_seconds DECIMAL(10, 6),
    response_time_ms INTEGER,

    -- Métricas de custo
    model_name VARCHAR(100),
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    input_cost_usd DECIMAL(10, 6),
    output_cost_usd DECIMAL(10, 6),
    total_cost_usd DECIMAL(10, 6),
    cost_per_thousand_tokens DECIMAL(10, 8),

    -- Métricas de retrieval
    retrieval_precision DECIMAL(5, 4),
    retrieval_recall DECIMAL(5, 4),
    retrieval_f1 DECIMAL(5, 4),
    retrieval_true_positives INTEGER,
    retrieval_false_positives INTEGER,
    retrieval_false_negatives INTEGER,
    retrieval_retrieved_count INTEGER,
    retrieval_relevant_count INTEGER,

    -- Métricas de fidelidade
    faithfulness_score DECIMAL(5, 4),
    faithfulness_statements_count INTEGER,
    faithfulness_supported_statements INTEGER,
    faithfulness_unsupported_statements INTEGER,

    -- Métricas de relevância
    answer_relevance_score DECIMAL(5, 4),
    answer_semantic_similarity DECIMAL(5, 4),
    answer_keyword_overlap DECIMAL(5, 4),
    context_relevance_score DECIMAL(5, 4),
    context_semantic_similarity DECIMAL(5, 4),
    context_keyword_overlap DECIMAL(5, 4),

    -- Métricas NDCG
    ndcg_score DECIMAL(5, 4),
    ndcg_dcg DECIMAL(8, 3),
    ndcg_idcg DECIMAL(8, 3),
    ndcg_k INTEGER,
    ndcg_retrieved_count INTEGER,
    ndcg_relevant_in_top_k INTEGER,

    -- Métricas de legibilidade
    flesch_reading_ease DECIMAL(6, 2),
    flesch_kincaid_grade DECIMAL(5, 2),
    smog_index DECIMAL(5, 2),
    coleman_liau_index DECIMAL(5, 2),
    automated_readability_index DECIMAL(5, 2),
    avg_sentence_length DECIMAL(6, 2),
    avg_word_length DECIMAL(6, 2),
    complex_words_ratio DECIMAL(5, 4),
    readability_level VARCHAR(50),

    -- Pontuação geral de qualidade
    overall_quality_score DECIMAL(5, 4),

    -- Dados brutos para análise futura
    faithfulness_details JSONB,
    metric_details JSONB
);

-- Índices para otimização de consultas
CREATE INDEX IF NOT EXISTS idx_query_metrics_query_id ON query_quality_metrics(query_id);
CREATE INDEX IF NOT EXISTS idx_query_metrics_timestamp ON query_quality_metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_query_metrics_overall_score ON query_quality_metrics(overall_quality_score);
CREATE INDEX IF NOT EXISTS idx_query_metrics_model_name ON query_quality_metrics(model_name);

-- Tabela para armazenar métricas agregadas por período
CREATE TABLE IF NOT EXISTS aggregated_metrics (
    id SERIAL PRIMARY KEY,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    aggregation_type VARCHAR(50),  -- 'daily', 'weekly', 'monthly'

    -- Contadores
    total_queries INTEGER DEFAULT 0,
    total_with_metrics INTEGER DEFAULT 0,

    -- Métricas agregadas
    avg_latency_seconds DECIMAL(10, 6),
    avg_response_time_ms INTEGER,
    avg_overall_quality_score DECIMAL(5, 4),
    avg_retrieval_precision DECIMAL(5, 4),
    avg_retrieval_recall DECIMAL(5, 4),
    avg_retrieval_f1 DECIMAL(5, 4),
    avg_faithfulness_score DECIMAL(5, 4),
    avg_answer_relevance_score DECIMAL(5, 4),
    avg_context_relevance_score DECIMAL(5, 4),
    avg_ndcg_score DECIMAL(5, 4),
    avg_flesch_reading_ease DECIMAL(6, 2),

    -- Métricas de custo
    total_input_tokens BIGINT,
    total_output_tokens BIGINT,
    total_cost_usd DECIMAL(12, 6),

    -- Métricas de distribuição
    p50_latency_seconds DECIMAL(10, 6),
    p95_latency_seconds DECIMAL(10, 6),
    p99_latency_seconds DECIMAL(10, 6),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice para consultas de agregação
CREATE INDEX IF NOT EXISTS idx_agg_metrics_period ON aggregated_metrics(period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_agg_metrics_type ON aggregated_metrics(aggregation_type);

-- Tabela para armazenar avaliações binárias (aceitação)
CREATE TABLE IF NOT EXISTS binary_acceptance_ratings (
    id SERIAL PRIMARY KEY,
    query_id INTEGER REFERENCES audit_log(id),
    rating BOOLEAN NOT NULL,  -- TRUE = útil, FALSE = não útil
    rater_id INTEGER,  -- ID do avaliador (usuário ou sistema)
    rating_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,

    UNIQUE(query_id, rater_id)  -- Um avaliador pode avaliar cada consulta apenas uma vez
);

-- Índice para avaliações
CREATE INDEX IF NOT EXISTS idx_binary_ratings_query_id ON binary_acceptance_ratings(query_id);
CREATE INDEX IF NOT EXISTS idx_binary_ratings_rating ON binary_acceptance_ratings(rating);

-- Tabela para armazenar análise qualitativa de erros
CREATE TABLE IF NOT EXISTS qualitative_error_analysis (
    id SERIAL PRIMARY KEY,
    query_id INTEGER REFERENCES audit_log(id),
    error_category VARCHAR(100),  -- 'factual_error', 'relevance_issue', 'coherence_problem', etc.
    severity_level VARCHAR(20),   -- 'low', 'medium', 'high', 'critical'
    description TEXT,
    suggested_fix TEXT,
    analyzed_by INTEGER,  -- ID do analista
    analysis_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice para análise de erros
CREATE INDEX IF NOT EXISTS idx_error_analysis_query_id ON qualitative_error_analysis(query_id);
CREATE INDEX IF NOT EXISTS idx_error_analysis_category ON qualitative_error_analysis(error_category);

-- Tabela para armazenar análises de evolução do paciente
CREATE TABLE IF NOT EXISTS patient_evolution_analysis (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    evolution_score DECIMAL(5, 4),
    evolution_pattern VARCHAR(50), -- 'positive', 'stagnant', 'negative', 'unknown'
    session_count INTEGER,
    clinical_notes TEXT,
    recommendations JSONB,
    alerts_generated JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para análise de evolução
CREATE INDEX IF NOT EXISTS idx_patient_evolution_patient_id ON patient_evolution_analysis(patient_id);
CREATE INDEX IF NOT EXISTS idx_patient_evolution_owner_id ON patient_evolution_analysis(owner_id);
CREATE INDEX IF NOT EXISTS idx_patient_evolution_analysis_date ON patient_evolution_analysis(analysis_date);

-- Tabela para armazenar alertas inteligentes
CREATE TABLE IF NOT EXISTS smart_alerts (
    id SERIAL PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    owner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    alert_type VARCHAR(50), -- 'stagnation', 'regression', 'treatment_change_needed', 'insufficient_data', 'positive_trend'
    severity VARCHAR(20), -- 'low', 'medium', 'high', 'critical'
    title VARCHAR(200),
    description TEXT,
    recommendations TEXT[], -- Array de recomendações
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    is_resolved BOOLEAN DEFAULT FALSE,
    metadata JSONB
);

-- Índices para alertas inteligentes
CREATE INDEX IF NOT EXISTS idx_smart_alerts_patient_id ON smart_alerts(patient_id);
CREATE INDEX IF NOT EXISTS idx_smart_alerts_owner_id ON smart_alerts(owner_id);
CREATE INDEX IF NOT EXISTS idx_smart_alerts_alert_type ON smart_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_smart_alerts_severity ON smart_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_smart_alerts_is_resolved ON smart_alerts(is_resolved);
CREATE INDEX IF NOT EXISTS idx_smart_alerts_generated_at ON smart_alerts(generated_at);

-- Sample insertions for initial setup
-- Create a user (example: Valkyria)
INSERT INTO users (username, full_name, email, role)
VALUES ('valkyria', 'Valkyria Therapist', 'valkyria@example.com', 'psychopedagogue')
ON CONFLICT (username) DO NOTHING;

-- -- Create sample patients
-- INSERT INTO patients (patient_id, owner_id, first_name, last_name, age, diagnosis)
-- VALUES
--     ('lucas', 1, 'Lucas', 'Silva', 8, 'Learning difficulties, hypersensitivity auditory'),
--     ('monica', 1, 'Mônica', 'Santos', 10, 'Attention Deficit Disorder'),
--     ('suzana', 1, 'Suzana', 'Costa', 7, 'Sensory Processing Disorder')
-- ON CONFLICT (patient_id) DO NOTHING;

-- -- Add sample sensitivities (only if patients exist)
-- INSERT INTO patient_sensitivities (patient_id, sensitivity_type, sensitivity_level, description)
-- SELECT 1, 'noise', 'high', 'Hypersensitivity to loud sounds and background noise'
-- WHERE EXISTS (SELECT 1 FROM patients WHERE id = 1)
-- UNION ALL
-- SELECT 1, 'touch', 'medium', 'Sensitivity to certain textures'
-- WHERE EXISTS (SELECT 1 FROM patients WHERE id = 1)
-- UNION ALL
-- SELECT 2, 'light', 'medium', 'Prefers dim lighting conditions'
-- WHERE EXISTS (SELECT 1 FROM patients WHERE id = 2);