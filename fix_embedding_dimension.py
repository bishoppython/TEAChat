"""
Script para corrigir a dimensão do embedding na tabela documents
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def fix_embedding_dimension():
    """Altera a dimensão do vetor de embedding de 768 para 1536"""
    database_url = os.getenv("DATABASE_URL")
    
    try:
        print("🔄 Conectando ao banco de dados...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("🔧 Alterando dimensão do embedding de 768 para 1536...")
        
        # Dropar a coluna antiga e recriar com nova dimensão
        cursor.execute("ALTER TABLE documents DROP COLUMN IF EXISTS embedding;")
        cursor.execute("ALTER TABLE documents ADD COLUMN embedding vector(1536);")
        
        # Recriar o índice
        cursor.execute("DROP INDEX IF EXISTS idx_documents_embedding;")
        cursor.execute("""
            CREATE INDEX idx_documents_embedding 
            ON documents USING ivfflat (embedding vector_cosine_ops) 
            WITH (lists = 100);
        """)
        
        conn.commit()
        
        print("✅ Dimensão do embedding atualizada com sucesso!")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Correção de Dimensão de Embedding")
    print("=" * 60)
    print()
    
    success = fix_embedding_dimension()
    
    print()
    if success:
        print("✅ Correção aplicada com sucesso!")
    else:
        print("❌ Falha na correção.")
    print()
