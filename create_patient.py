#!/usr/bin/env python3
"""
Script para criar pacientes no sistema
"""

import sys
import os
sys.path.append(os.getcwd())

from database.db_manager import get_db_manager

def create_patient_example():
    """Criar um paciente de exemplo"""
    db_manager = get_db_manager()
    
    # Informações do paciente
    patient_unique_id = "exemplo"  # Este é o patient_id único (string)
    owner_id = 5  # ID do usuário proprietário (pode ser 5 ou 6 conforme vimos)
    first_name = "Exemplo"
    last_name = "de Paciente"
    age = 10
    diagnosis = "Paciente de exemplo para testes"
    
    try:
        patient_db_id = db_manager.create_patient(
            patient_id=patient_unique_id,
            owner_id=owner_id,
            first_name=first_name,
            last_name=last_name,
            age=age,
            diagnosis=diagnosis
        )
        
        print(f"Paciente criado com sucesso!")
        print(f"ID do banco de dados: {patient_db_id}")
        print(f"Patient ID único: {patient_unique_id}")
        print(f"Proprietário (usuário ID): {owner_id}")
        
        return patient_db_id
        
    except Exception as e:
        print(f"Erro ao criar paciente: {e}")
        return None

if __name__ == "__main__":
    create_patient_example()