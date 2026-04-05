"""
Módulo de pré-processamento de dados para sistema RAG de psicologia clínica
Lida com chunking de documentos, limpeza e preparação para embeddings
"""
import re
from typing import List, Dict, Any, Tuple
try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    from langchain_core.text_splitter import RecursiveCharacterTextSplitter
import pandas as pd
# from PyPDF2 import PdfReader
import fitz  # PyMuPDF
from docx import Document as DocxDocument
import os
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClinicalDataProcessor:
    """
    Class to handle preprocessing of clinical documents including
    chunking, cleaning, and metadata extraction
    """
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialize the processor with chunking parameters
        
        :param chunk_size: Maximum size of text chunks in tokens/characters
        :param chunk_overlap: Overlap between chunks to maintain context
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Inicializar divisor de texto
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,  # Usando comprimento de caractere (ajustar se usar abordagem baseada em tokens)
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    # ---------------------- Usando PyMuPDF ----------------------
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        try:
            doc = fitz.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text() + "\n"
            return self.remove_null_bytes(text)
        except Exception as e:
            logger.error(f"Erro ao extrair texto do PDF {pdf_path}: {e}")
            return ""

    
    def extract_text_from_docx(self, docx_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = DocxDocument(docx_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting text from DOCX {docx_path}: {e}")
            return ""
    
    def extract_text_from_txt(self, txt_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(txt_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error extracting text from TXT {txt_path}: {e}")
            return ""
    
    def clean_clinical_text(self, text: str) -> str:
        """
        Limpar texto clínico removendo ou anonimizando informações sensíveis
        """
        # Remover ou anonimizar nomes de pacientes (abordagem básica)
        # Em uma implementação real, você usaria técnicas NLP mais sofisticadas
        text = re.sub(r'\bPatient Name:\s*[A-Z][a-z]+\s[A-Z][a-z]+\b', 'Patient Name: [ANONYMIZED]', text)
        text = re.sub(r'\bName:\s*[A-Z][a-z]+\s[A-Z][a-z]+\b', 'Name: [ANONYMIZED]', text)

        # Remover ou anonimizar datas (abordagem básica)
        # Formato: DD/MM/YYYY ou YYYY-MM-DD
        text = re.sub(r'\b(\d{1,2}/\d{1,2}/\d{4})\b', '[DATE]', text)
        text = re.sub(r'\b(\d{4}-\d{2}-\d{2})\b', '[DATE]', text)

        # Remover ou anonimizar endereços de email
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]', text)

        # Remover ou anonimizar números de telefone
        text = re.sub(r'\b(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE]', text)

        # Normalizar espaços em branco
        text = re.sub(r'\s+', ' ', text).strip()

        return text
    
    def remove_null_bytes(self, text: str) -> str:
        """Remove null byte characters from text"""
        return re.sub(r'[\x00]', '', text)

    
    def extract_metadata_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extrair metadados de texto clínico como:
        - Data da sessão
        - Nome do terapeuta
        - Informações do paciente
        - Flags de sensibilidade
        """
        metadata = {
            "date": None,
            "therapist": None,
            "session_type": None,
            "sensory_flags": [],
            "behavioral_notes": [],
            "diagnosis_mentions": []
        }

        # Extrair data (vários formatos)
        date_patterns = [
            r'(?:Date|Dated|Session Date):\s*([A-Za-z0-9/\-.,\s]+)',
            r'date of (?:assessment|session)\s*:?\s*([A-Za-z0-9/\-.,\s]+)',
        ]

        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata["date"] = match.group(1).strip()
                break

        # Extrair nome do terapeuta
        therapist_patterns = [
            r'(?:Therapist|Conducted by|Assessment by):\s*([A-Za-z\s]+)',
            r'(?:Facilitated by|Evaluated by):\s*([A-Za-z\s]+)',
        ]

        for pattern in therapist_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                metadata["therapist"] = match.group(1).strip()
                break

        # Extrair tipo de sessão
        session_types = [
            "initial assessment", "follow-up session", "progress evaluation",
            "parent consultation", "behavioral intervention", "sensory evaluation"
        ]

        for session_type in session_types:
            if session_type.lower() in text.lower():
                metadata["session_type"] = session_type
                break

        # Extrair flags sensoriais
        sensory_keywords = [
            "hypersensitive", "hyposensitive", "sensory overload", "noise sensitive",
            "auditory", "tactile", "visual", "sensory seeking", "sensory avoiding",
            "sensory processing", "sound sensitive", "light sensitive", "touch sensitive"
        ]

        for keyword in sensory_keywords:
            if keyword.lower() in text.lower():
                if keyword not in metadata["sensory_flags"]:
                    metadata["sensory_flags"].append(keyword)

        # Extrair notas comportamentais
        behavioral_keywords = [
            "hyperactive", "inattentive", "impulsive", "aggressive", "withdrawn",
            "self-stimulatory", "repetitive behaviors", "challenging behavior",
            "non-compliant", "refusing", "meltdown", "anxious", "agitated"
        ]

        for keyword in behavioral_keywords:
            if keyword.lower() in text.lower():
                if keyword not in metadata["behavioral_notes"]:
                    metadata["behavioral_notes"].append(keyword)

        # Extrair menções de diagnóstico
        diagnosis_keywords = [
            "ADHD", "Autism", "Anxiety", "Depression", "Learning Disorder",
            "Autism Spectrum", "Sensory Processing Disorder", "OCD",
            "Developmental Delay", "Intellectual Disability"
        ]

        for keyword in diagnosis_keywords:
            if keyword.lower() in text.lower():
                if keyword not in metadata["diagnosis_mentions"]:
                    metadata["diagnosis_mentions"].append(keyword)

        return metadata
    
    def chunk_text(self, text: str, chunk_id_prefix: str = "chunk") -> List[Dict[str, Any]]:
        """
        Dividir texto em chunks com metadados
        """
        # Limpar o texto primeiro
        cleaned_text = self.clean_clinical_text(text)

        # Extrair metadados para o documento inteiro
        doc_metadata = self.extract_metadata_from_text(cleaned_text)

        # Dividir o texto em chunks
        chunks = self.text_splitter.split_text(cleaned_text)

        # Criar objetos de chunk com metadados
        chunk_objects = []
        for i, chunk_text in enumerate(chunks):
            chunk_obj = {
                "chunk_id": f"{chunk_id_prefix}_{i+1}",
                "text": chunk_text,
                "chunk_order": i+1,
                "metadata": {**doc_metadata, "chunk_index": i+1, "total_chunks": len(chunks)}
            }
            chunk_objects.append(chunk_obj)

        return chunk_objects

    def process_clinical_document(self, file_path: str, doc_title: str = None) -> List[Dict[str, Any]]:
        """
        Processar um documento clínico (PDF, DOCX ou TXT) e retornar chunks com metadados
        """
        # Determinar tipo de arquivo e extrair texto
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.pdf':
            text = self.extract_text_from_pdf(file_path)
        elif file_ext == '.docx':
            text = self.extract_text_from_docx(file_path)
        elif file_ext == '.txt':
            text = self.extract_text_from_txt(file_path)
        else:
            raise ValueError(f"Tipo de arquivo não suportado: {file_ext}")

        text = self.remove_null_bytes(text)

        if not text.strip():
            logger.warning(f"Nenhum texto extraído de {file_path}")
            return []

        # Criar um título base se não for fornecido
        if doc_title is None:
            doc_title = os.path.basename(file_path)

        # Processar o texto em chunks
        chunks = self.chunk_text(text, chunk_id_prefix=doc_title.replace(" ", "_").replace(".", "_"))

        # Adicionar título do documento aos metadados de cada chunk
        for chunk in chunks:
            chunk["title"] = doc_title
            chunk["source_file"] = file_path
            chunk["file_type"] = file_ext

        return chunks

    def process_multiple_documents(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Processar múltiplos documentos clínicos
        """
        all_chunks = []
        for file_path in file_paths:
            logger.info(f"Processando documento: {file_path}")
            try:
                chunks = self.process_clinical_document(file_path)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.error(f"Erro ao processar documento {file_path}: {e}")
                continue

        return all_chunks
    
    def create_fine_tuning_dataset(self, raw_data: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Converter dados clínicos brutos para formato de ajuste fino (pares entrada/saída)

        :param raw_data: Lista de dicionários com chaves 'context', 'question', 'answer'
        :return: Lista de dicionários com 'input', 'output' para ajuste fino
        """
        ft_dataset = []
        for item in raw_data:
            # Construir entrada a partir do contexto e pergunta
            context = item.get('context', '')
            question = item.get('question', '')

            # Criar prompt de entrada
            input_text = f"Contexto: {context}\n\nPergunta: {question}\n\nPor favor, forneça uma resposta clínica baseada no contexto."

            # Obter a saída esperada
            output_text = item.get('answer', '')

            ft_dataset.append({
                "input": input_text,
                "output": output_text
            })

        return ft_dataset


# Função de exemplo de uso
def example_usage():
    """
    Exemplo de como usar o ClinicalDataProcessor
    """
    # Inicializar processador
    processor = ClinicalDataProcessor(chunk_size=500, chunk_overlap=50)

    # Exemplo de texto clínico
    clinical_text = """
    Relatório de Avaliação Inicial
    Data: 15/03/2023
    Nome do Paciente: Lucas Silva
    Idade: 8 anos
    Terapeuta: Dra. Maria Oliveira

    Lucas apresentou dificuldades em atenção e aprendizagem em sala de aula.
    Ele mostra hipersensibilidade a estímulos auditivos, particularmente sons altos
    que fazem com que ele cubra os ouvidos e fique agitado.

    Durante a avaliação, Lucas demonstrou desafios com compreensão de leitura
    e mostrou sinais de frustração quando confrontado com tarefas complexas.

    Recomendações:
    1. Fornecer fones de ouvido redutores de ruído durante atividades em sala de aula
    2. Implementar pausas sensoriais a cada 30 minutos
    3. Usar cronogramas visuais para apoiar a conclusão de tarefas
    """

    # Processar o texto
    chunks = processor.chunk_text(clinical_text, "initial_assessment_lucas")

    # Imprimir os resultados
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}:")
        print(f"  ID: {chunk['chunk_id']}")
        print(f"  Texto: {chunk['text'][:100]}...")
        print(f"  Metadados: {chunk['metadata']}")
        print()


if __name__ == "__main__":
    example_usage()