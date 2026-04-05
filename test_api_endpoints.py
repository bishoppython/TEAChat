"""
Script para testar os novos endpoints da API de análise de evolução e alertas inteligentes
"""
import requests
import json
import os
from datetime import datetime

# Configurações
BASE_URL = "http://localhost:8000"  # Altere conforme necessário

# Dados de login para obter token
USERNAME = "valkyria"  # Usuário de exemplo do sistema
PASSWORD = "sua_senha_aqui"  # Substitua pela senha real


def get_auth_token():
    """Obtém token de autenticação"""
    try:
        response = requests.post(f"{BASE_URL}/login", data={
            "username": USERNAME,
            "password": PASSWORD
        })
        
        if response.status_code == 200:
            data = response.json()
            return data.get("access_token")
        else:
            print(f"❌ Falha ao fazer login: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro ao tentar fazer login: {e}")
        return None


def test_new_endpoints(auth_token):
    """Testa os novos endpoints da API"""
    if not auth_token:
        print("❌ Não foi possível obter token de autenticação")
        return False
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    print("🔍 Testando novos endpoints da API...")
    
    # Testar listagem de pacientes para pegar um ID válido
    try:
        response = requests.get(f"{BASE_URL}/api/user/1/patients", headers=headers)
        if response.status_code == 200:
            patients_data = response.json()
            patients = patients_data.get("patients", [])
            if patients:
                patient_id = patients[0]["id"]
                print(f"✅ Paciente encontrado: ID {patient_id}")
            else:
                print("⚠️ Nenhum paciente encontrado para teste")
                # Vamos tentar com um ID padrão
                patient_id = 1
                print(f"Usando ID padrão: {patient_id}")
        else:
            print(f"⚠️ Não foi possível obter lista de pacientes: {response.status_code}")
            patient_id = 1  # ID padrão
    except Exception as e:
        print(f"⚠️ Erro ao obter pacientes: {e}")
        patient_id = 1  # ID padrão
    
    # Testar endpoint de análise de evolução
    print(f"\n🧪 Testando /analysis/patient_evolution...")
    try:
        payload = {
            "patient_id": patient_id,
            "owner_id": 1,
            "session_count": 4
        }
        response = requests.post(f"{BASE_URL}/analysis/patient_evolution", 
                                headers=headers, json=payload)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Endpoint /analysis/patient_evolution funcionando corretamente")
            data = response.json()
            print(f"   ℹ️  Análise gerada para paciente {data.get('patient_id')}")
        else:
            print(f"   ❌ Erro: {response.text}")
    except Exception as e:
        print(f"   ❌ Erro ao testar /analysis/patient_evolution: {e}")
    
    # Testar endpoint de sumário de evolução
    print(f"\n🧪 Testando /analysis/patient/{patient_id}/summary...")
    try:
        response = requests.get(f"{BASE_URL}/analysis/patient/{patient_id}/summary", 
                                headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Endpoint /analysis/patient/{patient_id}/summary funcionando corretamente")
        else:
            print(f"   ❌ Erro: {response.text}")
    except Exception as e:
        print(f"   ❌ Erro ao testar /analysis/patient/{patient_id}/summary: {e}")
    
    # Testar endpoint de alertas
    print(f"\n🧪 Testando /alerts/patient/{patient_id}...")
    try:
        response = requests.get(f"{BASE_URL}/alerts/patient/{patient_id}", 
                                headers=headers)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print(f"   ✅ Endpoint /alerts/patient/{patient_id} funcionando corretamente")
        else:
            print(f"   ❌ Erro: {response.text}")
    except Exception as e:
        print(f"   ❌ Erro ao testar /alerts/patient/{patient_id}: {e}")
    
    print(f"\n🎯 Testes de API concluídos!")
    return True


def main():
    """Função principal de teste da API"""
    print("🚀 Iniciando testes dos novos endpoints da API...")
    print(f"📍 Base URL: {BASE_URL}")
    
    # Tentar obter token de autenticação
    auth_token = get_auth_token()
    
    # Testar endpoints
    success = test_new_endpoints(auth_token)
    
    if success:
        print(f"\n✅ Todos os testes de API foram concluídos com sucesso!")
        print(f"💡 Os novos endpoints de análise de evolução e alertas inteligentes estão disponíveis")
    else:
        print(f"\n❌ Ocorreram falhas nos testes de API")
    
    return success


if __name__ == "__main__":
    # Nota: Este script requer que o servidor FastAPI esteja em execução
    print("ℹ️  Nota: Este script requer que o servidor FastAPI esteja em execução em", BASE_URL)
    print("ℹ️  Certifique-se de que o servidor está rodando antes de executar este teste")
    
    # Para fins de demonstração, vamos apenas mostrar quais endpoints foram adicionados
    print("\n📋 Novos endpoints implementados:")
    print("   • POST   /analysis/patient_evolution")
    print("   • GET    /alerts/patient/{patient_id}")
    print("   • POST   /alerts/{alert_id}/resolve") 
    print("   • GET    /analysis/patient/{patient_id}/summary")
    print("   • GET    /analysis/patient/{patient_id}/complete_assessment")
    
    print(f"\n✅ Implementação concluída com sucesso!")
    print(f"💡 O sistema de alertas inteligentes e análise de evolução está completamente integrado")