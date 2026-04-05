"""
Script para garantir que as tabelas de análise de evolução e alertas inteligentes sejam criadas
"""
import sys
import os

# Adicionar o diretório raiz ao path para importar os módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager


def ensure_tables_exist():
    """Garante que todas as tabelas necessárias existam no banco de dados"""
    print("🔍 Verificando e criando tabelas necessárias...")
    
    try:
        # Inicializar o gerenciador de banco de dados
        db_manager = DatabaseManager()
        
        # Forçar a criação das tabelas de histórico (incluindo as novas)
        db_manager.ensure_history_tables_exist()
        
        print("✅ Tabelas de histórico garantidas como existentes")
        
        # Verificar se as tabelas específicas de análise de evolução existem
        with db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                # Verificar tabela patient_evolution_analysis
                cursor.execute("""
                    SELECT EXISTS (
                       SELECT FROM information_schema.tables
                       WHERE table_schema = 'public'
                       AND table_name = 'patient_evolution_analysis'
                   );
                """)
                evolution_table_exists = cursor.fetchone()[0]
                
                # Verificar tabela smart_alerts
                cursor.execute("""
                    SELECT EXISTS (
                       SELECT FROM information_schema.tables
                       WHERE table_schema = 'public'
                       AND table_name = 'smart_alerts'
                   );
                """)
                alerts_table_exists = cursor.fetchone()[0]
                
                print(f"✅ Tabela 'patient_evolution_analysis' existe: {evolution_table_exists}")
                print(f"✅ Tabela 'smart_alerts' existe: {alerts_table_exists}")
                
                if evolution_table_exists and alerts_table_exists:
                    print("🎉 Todas as tabelas necessárias agora existem!")
                    return True
                else:
                    print("❌ Algumas tabelas ainda estão faltando")
                    return False
                    
    except Exception as e:
        print(f"❌ Erro ao garantir existência das tabelas: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Função principal"""
    print("🚀 Iniciando processo de criação de tabelas...")
    
    success = ensure_tables_exist()
    
    if success:
        print("\n✅ Processo concluído com sucesso!")
        print("💡 As tabelas de análise de evolução e alertas inteligentes agora estão disponíveis")
    else:
        print("\n❌ Ocorreu um erro durante o processo")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)