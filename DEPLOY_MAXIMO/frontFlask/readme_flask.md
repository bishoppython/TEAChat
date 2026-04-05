# Frontend Flask - Sistema de IA para Psicopedagogia Clínica

Este é o frontend em Flask para o Sistema de IA para Psicopedagogia Clínica, substituindo a interface anterior em Streamlit.

## 🚀 Características

- **Interface Web Moderna**: Design responsivo com Bootstrap 5
- **Autenticação Segura**: Sistema de login/registro com JWT
- **Dashboard Intuitivo**: Visão geral das estatísticas e ações rápidas
- **Gestão de Documentos**: Adicionar documentos de texto ou fazer upload de arquivos (PDF, DOC, TXT, CSV)
- **Consultas Inteligentes**: Faça perguntas sobre pacientes e receba respostas baseadas em IA
- **Avaliações Clínicas**: Execute avaliações estruturadas com diferentes tipos
- **Perfis de Pacientes**: Visualize informações detalhadas de cada paciente

## 📋 Pré-requisitos

- Python 3.8 ou superior
- Backend da API rodando em `http://localhost:8000`

## 🔧 Instalação

1. **Clone o repositório** (se ainda não fez):
```bash
git clone <seu-repositorio>
cd <diretorio-do-projeto>
```

2. **Instale as dependências do Flask**:
```bash
pip install -r requirements_flask.txt
```

3. **Configure as variáveis de ambiente** (opcional):

Crie um arquivo `.env` na raiz do projeto:
```bash
FLASK_SECRET_KEY=sua-chave-secreta-aqui
FLASK_PORT=5000
FLASK_DEBUG=False
API_BASE_URL=http://localhost:8000
```

## 🏃 Executando

1. **Certifique-se de que o backend está rodando**:
```bash
# Em um terminal separado
python app.py
```

2. **Inicie o frontend Flask**:
```bash
python frontend_flask.py
```

3. **Acesse a aplicação**:
```
http://localhost:5000
```

## 📁 Estrutura de Arquivos

```
.
├── frontend_flask.py          # Aplicação principal Flask
├── requirements_flask.txt      # Dependências Python
├── templates/                  # Templates HTML
│   ├── base.html              # Template base
│   ├── login.html             # Página de login
│   ├── register.html          # Página de registro
│   ├── dashboard.html         # Dashboard principal
│   ├── query.html             # Página de consultas
│   ├── documents.html         # Adicionar documentos
│   ├── upload.html            # Upload de arquivos
│   ├── assessment.html        # Avaliações clínicas
│   ├── patient_profile.html   # Perfil do paciente
│   ├── 404.html               # Página de erro 404
│   └── 500.html               # Página de erro 500
└── README_FLASK.md            # Este arquivo
```

## 🎨 Funcionalidades Principais

### 1. Autenticação
- Login com usuário e senha
- Registro de novos usuários
- Sessões seguras com JWT
- Logout automático quando token expira

### 2. Dashboard
- Visão geral de estatísticas (documentos, pacientes, chunks, consultas)
- Ações rápidas para funcionalidades principais
- Informações sobre o sistema

### 3. Consultas
- Busca inteligente em documentos
- Suporte a consultas por paciente ou geral
- Exibição detalhada de resultados
- Métricas de performance

### 4. Gestão de Documentos
- **Adicionar Documento**: Cole texto diretamente
- **Upload de Arquivo**: Suporte para PDF, DOC, DOCX, TXT, CSV
- Preview de arquivos antes do upload
- Processamento automático em chunks

### 5. Avaliações Clínicas
- Múltiplos tipos de avaliação
- Análise baseada em evidências
- Métricas de confiança
- Sugestões contextuais

### 6. Perfis de Pacientes
- Visualização de informações do paciente
- Lista de sensibilidades
- Histórico clínico
- Ações rápidas (consultar, avaliar)

## 🔒 Segurança

- Todas as rotas principais são protegidas por autenticação
- Tokens JWT com expiração
- Validação de permissões (usuários só acessam seus próprios dados)
- Senhas não são armazenadas em texto plano
- CSRF protection habilitado

## 🎨 Design

- Interface responsiva (funciona em desktop, tablet e mobile)
- Design moderno com Bootstrap 5 e Bootstrap Icons
- Gradientes e animações suaves
- Feedback visual para ações do usuário
- Mensagens flash para comunicação clara

## 🐛 Solução de Problemas

### Backend não está acessível
```
Erro: API não disponível
```
**Solução**: Verifique se o backend está rodando em `http://localhost:8000`

### Erro de autenticação
```
Sua sessão expirou
```
**Solução**: Faça login novamente. Os tokens JWT expiram após 30 minutos.

### Erro ao fazer upload
```
Erro ao processar arquivo
```
**Solução**: 
- Verifique se o arquivo não excede 10MB
- Confirme que o formato é suportado (PDF, DOC, DOCX, TXT, CSV)
- Verifique se o backend tem permissões para processar arquivos

## 📝 Notas de Desenvolvimento

### Adicionando Novas Páginas

1. Crie um template em `templates/sua_pagina.html`
2. Adicione a rota em `frontend_flask.py`
3. Adicione link no sidebar em `base.html` (se necessário)

Exemplo:
```python
@app.route('/nova_pagina')
@login_required
def nova_pagina():
    return render_template('nova_pagina.html')
```

### Modificando Estilos

Os estilos CSS estão no `<style>` do arquivo `base.html`. Para customizar:

1. Abra `templates/base.html`
2. Modifique as variáveis CSS em `:root`
3. Ajuste classes conforme necessário

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `FLASK_SECRET_KEY` | (gerado) | Chave secreta para sessões |
| `FLASK_PORT` | 5000 | Porta do servidor Flask |
| `FLASK_DEBUG` | False | Modo debug (use True apenas em desenvolvimento) |
| `API_BASE_URL` | http://localhost:8000 | URL do backend |

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
3. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
4. Push para a branch (`git push origin feature/AmazingFeature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto é parte do Sistema de IA para Psicopedagogia Clínica.

## 📧 Suporte

Para questões e suporte, entre em contato através dos canais oficiais do projeto.

---

**Desenvolvido com ❤️ para profissionais de Psicopedagogia**
