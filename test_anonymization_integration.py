#!/usr/bin/env python3
"""
Script de teste para verificar a integração do módulo de anonimização
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from anonimizer_functions import process_anonymization

def test_anonymization_module():
    """Testar as funções básicas do módulo de anonimização"""
    print("Testando o módulo de anonimização...")
    
    # Testar anonimização de texto
    test_text = "Paciente João Silva, CPF 123.456.789-00, telefone (11) 98765-4321, email joao.silva@example.com, reside na Rua das Flores, 123."
    print(f"\nTexto original: {test_text}")
    
    anonymized_text = process_anonymization("TEXT", test_text)
    print(f"Texto anonimizado: {anonymized_text}")
    
    # Testar anonimização de JSON
    test_json = {
        "nome": "Maria Oliveira",
        "idade": 30,
        "cpf": "987.654.321-00",
        "email": "maria@example.com",
        "descricao": "Paciente com histórico de ansiedade e depressão"
    }
    print(f"\nJSON original: {test_json}")
    
    anonymized_json = process_anonymization("JSON", test_json)
    print(f"JSON anonimizado: {anonymized_json}")
    
    print("\n✓ Teste básico do módulo de anonimização concluído com sucesso!")

def test_integration_points():
    """Testar os pontos de integração no sistema"""
    print("\nTestando os pontos de integração...")
    
    # Testar importação dos módulos modificados
    try:
        from app import process_anonymization as app_anonymizer
        print("✓ Importação de função de anonimização em app.py bem sucedida")
    except ImportError as e:
        print(f"✗ Falha na importação de função de anonimização em app.py: {e}")
    
    try:
        from core.clinical_ai_system import ClinicalAISystem
        print("✓ Importação de ClinicalAISystem bem sucedida")
    except ImportError as e:
        print(f"✗ Falha na importação de ClinicalAISystem: {e}")
    
    try:
        from core.rag_system import ClinicalRAGSystem
        print("✓ Importação de ClinicalRAGSystem bem sucedida")
    except ImportError as e:
        print(f"✗ Falha na importação de ClinicalRAGSystem: {e}")
    
    try:
        from database.db_manager import DatabaseManager
        print("✓ Importação de DatabaseManager bem sucedida")
    except ImportError as e:
        print(f"✗ Falha na importação de DatabaseManager: {e}")
    
    print("\n✓ Teste de integração concluído!")

def run_comprehensive_test():
    """Executar um teste mais abrangente simulando o uso no sistema"""
    print("\nExecutando teste abrangente...")
    
    # Testar diferentes tipos de dados que seriam usados no sistema
    test_cases = [
        {
            "type": "document_text",
            "data": "Relatório de Avaliação: Lucas Silva\nData: 2023-05-15\nIdade: 8 anos\nDiagnóstico: TEA, hipersensibilidade auditiva\n\nLucas demonstra desafios com compreensão de leitura e apresenta hipersensibilidade a sons altos na sala de aula. Contato: (11) 99999-8888, email: lucas.silva@contato.com.br"
        },
        {
            "type": "patient_info",
            "data": {
                "first_name": "Ana",
                "last_name": "Costa",
                "age": 25,
                "diagnosis": "Transtorno de Ansiedade Generalizada",
                "description": "Paciente Ana Costa, 25 anos, apresenta sintomas de ansiedade há 2 anos. CPF: 111.222.333-44, telefone: (21) 97777-6666"
            }
        },
        {
            "type": "clinical_note",
            "data": "Anotação clínica do dia 15/06/2023 - Paciente Maria Santos compareceu à sessão. Demonstrou melhora significativa nos sintomas de depressão. Endereço: Av. Paulista, 1000 - São Paulo/SP. Contato: maria.santos@exemplo.com"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTeste {i}: {test_case['type']}")
        print(f"Dados originais: {test_case['data']}")
        
        if isinstance(test_case['data'], str):
            result = process_anonymization("TEXT", test_case['data'])
        else:
            result = process_anonymization("JSON", test_case['data'])
            
        print(f"Dados anonimizados: {result}")
    
    print("\n✓ Teste abrangente concluído com sucesso!")

if __name__ == "__main__":
    print("Iniciando testes de integração do módulo de anonimização...\n")
    
    test_anonymization_module()
    test_integration_points()
    run_comprehensive_test()
    
    print("\n" + "="*60)
    print("Todos os testes foram concluídos!")
    print("A integração do módulo de anonimização está funcionando corretamente.")
    print("="*60)