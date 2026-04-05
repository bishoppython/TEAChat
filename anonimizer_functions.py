import re
import json
import nltk

# Garante que os dados NLTK estão disponíveis
def ensure_nltk_data():
    required_data = {
        'punkt': 'tokenizers/punkt',
        'punkt_tab': 'tokenizers/punkt_tab',
        'averaged_perceptron_tagger': 'taggers/averaged_perceptron_tagger',
        'mac_morpho': 'taggers/mac_morpho'
    }
    
    for name, path in required_data.items():
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(name, quiet=True)

ensure_nltk_data()

from nltk.tokenize import word_tokenize
from nltk import pos_tag

# Padrões regex para detectar dados sensíveis
REGEX_PATTERNS = {
    "CPF": r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b",
    "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "PHONE": r"\(?\d{2}\)?\s?9?\d{4,5}-?\d{4}\b",
    "ADDRESS": r"(Rua|Avenida|Praça|Travessa|Estrada)\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇa-z0-9 ,.-]+",
    "DATE": r"\b\d{1,2}/\d{1,2}/\d{4}\b",
    "AGE": r"\b(\d{1,3})\s+anos\b",
    "GENDER": r"\b(masculino|feminino|homem|mulher|sexo masculino|sexo feminino)\b",
}

# Converte idade numérica para faixa etária
def map_age_to_range(age):
    try:
        age = int(age)
    except ValueError:
        return "<AGE_RANGE>"
    
    if age < 18:
        return "<0-17>"
    elif age < 30:
        return "<18-29>"
    elif age < 40:
        return "<30-39>"
    elif age < 50:
        return "<40-49>"
    elif age < 60:
        return "<50-59>"
    elif age < 70:
        return "<60-69>"
    else:
        return "<70+>"

# Palavras comuns que não devem ser anonimizadas
COMMON_WORDS = {
    "Rua", "Avenida", "Praça", "Travessa", "Estrada", "Alameda", "Rodovia",
    "Paciente", "Endereço", "CPF", "Email", "Telefone", "Tel", "Nome", "Idade",
    "Gênero", "Data", "Contato", "Nascimento",
    "Relatório", "Ficha", "Prontuário", "Médico", "Consulta", "Dr", "Dra", "Atendimento",
    "Diagnóstico", "Queixa", "Exames", "Conduta", "Anamnese", "Prescrição",
    "Hipertensão", "Diabetes", "Tratamento", "Medicamento", "Prescritos", "Prescrito",
    "Principal", "Solicitados", "Portador", "Reside",
    "Compareceu", "Atendido", "Relata", "Solicita", "Exame", "Hemograma",
    "Ultrassonografia", "Arterial", "Abdominal", "Recorrentes", "Dores",
    "Fadiga", "Constante", "Dificuldade", "Dormir", "Laboratoriais", "Retorno",
    "Dias", "Semanas", "Uso", "Contínuo", "Dados", "Eletrônico"
}

# Detecta se um token é provavelmente um nome próprio
def is_likely_proper_name(token, prev_token=None, next_token=None):
    if token in COMMON_WORDS:
        return False
    
    if len(token) <= 2 or len(token) > 20:
        return False
    
    if not token[0].isupper():
        return False
    
    if any(char.isdigit() for char in token):
        return False
    
    name_indicators = {"Nome", "Paciente", "Dr", "Dra", "Professor", "Sr", "Sra"}
    if prev_token in name_indicators:
        return True
    
    if next_token and next_token.istitle() and next_token not in COMMON_WORDS:
        return True
    
    if len(token) == 2 and token.isupper():
        return False
    
    return token.istitle()

# Anonimiza texto livre
def anonymize_text_only(text, anonymization_level="total"):
    # Aplica substituições regex
    for label, pattern in REGEX_PATTERNS.items():
        if label == "AGE":
            matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
            for match in matches:
                age_num = match.group(1)
                faixa = map_age_to_range(age_num)
                text = text.replace(match.group(0), faixa, 1)
        elif label == "GENDER":
            text = re.sub(pattern, "<GENDER>", text, flags=re.IGNORECASE)
        else:
            text = re.sub(pattern, f"<{label}>", text, flags=re.IGNORECASE)

    # Tokeniza e detecta nomes próprios
    tokens = word_tokenize(text, language="portuguese")
    anon_tokens = []
    i = 0

    while i < len(tokens):
        token = tokens[i]

        if is_likely_proper_name(
            token,
            tokens[i - 1] if i > 0 else None,
            tokens[i + 1] if i < len(tokens) - 1 else None
        ):
            full_name_segment = [token]
            j = i + 1
 
            while j < len(tokens):
                if is_likely_proper_name(
                    tokens[j],
                    tokens[j - 1] if j > 0 else None,
                    tokens[j + 1] if j < len(tokens) - 1 else None
                ):
                    full_name_segment.append(tokens[j])
                    j += 1
                elif tokens[j].lower() in ("de", "da", "do", "das", "dos", "e") and j + 1 < len(tokens) and is_likely_proper_name(
                    tokens[j + 1],
                    tokens[j],
                    tokens[j + 2] if j + 2 < len(tokens) else None
                ):
                    full_name_segment.append(tokens[j])
                    full_name_segment.append(tokens[j + 1])
                    j += 2
                else:
                    break

            proper_count = 0
            for t in full_name_segment:
                if t.lower() in ("de", "da", "do", "das", "dos", "e"):
                    anon_tokens.append(t)
                else:
                    proper_count += 1
                    if proper_count == 1:
                        anon_tokens.append("<NAME>")
                    elif proper_count == 2:
                        anon_tokens.append("<LASTNAME>")
                    else:
                        anon_tokens.append(t)

            i = j
        else:
            anon_tokens.append(token)
            i += 1

    return " ".join(anon_tokens)

# Processa anonimização baseado no tipo de dado
def process_anonymization(data_type, content, fields_to_keep=None):
    if data_type == "TEXT":
        return anonymize_text_only(content)

    if data_type == "JSON":
        if not isinstance(content, dict):
            raise ValueError("JSON content must be an object")

        output = {}

        for key, value in content.items():
            if fields_to_keep is not None and key in fields_to_keep:
                output[key] = value
                continue

            if isinstance(value, str):
                output[key] = anonymize_text_only(value)
            elif isinstance(value, (int, float)) and key.lower() in ("idade", "age", "anos", "years"):
                output[key] = map_age_to_range(value)
            else:
                output[key] = value

        return output

    raise ValueError(f"Unsupported type '{data_type}', expected TEXT or JSON")


# ==================== DADOS SINTÉTICOS PARA TESTE ====================

# Dados JSON para teste
dados_pacientes_json = [
    {
        "nome": "João Silva Santos",
        "idade": 45,
        "cpf": "123.456.789-00",
        "genero": "Masculino",
        "telefone": "(11) 98765-4321",
        "email": "joao.silva@email.com",
        "endereco": "Rua das Flores, 123, São Paulo, SP"
    },
    {
        "nome": "Maria Oliveira Costa",
        "idade": 32,
        "cpf": "987.654.321-00",
        "genero": "Feminino",
        "telefone": "(21) 99876-5432",
        "email": "maria.oliveira@email.com",
        "endereco": "Avenida Brasil, 456, Rio de Janeiro, RJ"
    },
    {
        "nome": "Carlos Eduardo Mendes",
        "idade": 58,
        "cpf": "456.789.123-00",
        "genero": "Masculino",
        "telefone": "(85) 97654-3210",
        "email": "carlos.mendes@email.com",
        "endereco": "Praça Central, 789, Fortaleza, CE"
    }
]

# Textos livres para teste
textos_pacientes = [
    "Prontuário Médico - Paciente: João Silva Santos. O paciente João Silva Santos, 45 anos, sexo masculino, portador do CPF 123.456.789-00, compareceu à consulta em 10/11/2025. Reside na Rua das Flores, 123, São Paulo, SP. Telefone para contato: (11) 98765-4321. Email: joao.silva@email.com. Diagnóstico: Hipertensão arterial.",
    "Ficha de Atendimento - Nome: Maria Oliveira Costa | Idade: 32 anos | Gênero: Feminino. CPF: 987.654.321-00 | Tel: (21) 99876-5432. Endereço: Avenida Brasil, 456, Rio de Janeiro, RJ. Contato eletrônico: maria.oliveira@email.com. Queixa principal: dores abdominais recorrentes há 2 semanas.",
    "Relatório de Consulta - Dr. Fernando Alves. Paciente Carlos Eduardo Mendes atendido em 10/11/2025. Dados do paciente: 58 anos, masculino, CPF 456.789.123-00. Contato: (85) 97654-3210 / carlos.mendes@email.com. Endereço: Praça Central, 789, Fortaleza, CE."
]

# ==================== EXEMPLO DE USO ====================

if __name__ == "__main__":
    print("=" * 80)
    print("TESTE: ANONIMIZAÇÃO DE DADOS JSON")
    print("=" * 80)
    
    for i, paciente in enumerate(dados_pacientes_json, 1):
        print(f"\n--- Paciente {i} (Original) ---")
        print(json.dumps(paciente, indent=2, ensure_ascii=False))
        
        resultado = process_anonymization("JSON", paciente)
        
        print(f"\n--- Paciente {i} (Anonimizado) ---")
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        print("-" * 80)
    
    print("\n" + "=" * 80)
    print("TESTE: ANONIMIZAÇÃO DE TEXTO LIVRE")
    print("=" * 80)
    
    for i, texto in enumerate(textos_pacientes, 1):
        print(f"\n--- Texto {i} (Original) ---")
        print(texto)
        
        resultado = process_anonymization("TEXT", texto)
        
        print(f"\n--- Texto {i} (Anonimizado) ---")
        print(resultado)
        print("-" * 80)
    
    print("\n" + "=" * 80)
    print("TESTE: JSON COM CAMPOS PARA MANTER")
    print("=" * 80)
    
    paciente_teste = dados_pacientes_json[0].copy()
    print(f"\n--- Original (mantendo 'email' e 'telefone') ---")
    print(json.dumps(paciente_teste, indent=2, ensure_ascii=False))
    
    resultado = process_anonymization("JSON", paciente_teste, fields_to_keep=["email", "telefone"])
    
    print(f"\n--- Anonimizado (mantendo 'email' e 'telefone') ---")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    print("=" * 80)
