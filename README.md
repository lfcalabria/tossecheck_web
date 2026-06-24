# TosseCheck Web

Portal web do TosseCheck para veterinarios acessarem responsaveis, pets, videos de tosse e prontuarios clinicos.

## Stack

- Python 3.11
- Django 5.2
- django-allauth
- SQLite em desenvolvimento
- Testes com `django.test`
- CI com GitHub Actions

## Como rodar localmente

Crie e ative o ambiente virtual:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instale as dependencias:

```powershell
pip install -r requirements-dev.txt
```

Copie as variaveis de exemplo se quiser documentar seu ambiente local:

```powershell
Copy-Item .env.example .env
```

Observacao: o projeto le variaveis diretamente do ambiente. O arquivo `.env` fica ignorado pelo Git; carregue essas variaveis pela sua IDE, terminal ou ferramenta de ambiente.

Rode as migracoes e suba o servidor:

```powershell
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Acesse:

```text
http://127.0.0.1:8000/
```

## Modo demo

Para apresentar as telas sem depender do backend externo:

```text
http://127.0.0.1:8000/portal/demo/
```

Tambem e possivel entrar pela tela de login:

```text
CRMV: DEMO
Senha: demo123
```

CPF demo com responsavel cadastrado:

```text
529.982.247-25
```

## Testes e qualidade

Rode o check do Django:

```powershell
python manage.py check --fail-level WARNING
```

Rode a suite de testes:

```powershell
python manage.py test
```

Rode com cobertura:

```powershell
coverage run manage.py test
coverage report
```

## GitHub Actions

O workflow em `.github/workflows/ci.yml` executa:

- instalacao das dependencias de desenvolvimento;
- `python manage.py check --fail-level WARNING`;
- `python manage.py makemigrations --check --dry-run`;
- testes com cobertura minima de 65%.

## Estrutura

```text
tossecheck_web/      Configuracoes Django do projeto
portal/             App do portal web
portal/templates/   Templates HTML do portal
portal/static/      CSS, JS e imagens do portal
portal/tests/       Testes automatizados
.github/workflows/  Pipelines de CI
```

## Regras de engenharia

- Mantenha as dependencias declaradas em `requirements.txt` e ferramentas de desenvolvimento em `requirements-dev.txt`.
- Nao versione `.env`, banco SQLite local, logs, `staticfiles/`, `media/` ou relatorios de cobertura.
- Preserve o modo demo isolado da integracao real com backend.
- Ao alterar templates, mantenha o padrao visual definido em `portal/base.html` e `portal/static/portal/pets.css`.
- Ao alterar views, cubra comportamento feliz e falhas de backend/sessao nos testes.
