"""
Script de demonstração do sistema de alertas inteligentes e análise de evolução clínica
"""
import sys
import os
from datetime import datetime, timedelta
import random

# Adicionar o diretório raiz ao path para importar os módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db_manager import DatabaseManager
from utils.embedding_generator import CachedEmbeddingGenerator
from core.openai_interface import ClinicalOpenAIInterface, OpenAIClient
from core.gemini_interface import ClinicalGeminiInterface
from analysis import ClinicalIntelligenceSystem


import time

def create_demo_patient_and_documents(db_manager):
    """Cria um paciente de demonstração com documentos clínicos simulados"""
    print("📝 Criando paciente de demonstração...")

    # Criar um nome de usuário único baseado no timestamp
    timestamp = str(int(time.time()))
    username = f"demo_therapist_{timestamp}"
    email = f"demo_{timestamp}@clinic.com"

    # Criar um usuário de demonstração
    user_id = db_manager.create_user(
        username=username,
        full_name="Dr. Demo Therapist",
        email=email,
        role="therapist"
    )
    
    # Criar um paciente de demonstração
    patient_id = db_manager.create_patient(
        patient_id="demo_patient",
        owner_id=user_id,
        first_name="Ana",
        last_name="Silva",
        age=8,
        diagnosis="Transtorno do Espectro Autista, Hipersensibilidade Sensorial",
        neurotype="TEA",
        level="moderate",
        description="Criança com TEA e hipersensibilidade auditiva e tátil."
    )
    
    print(f"✅ Paciente criado com ID: {patient_id}")
    
    # Criar documentos de sessão simulados para demonstrar evolução
    session_contents = [
        {
            "title": "Avaliação Inicial - Ana Silva",
            "content": """
Relatório de Avaliação Inicial: Ana Silva
Data: 2024-01-15
Idade: 8 anos
Diagnóstico: Transtorno do Espectro Autista, Hipersensibilidade Sensorial

Ana demonstra desafios com compreensão de leitura e apresenta
hipersensibilidade a sons altos na sala de aula. Quando exposta a
estímulos auditivos como sirenes de incêndio ou ruídos de construção,
ela cobre os ouvidos e fica visivelmente desconfortável.

Recomendação: Fornecer fones de ouvido com cancelamento de ruído
durante atividades de leitura e implementar uma programação de pausas
sensoriais a cada 30 minutos.
            """
        },
        {
            "title": "Sessão 2 - Ana Silva",
            "content": """
Sessão Terapêutica - 2ª Consulta: Ana Silva
Data: 2024-01-22
Idade: 8 anos

Hoje Ana participou da sessão com mais disposição. Ainda demonstra
sensibilidade auditiva, mas com menor intensidade de reação. Começou
a utilizar os fones de ouvido de forma mais autônoma quando sente
que o ambiente está muito barulhento.

Melhoras observadas: Menor ansiedade em ambientes ruidosos,
início de auto-regulação sensorial.
            """
        },
        {
            "title": "Sessão 3 - Ana Silva",
            "content": """
Sessão Terapêutica - 3ª Consulta: Ana Silva
Data: 2024-01-29
Idade: 8 anos

Ana mostrou resistência no início da sessão, mas após adaptação
ao ambiente, participou de atividades com melhor atenção. Ainda
apresenta hipersensibilidade, mas com menor frequência de crises.

Pontos de atenção: Continuar com fones de ouvido, introduzir
atividades de propriocepção para melhorar regulação.
            """
        },
        {
            "title": "Sessão 4 - Ana Silva",
            "content": """
Sessão Terapêutica - 4ª Consulta: Ana Silva
Data: 2024-02-05
Idade: 8 anos

Hoje foi observada estagnação no comportamento de Ana. Ela voltou
a demonstrar reações intensas a estímulos sonoros, semelhantes às
observadas na primeira sessão. Aparentemente, os ganhos anteriores
não foram consolidados e há necessidade de reavaliar a abordagem
terapêutica atual.

Recomendações: Considerar mudança na abordagem terapêutica,
possível necessidade de envolvimento multidisciplinar.
            """
        }
    ]
    
    # Adicionar os documentos ao sistema
    for i, session in enumerate(session_contents):
        doc_id = db_manager.add_document_chunk(
            owner_id=user_id,
            patient_id=patient_id,
            title=session["title"],
            text=session["content"].strip(),
            source_type="assessment",
            chunk_order=i
        )
        print(f"✅ Documento '{session['title']}' adicionado com ID: {doc_id}")
    
    return patient_id, user_id


def run_demo_analysis(intelligence_system, patient_id, user_id):
    """Executa a análise de demonstração"""
    print(f"\n🔍 Executando análise de evolução para paciente ID: {patient_id}")
    
    # Executar análise de evolução
    result = intelligence_system.analyze_patient_evolution_and_alert(
        patient_id=patient_id,
        owner_id=user_id,
        session_count=4
    )
    
    print(f"\n📊 Resultado da Análise de Evolução:")
    print(f"   Padrão de Evolução: {result['analysis_result']['evolution_pattern']}")
    print(f"   Score de Evolução: {result['analysis_result']['evolution_score']:.2f}")
    print(f"   Sessões Analisadas: {result['analysis_result']['sessions_analyzed']}")
    
    print(f"\n🔔 Alertas Gerados: {len(result['alerts_generated'])}")
    for i, alert in enumerate(result['alerts_generated']):
        print(f"   {i+1}. {alert['title']}")
        print(f"      Tipo: {alert['alert_type']}, Severidade: {alert['severity']}")
        print(f"      Descrição: {alert['description']}")
    
    print(f"\n💡 Recomendações Geradas: {len(result['recommendations'])}")
    for i, rec in enumerate(result['recommendations']):
        print(f"   {i+1}. {rec['treatment_name']}")
        print(f"      Relevância: {rec['relevance_score']:.2f}")
        print(f"      Confiança: {rec['confidence_level']}")
        print(f"      Notas: {rec['personalization_notes'][:100]}...")
    
    return result


def main():
    """Função principal de demonstração"""
    print("🎯 Demonstração do Sistema de Alertas Inteligentes e Análise de Evolução Clínica")
    print("="*70)
    
    try:
        # Inicializar componentes
        print("🔧 Inicializando componentes do sistema...")
        db_manager = DatabaseManager()
        embedder = CachedEmbeddingGenerator()
        
        # Tente inicializar interfaces de IA (elas podem não estar disponíveis)
        try:
            openai_client = OpenAIClient()
            openai_interface = ClinicalOpenAIInterface(openai_client)
        except:
            print("⚠️  Interface OpenAI não disponível (isso é normal em ambientes sem chave)")
            openai_interface = None
            
        try:
            gemini_interface = ClinicalGeminiInterface()
        except:
            print("⚠️  Interface Gemini não disponível (isso é normal em ambientes sem chave)")
            gemini_interface = None
        
        # Criar sistema de inteligência clínica
        intelligence_system = ClinicalIntelligenceSystem(
            db_manager=db_manager,
            embedding_generator=embedder,
            openai_interface=openai_interface,
            gemini_interface=gemini_interface
        )
        
        print("✅ Sistema de inteligência clínica inicializado")
        
        # Criar paciente de demonstração com documentos
        patient_id, user_id = create_demo_patient_and_documents(db_manager)
        
        # Executar análise de demonstração
        analysis_result = run_demo_analysis(intelligence_system, patient_id, user_id)
        
        # Obter alertas ativos para o paciente
        print(f"\n🔔 Obtendo alertas ativos para o paciente...")
        active_alerts = intelligence_system.get_patient_alerts(patient_id, user_id)
        print(f"   Alertas ativos: {len(active_alerts)}")
        
        for i, alert in enumerate(active_alerts):
            print(f"   {i+1}. {alert.title}")
            print(f"      Tipo: {alert.alert_type.value}, Severidade: {alert.severity.value}")
        
        # Executar avaliação clínica completa
        print(f"\n📋 Executando avaliação clínica completa...")
        complete_assessment = intelligence_system.run_complete_clinical_assessment(patient_id, user_id)
        
        print(f"   Avaliação completa gerada com sucesso!")
        print(f"   Sumário de evolução disponível: {bool(complete_assessment['evolution_summary']['has_data'])}")
        if complete_assessment['detailed_analysis']:
            print(f"   Análise detalhada disponível")
            print(f"   Recomendações geradas: {len(complete_assessment['detailed_analysis']['top_recommendations'])}")
        
        print(f"\n✨ Demonstração concluída com sucesso!")
        print(f"\n📈 Funcionalidades Demonstradas:")
        print(f"   • Análise de evolução clínica após 4 sessões")
        print(f"   • Detecção de estagnação/regressão terapêutica")
        print(f"   • Geração automática de alertas inteligentes")
        print(f"   • Recomendações terapêuticas baseadas em evidências")
        print(f"   • Avaliação clínica completa integrada")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro durante a demonstração: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print(f"\n🎉 Demonstração concluída com sucesso!")
        print(f"💡 O sistema de alertas inteligentes e análise de evolução está funcionando corretamente!")
    else:
        print(f"\n⚠️  Ocorreram erros durante a demonstração.")
    sys.exit(0 if success else 1)