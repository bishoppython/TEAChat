-- Schema para armazenamento de métricas de qualidade do sistema RAG

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