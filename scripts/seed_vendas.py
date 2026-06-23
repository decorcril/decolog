import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# Só depois do setup:
import random
import calendar
from decimal import Decimal
from datetime import date

from django.contrib.auth.models import User
from django.utils import timezone
from clientes.models import Cliente
from produtos.models import Produto
from vendas.models import Pedido, ItemPedido
from vendas.models.pagamento import Pagamento

# ── Configurações ──
PEDIDOS_POR_MES_POR_VENDEDOR = 10
METODOS  = ['pix', 'transfer', 'boleto', 'credit', 'debit', 'cash']
TIPOS    = ['direct', 'maintenance']
STATUS   = ['aguard_producao', 'cutting', 'assembling', 'picking', 'shipped', 'delivered']


def gerar_transacao(usadas):
    while True:
        t = f'SEED{random.randint(100000, 999999999)}'
        if t not in usadas:
            usadas.add(t)
            return t


def main():
    vendedores = list(User.objects.filter(
        groups__name='Vendedor', is_active=True
    ).order_by('username'))

    if not vendedores:
        print('Nenhum vendedor encontrado.')
        sys.exit(1)

    clientes = list(Cliente.objects.filter(ativo=True))
    if not clientes:
        print('Nenhum cliente encontrado.')
        sys.exit(1)

    produtos = list(
        Produto.objects.filter(ativo=True, categoria='produto_final')
                       .select_related('preco')
    )
    produtos = [p for p in produtos if hasattr(p, 'preco') and p.preco]
    if not produtos:
        print('Nenhum produto com preço encontrado.')
        sys.exit(1)

    print(f'Vendedores: {[v.username for v in vendedores]}')
    print(f'Clientes: {len(clientes)} | Produtos: {len(produtos)}')

    hoje  = date.today()
    meses = [(hoje.year, m) for m in range(1, hoje.month + 1)]

    transacoes_usadas = set(
        Pagamento.objects.values_list('transacao', flat=True)
    )

    criados = 0

    for ano, mes in meses:
        _, ultimo_dia = calendar.monthrange(ano, mes)
        print(f'\n── {ano}/{mes:02d} ──')

        for vendedor in vendedores:
            for _ in range(PEDIDOS_POR_MES_POR_VENDEDOR):
                cliente = random.choice(clientes)
                produto = random.choice(produtos)
                qtd     = random.randint(1, 5)
                preco   = produto.preco.preco_venda

                pedido = Pedido.objects.create(
                    cliente              = cliente,
                    tipo_venda           = random.choice(TIPOS),
                    condicao_pagamento   = random.choice(['À vista', '30 dias', '30/60']),
                    contato              = cliente.contato or '',
                    transportadora       = random.choice([
                        'Contratação Remetente - CIF',
                        'Retirada na Loja',
                        'Envio pela Decorcril',
                        '',
                    ]),
                    frete                = Decimal(str(random.choice([0, 0, 50, 100]))),
                    percentual_entrada   = Decimal('0'),
                    observacoes          = f'Seed — {vendedor.username} {ano}/{mes:02d}',
                    criado_por           = vendedor,
                    status               = random.choice(STATUS),
                )

                ItemPedido.objects.create(
                    pedido         = pedido,
                    produto        = produto,
                    quantidade     = qtd,
                    preco_unitario = preco,
                )

                # Data aleatória no mês
                dia = random.randint(1, ultimo_dia)
                dt = timezone.datetime(
                    ano, mes, dia,
                    random.randint(8, 17),
                    random.randint(0, 59),
                    tzinfo=timezone.UTC,
                )
                Pedido.objects.filter(pk=pedido.pk).update(criado_em=dt)

                # Pagamento — todos têm pelo menos um pagamento parcial
                valor_pago = (pedido.total_geral * Decimal(
                    str(random.choice([0.5, 0.75, 1.0]))
                )).quantize(Decimal('0.01'))

                metodo    = random.choice(METODOS)
                transacao = None if metodo == 'cash' else gerar_transacao(transacoes_usadas)

                Pagamento.objects.create(
                    pedido     = pedido,
                    metodo     = metodo,
                    valor      = valor_pago,
                    transacao  = transacao,
                    criado_por = vendedor,
                )

                criados += 1

            print(f'  {vendedor.username}: {PEDIDOS_POR_MES_POR_VENDEDOR} pedidos criados')

    print(f'\n✅ {criados} pedidos criados com sucesso!')
    print(f'   {len(meses)} meses × {len(vendedores)} vendedores × {PEDIDOS_POR_MES_POR_VENDEDOR} pedidos')


if __name__ == '__main__':
    main()