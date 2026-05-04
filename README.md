# Decolog

Sistema de controle de estoque desenvolvido para a empresa Decorcril. Esta é a primeira versão do sistema, construída com Django, cobrindo o ciclo completo de gestão de materiais — desde a entrada de chapas de acrílico até o registro de cortes e saída de produtos acabados.

## Funcionalidades

**Estoque**
- Consulta de estoque por produto e local
- Entrada, saída, ajuste e transferência de produtos (unitária e em lote)
- Histórico completo de movimentações com filtros avançados
- Relatórios de estoque atual e estoque baixo

**Produção**
- Registro de cortes com rastreamento de chapas utilizadas e produtos cortados
- Estorno automático de estoque ao excluir um registro de corte
- Histórico de cortes por operador

**Cadastros**
- Produtos (insumos, chapas de acrílico e produtos finais)
- Locais de estocagem
- Fornecedores com sistema de tags

**Controle de Acesso**
- Perfis: Administrador, Gerente, Estoquista, Logística, Supervisor de Laser, Operador de Laser
- Cada perfil acessa apenas o que é relevante para sua função
- Dashboard personalizado por perfil

## Tecnologias

- Python 3.14
- Django 6.0.4
- PostgreSQL (produção) / SQLite (desenvolvimento)
- Bootstrap 5.3
- Gunicorn + Nginx (produção)

## Instalação

**Pré-requisitos:** Python 3.11+, PostgreSQL

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/decolog.git
cd decolog

# Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Instale as dependências
pip install -r requirements.txt

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env com suas configurações

# Execute as migrations
python manage.py migrate

# Crie um superusuário
python manage.py createsuperuser

# Inicie o servidor
python manage.py runserver
```

## Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```
SECRET_KEY=sua-chave-secreta
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://usuario:senha@localhost/decolog
```

## Scripts Utilitários

Os scripts estão na pasta `scripts/`:

- `exportar_decolog.py` — exporta produtos e estoques para Excel (backup)
- `popular_registros_corte.py` — popula registros de corte fictícios para testes (apenas desenvolvimento)

```bash
python scripts/exportar_decolog.py
```

## Estrutura do Projeto

```
decolog/
├── config/          # Configurações do Django
├── core/            # Dashboard, locais, fornecedores, perfis
├── produtos/        # Cadastro de produtos
├── estoque/         # Consulta e gestão de estoque
├── movimentacoes/   # Entradas, saídas, transferências
├── producao_corte/  # Registro de cortes
├── relatorios/      # Relatórios de estoque
├── scripts/         # Scripts utilitários
└── static/          # Arquivos estáticos
```

## Autor

Roberto Sousa

## Licença

Uso interno — Decorcril.