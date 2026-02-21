"""
Módulo para formatação de respostas do sistema de IA clínica
Responsável por limpar e melhorar a apresentação das respostas geradas
"""
import re
from typing import Dict, Any, List


def convert_markdown_to_html(text: str) -> str:
    """
    Converte markdown básico em HTML para exibição no frontend

    Args:
        text: Texto em formato markdown

    Returns:
        Texto convertido em HTML
    """
    if not text:
        return text

    # Converter quebras de linha para facilitar o processamento
    lines = text.split('<br>')
    result_lines = []

    for line in lines:
        # Converter cabeçalhos ## para <h3>
        line = re.sub(r'##\s+(.+)', r'<h3 class="markdown-subheader">\1</h3>', line)

        # Converter cabeçalhos # para <h4>
        line = re.sub(r'#\s+(.+)', r'<h4 class="markdown-header">\1</h4>', line)

        result_lines.append(line)

    text = '<br>'.join(result_lines)

    # Converter traços no início da linha (após <br>) em listas HTML
    # Isso evita converter traços no meio de frases
    text = re.sub(r'(<br>\s*|\A\s*)-\s+([^<]+?)(<br>)', r'\1<ul class="markdown-list"><li class="markdown-list-item">\2</li></ul>\3', text)

    # Converter asteriscos em negrito
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

    return text


def clean_response_format(response: str) -> str:
    """
    Limpa e formata a resposta removendo referências a documentos e melhorando a apresentação

    Args:
        response: Resposta bruta do sistema

    Returns:
        Resposta limpa e formatada
    """
    if not response:
        return response

    # Remover referências a chunks (ex: "(Chunk 11)", "(Relatório de Avaliação Final - Lucas - Chunk 3)")
    cleaned_response = re.sub(r'\s*\([^)]*Chunk\s*\d+\)', '', response, flags=re.IGNORECASE)

    # Remover referências mais genéricas a chunks e documentos
    cleaned_response = re.sub(r'\s*\([^)]*[Cc]hunk[^)]*\)', '', cleaned_response)
    cleaned_response = re.sub(r'\s*\([^)]*[Pp]arte[^)]*\)', '', cleaned_response)
    cleaned_response = re.sub(r'\s*\([^)]*[Ss]ection[^)]*\)', '', cleaned_response)

    # Remover quaisquer parênteses com números ou referências a documentos
    cleaned_response = re.sub(r'\s*\([^)]*\d+[^)]*\)', '', cleaned_response)

    # Remover menções diretas a "Chunk" seguido de número no meio do texto
    # Ex: "no Chunk 4 do Relatório", "do Chunk 2 do mesmo relatório"
    # Preservar a capitalização original
    cleaned_response = re.sub(r'([Nn]o)\s+Chunk\s+\d+', r'\1 documento', cleaned_response)
    cleaned_response = re.sub(r'([Dd]o)\s+Chunk\s+\d+', r'\1 documento', cleaned_response)
    cleaned_response = re.sub(r'([Cc]hunk)\s+\d+', r'documento', cleaned_response)
    # Também capturar variações como "No Chunk" no início da frase
    cleaned_response = re.sub(r'(No)\s+Chunk\s+\d+', r'No documento', cleaned_response)
    cleaned_response = re.sub(r'(Do)\s+Chunk\s+\d+', r'Do documento', cleaned_response)

    # Padronizar o formato de evidências para melhor apresentação
    # Converter listas de evidências em uma apresentação mais limpa
    cleaned_response = re.sub(
        r'\*\s*"([^"]+)"\s*\([^)]+\)',
        r'• \1',
        cleaned_response
    )

    # Melhorar a formatação de seções - manter apenas títulos em negrito
    cleaned_response = cleaned_response.replace("**1. Análise:**", "\n## 🔍 Análise\n")
    cleaned_response = cleaned_response.replace("**2. Evidências:**", "\n## 📚 Evidências\n")
    cleaned_response = cleaned_response.replace("**3. Recomendações:**", "\n## 💡 Recomendações\n")

    # Melhorar formatação de outras seções comuns
    cleaned_response = cleaned_response.replace("**Análise:**", "\n## 🔍 Análise\n")
    cleaned_response = cleaned_response.replace("**Evidências:**", "\n## 📚 Evidências\n")
    cleaned_response = cleaned_response.replace("**Recomendações:**", "\n## 💡 Recomendações\n")
    cleaned_response = cleaned_response.replace("**Sugestões:**", "\n## 💡 Sugestões\n")
    cleaned_response = cleaned_response.replace("**PACIENTE:**", "\n## 👤 Paciente\n")
    cleaned_response = cleaned_response.replace("**CONTEXTO DOS DOCUMENTOS:**", "\n## 📄 Contexto dos Documentos\n")
    cleaned_response = cleaned_response.replace("**PERGUNTA DO USUÁRIO:**", "\n## ❓ Pergunta do Usuário\n")
    cleaned_response = cleaned_response.replace("**SUA RESPOSTA:**", "\n## 📝 Resposta\n")

    # Remover ** de outros lugares para evitar negrito excessivo
    cleaned_response = re.sub(r'\*\*([^*]+)\*\*', r'\1', cleaned_response)

    # Melhorar formatação de listas
    cleaned_response = re.sub(r'\*\s*(.+)', r'• \1', cleaned_response)

    # Corrigir espaçamento duplo
    cleaned_response = re.sub(r'\n\s*\n\s*\n', '\n\n', cleaned_response)

    # Remover espaços extras no início e fim
    cleaned_response = cleaned_response.strip()

    return cleaned_response


def format_clinical_response(response: str) -> str:
    """
    Formata resposta clínica com melhor estrutura e apresentação
    
    Args:
        response: Resposta bruta do sistema
        
    Returns:
        Resposta formatada para apresentação clínica
    """
    # Primeiro limpar a resposta
    cleaned = clean_response_format(response)
    
    # Adicionar melhor estruturação se necessário
    if "## 🔍 Análise" not in cleaned and "**Análise**" not in cleaned:
        # Se não tiver estrutura definida, tentar identificar e estruturar
        sections = identify_and_structure_sections(cleaned)
        return sections
    else:
        return cleaned


def identify_and_structure_sections(text: str) -> str:
    """
    Identifica seções em uma resposta e as estrutura adequadamente
    
    Args:
        text: Texto a ser estruturado
        
    Returns:
        Texto com seções estruturadas
    """
    # Procurar por padrões comuns de início de seções
    patterns = [
        (r'(?:análise|análise:|análise\s+de)', '## 🔍 Análise\n'),
        (r'(?:evidências|evidências:|evidências\s+de)', '## 📚 Evidências\n'),
        (r'(?:recomendações|recomendações:|recomendações\s+para)', '## 💡 Recomendações\n'),
        (r'(?:sugestões|sugestões:|sugestões\s+para)', '## 💡 Sugestões\n'),
        (r'(?:conclusão|conclusão:)', '## ✅ Conclusão\n'),
        (r'(?:observações|observações:)', '## 📋 Observações\n'),
    ]
    
    result = text
    
    for pattern, replacement in patterns:
        # Substituir padrões encontrados com formatação adequada
        result = re.sub(rf'({pattern})', replacement, result, flags=re.IGNORECASE)
    
    return result


def format_assessment_response(response: str) -> str:
    """
    Formata resposta de avaliação clínica com estrutura específica
    
    Args:
        response: Resposta bruta de avaliação
        
    Returns:
        Resposta formatada para avaliação clínica
    """
    # Aplicar formatação geral
    formatted = format_clinical_response(response)
    
    # Adicionar formatação específica para avaliações
    formatted = formatted.replace("1. Análise", "## 🔍 Análise Clínica")
    formatted = formatted.replace("2. Evidências", "## 📚 Evidências Clínicas")
    formatted = formatted.replace("3. Recomendações", "## 💡 Recomendações Clínicas")
    
    return formatted


def format_query_response(response: str) -> str:
    """
    Formata resposta de consulta com estrutura específica
    
    Args:
        response: Resposta bruta de consulta
        
    Returns:
        Resposta formatada para consulta
    """
    # Aplicar formatação geral
    formatted = format_clinical_response(response)
    
    # Adicionar formatação específica para consultas
    formatted = formatted.replace("1. Análise", "## 🔍 Análise da Consulta")
    formatted = formatted.replace("2. Evidências", "## 📚 Evidências Encontradas")
    formatted = formatted.replace("3. Recomendações", "## 💡 Recomendações")
    
    return formatted


def format_markdown_for_display(response: str, response_type: str = "general") -> str:
    """
    Formata markdown para exibição no frontend

    Args:
        response: Resposta a ser formatada
        response_type: Tipo da resposta ('general', 'assessment', 'query', 'document', 'patient_info')

    Returns:
        Resposta formatada para exibição
    """
    if response_type == "assessment":
        return format_assessment_response(response)
    elif response_type == "query":
        return format_query_response(response)
    elif response_type == "patient_info":
        return format_patient_info_response(response)
    else:
        return format_clinical_response(response)


def format_patient_info_response(response: str) -> str:
    """
    Formata informações do paciente com estrutura específica para perfis

    Args:
        response: Texto de informações do paciente

    Returns:
        Texto formatado com estrutura adequada para perfis de pacientes
    """
    if not response:
        return response

    # Primeiro, adicionar título para o início do histórico clínico se existir
    formatted = response
    if 'HISTÓRICO CLÍNICO' in formatted:
        formatted = formatted.replace('HISTÓRICO CLÍNICO', '## 📋 HISTÓRICO CLÍNICO:\n\n', 1)

    # Identificar e estruturar seções comuns em perfis de pacientes
    sections = [
        ('IDENTIFICAÇÃO', '## 👤 IDENTIFICAÇÃO'),
        ('DESENVOLVIMENTO', '## 📈 DESENVOLVIMENTO'),
        ('DIAGNÓSTICOS', '## 🏥 DIAGNÓSTICOS'),
        ('CONTEXTO FAMILIAR', '## 👨‍👩‍👧‍👦 CONTEXTO FAMILIAR'),
        ('HISTÓRICO ESCOLAR', '## 🎓 HISTÓRICO ESCOLAR'),
        ('E CARACTERÍSTICAS', '## 🌟 E CARACTERÍSTICAS'),
        ('PONTOS FORTES', '## 💪 PONTOS FORTES'),
        ('DESAFIOS', '## ⚠️ DESAFIOS'),
        ('INTERVENÇÕES ATUAIS', '## 🛠️ INTERVENÇÕES ATUAIS'),
        ('MEDICAÇÃO', '## 💊 MEDICAÇÃO'),
        ('OBJETIVOS TERAPÊUTICOS', '## 🎯 OBJETIVOS TERAPÊUTICOS'),
        ('EVOLUÇÃO', '## 📊 EVOLUÇÃO'),
        ('OBSERVAÇÕES', '## 📝 OBSERVAÇÕES'),
    ]

    for old_section, new_section in sections:
        # Substituir seções com e sem dois pontos
        formatted = formatted.replace(old_section + ':', new_section + ':\n\n')
        formatted = formatted.replace(old_section + ' :', new_section + ':\n\n')

    # Converter o markdown resultante para HTML
    html_result = convert_markdown_to_html(formatted)

    # Remover espaços extras no início e fim
    return html_result.strip()