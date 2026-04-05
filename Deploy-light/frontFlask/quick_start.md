# 🚀 Quick Start - Frontend Flask

Guia rápido para colocar o frontend Flask funcionando em 5 minutos.

## ⚡ Início Rápido

### 1. Pré-requisitos
```bash
# Verificar Python
python3 --version  # Precisa ser 3.8+

# Verificar pip
pip --version
```

### 2. Instalação
```bash
# Instalar dependências
pip install -r requirements_flask.txt
```

### 3. Configuração (Opcional)
```bash
# Copiar configurações de exemplo
cp .env.example .env

# Editar se necessário (opcional)
# nano .env
```

### 4. Verificar Backend
```bash
# O backend deve estar rodando em http://localhost:8000
curl http://localhost:8000/health
```

### 5. Executar
```bash
# Iniciar frontend
python3 frontend_flask.py

# Ou usar o script (Linux/Mac)
chmod +x run_flask.sh
./run_flask.sh
```

### 6. Acessar
```
http://localhost:5000
```

## 🎯 Primeiro Uso

1. **Criar Conta**
   - Acesse http://localhost:5000
   - Clique em "Criar Conta"
   - Preencha o formulário
   - Faça login automaticamente

2. **Adicionar Documento**
   - Vá para "Adicionar Documento"
   - Preencha ID do paciente: `1`
   - Adicione um título e texto
   - Clique em "Adicionar Documento"

3. **Fazer Consulta**
   - Vá para "Consultar"
   - ID do paciente: `1` (ou deixe "exemplo")
   - Digite uma pergunta
   - Veja a resposta da IA

## 📋 Estrutura Mínima Necessária

```
seu-projeto/
├── frontend_flask.py          # ✅ Obrigatório
├── requirements_flask.txt     # ✅ Obrigatório
├── .env                       # ⚠️  Recomendado
└── templates/                 # ✅ Obrigatório
    ├── base.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── query.html
    ├── documents.html
    ├── upload.html
    ├── assessment.html
    ├── patient_profile.html
    ├── 404.html
    └── 500.html
```

## ❌ Problemas Comuns

### Backend não está rodando
```bash
# Terminal 1: Iniciar backend
python app.py

# Terminal 2: Iniciar frontend
python3 frontend_flask.py
```

### Porta 5000 em uso
```bash
# Usar outra porta
export FLASK_PORT=5001
python3 frontend_flask.py
```

### Erro de template
```bash
# Verificar se a pasta templates existe
ls -la templates/

# Se não existir, criar
mkdir templates
# Copiar todos os arquivos .html para templates/
```

### Erro de importação Flask
```bash
# Instalar Flask
pip install Flask
```

## 📝 Configurações Rápidas

### Porta Customizada
```bash
# No terminal
export FLASK_PORT=8080
python3 frontend_flask.py
```

### Modo Debug (apenas desenvolvimento)
```bash
export FLASK_DEBUG=True
python3 frontend_flask.py
```

### URL do Backend Customizada
```bash
export API_BASE_URL=http://seu-backend:8000
python3 frontend_flask.py
```

## ✅ Checklist Rápido

- [ ] Python 3.8+ instalado
- [ ] Dependências instaladas (`pip install -r requirements_flask.txt`)
- [ ] Backend rodando em localhost:8000
- [ ] Pasta `templates/` existe com todos os arquivos HTML
- [ ] Frontend iniciado (`python3 frontend_flask.py`)
- [ ] Acessível em http://localhost:5000
- [ ] Consegue fazer login/registro

## 🆘 Precisa de Ajuda?

1. Verifique o [README_FLASK.md](README_FLASK.md) para documentação completa
2. Consulte o [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md) se estiver migrando do Streamlit
3. Verifique os logs no terminal onde o Flask está rodando

## 🎉 Pronto!

Se tudo funcionou, você deve ver:
```
 * Serving Flask app 'frontend_flask'
 * Debug mode: off
 * Running on http://0.0.0.0:5000
```

Acesse http://localhost:5000 e comece a usar o sistema!

---

**Tempo estimado de setup: ~5 minutos** ⏱️
