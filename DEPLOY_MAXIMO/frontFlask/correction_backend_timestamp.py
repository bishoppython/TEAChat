"""
Script de correção para o problema de conversão de timestamp no backend

Este script demonstra como resolver o erro:
ERRO: operador não existe: timestamp without time zone >= numeric

O problema ocorre quando um valor numérico (timestamp Unix) é comparado
diretamente com um campo timestamp no PostgreSQL sem conversão adequada.
"""

def fix_timestamp_comparison_in_sql_query():
    """
    Demonstração das diferentes formas de corrigir a comparação de timestamps
    """
    
    print("Soluções para o problema de comparação de timestamps:")
    print("="*50)
    
    # Solução 1: Converter timestamp Unix para formato timestamp no PostgreSQL
    print("\n1. Solução PostgreSQL - Usando TO_TIMESTAMP:")
    print("   ANTES (incorreto):")
    print("   WHERE user_id = ? AND created_at >= 1769691623")
    print("   DEPOIS (correto):")
    print("   WHERE user_id = ? AND created_at >= TO_TIMESTAMP(?)")
    
    # Solução 2: Converter no código Python antes de enviar para o banco
    print("\n2. Solução Python - Convertendo antes de montar a query:")
    print("   import datetime")
    print("   import psycopg2")
    print("")
    print("   # Timestamp Unix recebido")
    print("   unix_timestamp = 1769691623")
    print("")
    print("   # Converter para datetime")
    print("   dt = datetime.datetime.fromtimestamp(unix_timestamp)")
    print("   ")
    print("   # Usar na query")
    print("   query = \"SELECT * FROM tabela WHERE user_id = ? AND created_at >= ?\"")
    print("   cursor.execute(query, (user_id, dt))")
    
    # Solução 3: Usando SQLAlchemy com conversão adequada
    print("\n3. Solução SQLAlchemy - Usando conversão adequada:")
    print("   from sqlalchemy import func")
    print("   import datetime")
    print("")
    print("   # Converter timestamp Unix para datetime")
    print("   if isinstance(timestamp_param, (int, float)):")
    print("       timestamp_dt = datetime.datetime.fromtimestamp(timestamp_param)")
    print("   else:")
    print("       timestamp_dt = timestamp_param")
    print("")
    print("   # Usar na query")
    print("   results = session.query(YourModel)")
    print("             .filter(YourModel.user_id == user_id)")
    print("             .filter(YourModel.created_at >= timestamp_dt)")
    print("             .all()")
    
    # Solução 4: Função utilitária para conversão de timestamp
    print("\n4. Função utilitária para conversão de timestamp:")
    print("""
def convert_timestamp_for_query(timestamp_value):
    '''
    Converte diferentes formatos de timestamp para uso em queries SQL
    '''
    import datetime
    
    # Se for um número (timestamp Unix), converter para datetime
    if isinstance(timestamp_value, (int, float)):
        try:
            # Verificar se é um timestamp Unix (menor que 1e10 geralmente é Unix)
            if timestamp_value < 1e10:
                return datetime.datetime.fromtimestamp(timestamp_value)
            else:
                # Pode já ser um timestamp no formato correto
                return datetime.datetime.fromtimestamp(timestamp_value / 1000)  # milissegundos
        except (ValueError, OSError):
            # Se falhar, retornar o valor original
            return timestamp_value
    elif isinstance(timestamp_value, str):
        # Tentar converter string para datetime
        try:
            # Assumindo formato ISO ou similar
            return datetime.datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
        except ValueError:
            return timestamp_value
    else:
        # Se já for datetime ou outro tipo compatível, retornar como está
        return timestamp_value
    """)
    
    print("\n5. Exemplo de uso no contexto de uma API:")
    print("""
@app.route('/history/queries')
@login_required
def history_queries():
    # Parâmetros de filtragem
    patient_id = request.args.get('patient_id', type=int)
    min_date = request.args.get('min_date')  # Pode ser timestamp Unix ou string de data
    
    # Converter min_date se necessário
    if min_date:
        try:
            # Tentar converter como timestamp Unix primeiro
            min_date_converted = convert_timestamp_for_query(float(min_date))
        except ValueError:
            # Se não for número, manter como está
            min_date_converted = min_date
    else:
        min_date_converted = None
    
    # Montar query com o valor convertido
    query = session.query(QueryHistory).filter(QueryHistory.user_id == current_user_id)
    if min_date_converted:
        query = query.filter(QueryHistory.created_at >= min_date_converted)
    if patient_id:
        query = query.filter(QueryHistory.patient_id == patient_id)
    
    results = query.all()
    return jsonify({'queries': [q.to_dict() for q in results]})
    """)

def show_postgresql_specific_solution():
    """
    Mostra soluções específicas para PostgreSQL
    """
    print("\n\nSoluções Específicas para PostgreSQL:")
    print("="*40)
    
    print("\n1. Usando função TO_TIMESTAMP:")
    print("   SELECT * FROM tabela WHERE created_at >= TO_TIMESTAMP(1769691623);")
    
    print("\n2. Usando função TIMESTAMP WITH TIME ZONE:")
    print("   SELECT * FROM tabela WHERE created_at >= TIMESTAMP WITH TIME ZONE 'epoch' + 1769691623 * INTERVAL '1 second';")
    
    print("\n3. Se estiver usando psycopg2, converter no Python:")
    print("   import psycopg2.extras")
    print("   import datetime")
    print("   ")
    print("   unix_time = 1769691623")
    print("   dt = datetime.datetime.fromtimestamp(unix_time)")
    print("   query = \"SELECT * FROM tabela WHERE created_at >= %s\"")
    print("   cursor.execute(query, (dt,))")

def preventive_validation():
    """
    Demonstra validação preventiva para evitar o problema
    """
    print("\n\nValidação Preventiva:")
    print("="*20)
    
    print("""
# Função para validar e converter parâmetros de data
def validate_and_convert_date_params(params):
    '''
    Valida e converte parâmetros de data recebidos na requisição
    '''
    validated_params = params.copy()
    
    # Campos que podem conter timestamps
    date_fields = ['created_at', 'updated_at', 'min_date', 'max_date', 'start_date', 'end_date']
    
    for field in date_fields:
        if field in validated_params and validated_params[field] is not None:
            value = validated_params[field]
            
            # Se for um número, verificar se parece um timestamp Unix
            if isinstance(value, (int, float)):
                # Timestamps Unix geralmente têm 10 dígitos (segundos) ou 13 (milissegundos)
                str_val = str(int(value))
                
                if len(str_val) == 10:  # Timestamp Unix em segundos
                    validated_params[field] = datetime.datetime.fromtimestamp(value)
                elif len(str_val) == 13:  # Timestamp Unix em milissegundos
                    validated_params[field] = datetime.datetime.fromtimestamp(value / 1000.0)
                else:
                    # Não parece um timestamp, manter como está
                    pass
    
    return validated_params
    """)

if __name__ == "__main__":
    print("Script de Correção - Problema de Timestamp no Backend")
    print("="*60)
    
    fix_timestamp_comparison_in_sql_query()
    show_postgresql_specific_solution()
    preventive_validation()
    
    print("\n\nInstruções de Implementação:")
    print("="*25)
    print("1. Localize no código do backend onde são feitas consultas SQL")
    print("   com filtros em campos do tipo timestamp (como created_at)")
    print("")
    print("2. Identifique onde valores numéricos são passados diretamente")
    print("   para comparações com campos timestamp")
    print("")
    print("3. Implemente a conversão adequada desses valores antes de")
    print("   usá-los na consulta SQL, usando uma das soluções acima")
    print("")
    print("4. Teste as funcionalidades afetadas para garantir que o")
    print("   problema foi resolvido")