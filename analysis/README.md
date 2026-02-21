# Sistema de Alertas Inteligentes e Análise de Evolução Clínica

Este módulo implementa um sistema avançado de inteligência clínica que analisa a evolução do paciente ao longo de múltiplas sessões e gera alertas inteligentes e recomendações terapêuticas baseadas em evidências.

## Funcionalidades

### 1. Análise de Evolução Clínica
- **Análise Automática**: Avalia automaticamente a evolução do paciente após cada 4 sessões
- **Detecção de Padrões**: Identifica padrões de evolução positiva, estagnação ou regressão
- **Métricas de Progresso**: Calcula métricas quantitativas de progresso terapêutico
- **Comparação Semântica**: Utiliza embeddings para comparar conteúdos clínicos entre sessões

### 2. Sistema de Alertas Inteligentes
- **Alertas de Estagnação**: Detecta quando o paciente não demonstra evolução após 4 sessões
- **Alertas de Regressão**: Identifica sinais de piora clínica
- **Níveis de Severidade**: Classifica alertas por importância (baixo, médio, alto, crítico)
- **Armazenamento Persistente**: Alertas são armazenados no banco de dados para acompanhamento

### 3. Recomendações Terapêuticas Baseadas em Evidências
- **Base de Conhecimento**: Contém tratamentos baseados em evidências científicas
- **Personalização**: Recomendações adaptadas ao perfil específico do paciente
- **Níveis de Evidência**: Considera o nível científico de cada tratamento
- **Relevância**: Ranqueia recomendações por relevância e adequação

## Componentes do Sistema

### 1. `ClinicalEvolutionAnalyzer`
- Analisa a evolução do paciente ao longo de múltiplas sessões
- Compara conteúdos clínicos usando embeddings semânticos
- Calcula scores de evolução e identifica padrões

### 2. `EvolutionMetricsCalculator`
- Calcula métricas quantitativas de progresso
- Analisa palavras-chave clínicas
- Detecta mudanças entre sessões consecutivas

### 3. `SmartAlertsSystem`
- Gera alertas baseados na análise de evolução
- Armazena alertas no banco de dados
- Fornece interface para gerenciamento de alertas

### 4. `TherapyRecommendationAgent`
- Consulta base de tratamentos baseados em evidências
- Personaliza recomendações para cada paciente
- Ranqueia opções por relevância e adequação

### 5. `ClinicalIntelligenceSystem`
- Integra todos os componentes em um sistema coeso
- Fornece interfaces para análise completa
- Coordena geração de alertas e recomendações

## Endpoints da API

### Análise de Evolução
```
POST /analysis/patient_evolution
```
Analisa a evolução do paciente e gera alertas e recomendações.

### Obter Alertas de um Paciente
```
GET /alerts/patient/{patient_id}
```
Retorna alertas inteligentes ativos para um paciente específico.

### Resolver Alerta
```
POST /alerts/{alert_id}/resolve
```
Marca um alerta como resolvido.

### Sumário de Evolução
```
GET /analysis/patient/{patient_id}/summary
```
Obtém um sumário da evolução do paciente.

### Avaliação Clínica Completa
```
GET /analysis/patient/{patient_id}/complete_assessment
```
Executa uma avaliação clínica completa com análise de evolução, alertas e recomendações.

## Bancos de Dados

### Tabelas Adicionadas
- `patient_evolution_analysis`: Armazena análises de evolução do paciente
- `smart_alerts`: Armazena alertas inteligentes gerados

Ambas as tabelas respeitam o modelo de multi-tenancy do sistema existente.

## Benefícios Clínicos

1. **Tomada de Decisão Informada**: Alertas baseados em dados objetivos
2. **Prevenção de Estagnação**: Identificação precoce de falta de progresso
3. **Personalização de Tratamento**: Recomendações adaptadas a cada paciente
4. **Baseada em Evidências**: Tratamentos com suporte científico
5. **Eficiência Clínica**: Automatização de análise de evolução

## Exemplo de Uso

O sistema detecta automaticamente quando um paciente não demonstra evolução significativa após 4 sessões consecutivas e:
1. Gera um alerta de estagnação terapêutica
2. Sugere tratamentos alternativos baseados em evidências
3. Fornece notas clínicas detalhadas sobre a análise
4. Armazena tudo no banco de dados para acompanhamento

## Segurança e Privacidade

- Total conformidade com o sistema de autenticação existente
- Isolamento de dados por usuário (multi-tenancy)
- Anonimização de dados sensíveis conforme o sistema existente
- Integração segura com as APIs de IA existentes