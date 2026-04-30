import os
import sys
import django
from datetime import date, timedelta
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.contrib.auth.models import User
from produtos.models import Produto
from estoque.models import Estoque
from producao_corte.models import RegistroCorte, ItemCorte, ProdutoCortado

# ── Busca os objetos necessários ──
operador = User.objects.get(username='RobertoAdmin')
chapa = Produto.objects.get(nome='Chapa de Acrílico Cristal 1030x2030mm - 3mm')
produto = Produto.objects.get(codigo='2029-13')

print(f'Operador: {operador.username}')
print(f'Chapa: {chapa.nome}')
print(f'Produto: {produto.nome}')
print()

# ── Gera 30 registros nos últimos 60 dias ──
hoje = date.today()
criados = 0

for i in range(30):
    data_corte = hoje - timedelta(days=random.randint(1, 60))

    # Verifica se tem estoque suficiente
    estoque = Estoque.objects.filter(produto=chapa).first()
    if not estoque or estoque.quantidade < 1:
        print(f'⚠️  Sem estoque para criar registro {i+1}, pulando...')
        continue

    qtd_chapa = random.randint(1, 3)
    qtd_produto = random.randint(1, 10)

    registro = RegistroCorte.objects.create(
        data=data_corte,
        operador=operador,
        observacao=random.choice([
            'Lote urgente',
            'Pedido cliente VIP',
            'Reposição estoque loja',
            '',
            '',
            '',
        ]),
    )

    item_corte = ItemCorte.objects.create(
        registro=registro,
        chapa=chapa,
        quantidade_chapa=qtd_chapa,
    )

    ProdutoCortado.objects.create(
        item_corte=item_corte,
        produto=produto,
        quantidade=qtd_produto,
    )

    criados += 1
    print(f'✅ {data_corte} — {qtd_chapa}× chapa → {qtd_produto}× {produto.nome}')

print()
print(f'Total criado: {criados} registros')