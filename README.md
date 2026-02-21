# Clinical Psychology RAG + LoRA System Documentation

## Overview

This is a clinical psychology AI system that combines Retrieval-Augmented Generation (RAG) with LoRA fine-tuned models and Google Gemini integration. The system is designed to assist clinical psychologists and psychopedagogues in managing patient information, retrieving relevant clinical documents, and generating contextually appropriate responses based on patient-specific data.

### Key Features

- **Multi-source RAG System**: Combines Google Gemini, OpenAI and local embedding generation
- **Patient-specific Knowledge Base**: Stores and retrieves patient-specific clinical information
- **Document Management**: Handles various document formats (PDF, DOCX, TXT, CSV, etc.)
- **Clinical Assessment Tools**: Provides structured clinical assessment capabilities
- **Multi-tenancy Support**: Secure access control with user and patient isolation
- **Audit Logging**: Tracks all queries and responses for compliance purposes
- **Advanced Fallback Systems**: Multiple layers of fallback including local AI options when primary AI services are unavailable

## Architecture

The system consists of several core components:

1. **API Layer**: FastAPI-based REST API serving as the main interface
2. **RAG System**: ClinicalRAGSystem handles document retrieval and similarity matching
3. **Embedding Generator**: Multi-tier embedding system with Google Gemini → OpenAI → Local fallbacks
4. **Database**: PostgreSQL with pgvector extension for vector similarity search
5. **User Knowledge Base**: Comprehensive patient context management
6. **Clinical Interfaces**: Google Gemini integration for response generation

## Prerequisites

- Python 3.9 or higher
- PostgreSQL database with pgvector extension
- Google API Key (for embeddings and Gemini)
- (Optional) OpenAI API Key as fallback
- (Optional) Local models

## Installation

1. **Clone the repository** (if applicable) or copy the files
2. **Create and activate a virtual environment**:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:

```bash
pip install -r requirements.txt
```

4. **Set up PostgreSQL with pgvector**:

For Ubuntu/Debian:
```bash
sudo apt-get install postgresql postgresql-contrib
# Install pgvector extension - this may require building from source
# or using a PostgreSQL distribution that includes pgvector
```

For Docker:
```bash
docker run -d --name postgres-vector -e POSTGRES_PASSWORD=your_password -p 5432:5432 ankane/pgvector
```

5. **Configure environment variables**:

Create a `.env` file based on `.env.example`:

```bash
# Google API Key (required for embeddings)
GOOGLE_API_KEY=your_google_api_key_here

# OpenAI API Key (optional, but recommended)
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration (required)
DATABASE_URL=postgresql://username:password@localhost:5432/clinical_db

DEFAULT_MODEL=gpt-3.5-turbo

# RAG Configuration
MAX_CONTEXT_TOKENS=2048
RAG_TOP_K=4
RAG_MIN_SIMILARITY=0.5

# Training Configuration
TRAINING_BATCH_SIZE=4
CHUNK_SIZE=500
CHUNK_OVERLAP=50

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

6. **Initialize the database**:

The system will automatically create tables when started, using the schema from `database/schema.sql`.

## Running the Backend API (Without Frontend)

1. **Ensure your virtual environment is activated**:
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Ensure your database is running** and PostgreSQL with pgvector is properly configured

3. **Set up your environment variables** in the `.env` file

4. **Start the API server**:

```bash
python app.py
```

Or using uvicorn directly:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

5. **The API will be accessible at**: `http://localhost:8000`

## Available Endpoints

### Health Check
- `GET /` - Root endpoint with system information
- `GET /health` - Health check endpoint

### Query System
- `POST /query` - Query the clinical AI system
- Request body:
  ```json
  {
    "query": "Your question here",
    "owner_id": 1,
    "patient_id": "patient123",
    "use_openai": true,
    "model": "gpt-3.5-turbo",
    "k": 4,
    "min_similarity": 0.1
  }
  ```

### Document Management
- `POST /add_document` - Add a clinical document
- `POST /upload_document` - Upload document file (PDF, DOCX, etc.)
- Request: multipart form data with file, owner_id, patient_id, title
- `PUT /history/documents/{history_id}` - Update a document history record
- `DELETE /history/documents/{history_id}` - Delete a document history record
- `GET /history/documents` - Get user's document history

### Patient Information
- `POST /patient_profile` - Get patient profile information
- `POST /assessment` - Run clinical assessment
- `POST /patient/create` - Create new patient
- `PUT /patient/{patient_id}` - Update existing patient information
- `GET /patients/list` - List all patients for logged user
- `GET /patient/{patient_id}` - Get complete patient details
- `GET /api/user/{user_id}/patients` - Get specific user's patients (used by Flask frontend)

### Authentication
- `POST /login` - Authenticate user and get access/refresh tokens
- `POST /register` - Register new user and get access/refresh tokens
- `POST /refresh` - Refresh access token using refresh token
- `POST /logout` - Logout user (client-side token invalidation)

### Cache Management
- `POST /user/{owner_id}/refresh_cache` - Refresh user's data cache including patient list

### History Management
- `GET /history/queries` - Get user's query history
- `PUT /history/queries/{query_id}` - Update a query record
- `DELETE /history/queries/{query_id}` - Delete a query record
- `GET /history/assessments` - Get user's clinical assessment history
- `PUT /history/assessments/{assessment_id}` - Update an assessment record
- `DELETE /history/assessments/{assessment_id}` - Delete an assessment record
- `GET /history/uploads` - Get user's file upload history
- `PUT /history/uploads/{upload_id}` - Update an upload record
- `DELETE /history/uploads/{upload_id}` - Delete an upload record from history
- `GET /history/stats` - Get history statistics for the user

### Metrics and Quality Evaluation
- `GET /metrics/quality/{query_id}` - Get quality metrics for a specific query
- `GET /metrics/aggregated` - Get aggregated metrics for a period
- `POST /metrics/evaluate_response` - Evaluate response quality (for testing/validation)
- `GET /metrics/leaderboard` - Get model leaderboard by quality

### Other Endpoints
- `GET /models` - List available models
- `GET /api/user/{owner_id}/stats` - Get user statistics
- `GET /api/user/{owner_id}/context` - Get user context

## Database Schema

The system uses PostgreSQL with pgvector extension for vector similarity search:

- `users` - Therapist/user accounts
- `patients` - Patient information linked to users
- `patient_sensitivities` - Patient sensitivity profiles
- `documents` - Document chunks with vector embeddings
- `audit_log` - Query/response logging for compliance

## Configuration

### API Keys
- **Google API Key**: Required for Gemini and embeddings
- **OpenAI API Key**: Optional fallback for embeddings
- The system uses a tiered approach: Google Gemini → OpenAI → Local embeddings

### RAG Configuration
- `RAG_TOP_K`: Number of documents to retrieve (default: 4)
- `RAG_MIN_SIMILARITY`: Minimum similarity threshold (default: 0.5)
- `CHUNK_SIZE`: Size of text chunks when splitting documents (default: 500)
- `CHUNK_OVERLAP`: Overlap between chunks (default: 50)

### Model Usage
The system primarily uses Google Gemini models for:
- Embedding generation (using `text-embedding-004` model)
- Response generation (using `gemini-2.5-flash-lite` model)

## Supported File Types for Upload

The system supports uploading and processing of the following file types:
- PDF files
- DOCX and DOC files
- TXT files
- CSV files

## Security

- Multi-tenant architecture ensures users can only access their own data
- Patient data is isolated by owner_id
- All queries are logged for audit purposes
- Database foreign key constraints ensure data integrity

## Troubleshooting

### Common Issues

1. **Database Connection**: Ensure PostgreSQL is running and the connection string is correct
2. **Missing pgvector**: The system requires pgvector extension for vector similarity search
3. **API Keys**: Verify that Google API key is properly set for embeddings and Gemini
4. **Embedding Dimensions**: Ensure consistency in embedding dimensions (Gemini: 768, OpenAI: 1536)

### Logging
The system logs important events to help with debugging:
- Query processing
- Document ingestion
- API failures
- Embedding generation

## Development

The system is designed to be modular with clear separation between:
- API layer (`app.py`)
- Business logic (`core/clinical_ai_system.py`)
- RAG system (`core/rag_system.py`)
- Database operations (`database/db_manager.py`)
- Embedding generation (`utils/embedding_generator.py`)

## Frontend (Optional)

A Streamlit frontend is available in `frontend.py` that provides a user-friendly interface for the system. To run the frontend:

```bash
streamlit run frontend.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Specify license information here if applicable]
# TEAChat_V9
