# Guia de Migração: Streamlit → Flask

Este guia ajuda na transição do frontend Streamlit para Flask.

## 📊 Comparação Rápida

| Aspecto | Streamlit | Flask |
|---------|-----------|-------|
| **Tipo** | Framework de app de dados | Framework web completo |
| **Complexidade** | Simples | Média |
| **Controle** | Limitado | Total |
| **Performance** | Boa para prototipagem | Melhor para produção |
| **Customização** | Limitada | Completa |
| **Escalabilidade** | Limitada | Alta |

## 🔄 Mudanças Principais

### 1. Estrutura de Arquivos

**Antes (Streamlit):**
```
frontend.py  (tudo em um arquivo)
```

**Depois (Flask):**
```
frontend_flask.py      (lógica da aplicação)
templates/            (arquivos HTML)
  ├── base.html
  ├── login.html
  ├── dashboard.html
  └── ...
```

### 2. Gerenciamento de Estado

**Streamlit:**
```python
st.session_state.token = "abc123"
if 'user_id' in st.session_state:
    user_id = st.session_state.user_id
```

**Flask:**
```python
session['token'] = "abc123"
if 'user_id' in session:
    user_id = session['user_id']
```

### 3. Formulários

**Streamlit:**
```python
username = st.text_input("Nome de usuário")
password = st.text_input("Senha", type="password")
if st.button("Login"):
    # processar
```

**Flask (no template HTML):**
```html
<form method="POST">
    <input type="text" name="username">
    <input type="password" name="password">
    <button type="submit">Login</button>
</form>
```

**Flask (no Python):**
```python
@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    # processar
```

### 4. Exibição de Mensagens

**Streamlit:**
```python
st.success("Login realizado!")
st.error("Erro ao processar")
st.warning("Atenção")
```

**Flask:**
```python
flash('Login realizado!', 'success')
flash('Erro ao processar', 'danger')
flash('Atenção', 'warning')
```

### 5. Layout

**Streamlit:**
```python
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Documentos", 10)
```

**Flask (HTML com Bootstrap):**
```html
<div class="row">
    <div class="col-md-4">
        <div class="card">
            <h3>10</h3>
            <p>Documentos</p>
        </div>
    </div>
</div>
```

## 🚀 Passos de Migração

### Passo 1: Instalar Dependências

```bash
# Criar arquivo requirements_flask.txt
pip install -r requirements_flask.txt
```

### Passo 2: Criar Estrutura de Pastas

```bash
mkdir templates
```

### Passo 3: Copiar Arquivos

1. Copie `frontend_flask.py` para o diretório do projeto
2. Copie todos os arquivos HTML para a pasta `templates/`
3. Copie `requirements_flask.txt`

### Passo 4: Configurar Variáveis de Ambiente

```bash
# Copie .env.example para .env
cp .env.example .env

# Edite .env com suas configurações
nano .env  # ou use seu editor preferido
```

### Passo 5: Executar

```bash
# Opção 1: Direto com Python
python3 frontend_flask.py

# Opção 2: Com script de inicialização (Linux/Mac)
chmod +x run_flask.sh
./run_flask.sh
```

## 🎯 Vantagens da Migração

### ✅ Vantagens do Flask

1. **Melhor Performance**: Flask é mais leve e rápido
2. **Controle Total**: Você controla cada aspecto da aplicação
3. **Produção Ready**: Melhor para ambientes de produção
4. **SEO Friendly**: Melhor para indexação em mecanismos de busca
5. **Escalabilidade**: Fácil de escalar horizontal e verticalmente
6. **Customização**: Design completamente personalizável
7. **Padrão da Indústria**: Flask é amplamente usado em produção

### ⚠️ Considerações

1. **Mais Código**: Flask requer mais código do que Streamlit
2. **HTML/CSS**: Necessário conhecimento de frontend
3. **Complexidade**: Curva de aprendizado um pouco maior

## 🔧 Troubleshooting Comum

### Erro: "Template not found"
```
jinja2.exceptions.TemplateNotFound: login.html
```
**Solução**: Certifique-se de que todos os arquivos HTML estão na pasta `templates/`

### Erro: "Working outside of request context"
```
RuntimeError: Working outside of request context
```
**Solução**: Certifique-se de acessar `session`, `request`, etc. apenas dentro de rotas

### Erro: "Secret key not set"
```
RuntimeError: The session is unavailable because no secret key was set
```
**Solução**: Configure `FLASK_SECRET_KEY` no arquivo `.env` ou em `frontend_flask.py`

### Porta em uso
```
OSError: [Errno 48] Address already in use
```
**Solução**: 
```bash
# Encontrar processo usando a porta 5000
lsof -i :5000

# Matar o processo
kill -9 <PID>

# Ou usar outra porta
export FLASK_PORT=5001
python3 frontend_flask.py
```

## 📚 Recursos Adicionais

### Documentação
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Jinja2 Templates](https://jinja.palletsprojects.com/)
- [Bootstrap 5 Docs](https://getbootstrap.com/docs/5.3/)

### Tutoriais
- [Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world)
- [Real Python Flask](https://realpython.com/tutorials/flask/)

## 🎓 Próximos Passos

Após a migração bem-sucedida, considere:

1. **Adicionar testes**: Implemente testes unitários e de integração
2. **Configurar WSGI**: Use Gunicorn ou uWSGI para produção
3. **Adicionar cache**: Implemente cache com Redis
4. **Melhorar UI**: Adicione mais animações e interatividade
5. **Implementar logging**: Configure logging robusto
6. **Adicionar monitoramento**: Use ferramentas como Sentry

## ✅ Checklist de Migração

- [ ] Dependências instaladas
- [ ] Estrutura de pastas criada
- [ ] Arquivos copiados
- [ ] Variáveis de ambiente configuradas
- [ ] Backend rodando
- [ ] Frontend acessível em http://localhost:5000
- [ ] Login funcional
- [ ] Todas as funcionalidades testadas
- [ ] Performance satisfatória
- [ ] Documentação atualizada

---

**Parabéns pela migração! 🎉**

Se você encontrar problemas, consulte a documentação ou abra uma issue no repositório.
