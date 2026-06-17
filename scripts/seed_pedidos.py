import os
import sys
import django
import random
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from clientes.models import Cliente
from produtos.models import Produto
from produtos.models.preco import PrecoProduto
from vendas.models import Pedido, ItemPedido
from vendas.models.pagamento import Pagamento

# ── Configurações ──
TOTAL_PEDIDOS     = 300
PEDIDOS_PAGOS     = 150  # 150 totalmente pagos
PEDIDOS_PENDENTES = 100  # 100 com pagamento parcial
PEDIDOS_SEM_PAG   = 50   # 50 sem nenhum pagamento

METODOS = ['pix', 'transfer', 'boleto', 'credit', 'debit', 'cash']

TIPOS_VENDA = ['direct', 'replacement', 'exchange', 'maintenance', 'advertising']

STATUS_OPCOES = ['open', 'in_production', 'picking', 'shipped', 'delivered']


def gerar_transacao():
    return f'TXN{random.randint(100000, 999999999)}'


def main():
    # Busca usuários
    try:
        vendedor1 = User.objects.get(username='RobertoAdmin')
    except User.DoesNotExist:
        print('Usuário RobertoAdmin não encontrado.')
        sys.exit(1)

    try:
        vendedor2 = User.objects.get(username='Vendedor')
    except User.DoesNotExist:
        print('Usuário Vendedor não encontrado.')
        sys.exit(1)

    vendedores = [vendedor1, vendedor2]

    # Busca clientes
    clientes = list(Cliente.objects.filter(ativo=True))
    if not clientes:
        print('Nenhum cliente encontrado. Rode seed_clientes.py primeiro.')
        sys.exit(1)

    # Busca produtos com preço
    produtos = list(
        Produto.objects.filter(ativo=True, categoria='produto_final')
                       .select_related('preco')
    )
    produtos_com_preco = [p for p in produtos if hasattr(p, 'preco') and p.preco]

    if not produtos_com_preco:
        print('Nenhum produto com preço encontrado. Cadastre preços primeiro.')
        sys.exit(1)

    print(f'Encontrados {len(clientes)} clientes e {len(produtos_com_preco)} produtos com preço.')

    criados = 0
    transacoes_usadas = set(
        Pagamento.objects.values_list('transacao', flat=True)
    )

    def nova_transacao():
        while True:
            t = gerar_transacao()
            if t not in transacoes_usadas:
                transacoes_usadas.add(t)
                return t

    for i in range(TOTAL_PEDIDOS):
        vendedor  = random.choice(vendedores)
        cliente   = random.choice(clientes)
        tipo      = random.choice(TIPOS_VENDA)
        n_itens   = random.randint(1, 5)

        pedido = Pedido.objects.create(
            cliente              = cliente,
            tipo_venda           = tipo,
            condicao_pagamento   = random.choice(['À vista', '30 dias', '30/60', '30/60/90']),
            contato              = cliente.contato or '',
            transportadora       = random.choice([
                'Contratação Remetente - CIF',
                'Retirada na Loja',
                'Envio pela Decorcril',
                '',
            ]),
            frete                = Decimal(str(random.choice([0, 0, 0, 50, 100, 150, 200]))),
            percentual_entrada   = Decimal(str(random.choice([0, 30, 50, 100]))),
            observacoes          = '',
            observacoes_internas = '',
            criado_por           = vendedor,
        )

        # Adiciona itens
        for _ in range(n_itens):
            produto = random.choice(produtos_com_preco)
            qtd     = random.randint(1, 10)
            preco   = produto.preco.preco_venda
            ItemPedido.objects.create(
                pedido         = pedido,
                produto        = produto,
                quantidade     = qtd,
                preco_unitario = preco,
            )

        # Define status manualmente (para variar)
        if tipo in ('exchange', 'maintenance', 'advertising', 'replacement'):
            pedido.status = random.choice(['in_production', 'picking', 'shipped', 'delivered'])
        else:
            pedido.status = random.choice(STATUS_OPCOES)
        pedido.save(update_fields=['status', 'atualizado_em'])

        # Pagamentos
        if i < PEDIDOS_PAGOS:
            # Totalmente pago
            metodo = random.choice(METODOS)
            transacao = None if metodo == 'cash' else nova_transacao()
            Pagamento.objects.create(
                pedido     = pedido,
                metodo     = metodo,
                valor      = pedido.total_geral,
                transacao  = transacao,
                criado_por = vendedor,
            )

        elif i < PEDIDOS_PAGOS + PEDIDOS_PENDENTES:
            # Parcialmente pago (50% do total)
            valor_parcial = (pedido.total_geral * Decimal('0.5')).quantize(Decimal('0.01'))
            if valor_parcial > 0:
                metodo = random.choice(METODOS)
                transacao = None if metodo == 'cash' else nova_transacao()
                Pagamento.objects.create(
                    pedido     = pedido,
                    metodo     = metodo,
                    valor      = valor_parcial,
                    transacao  = transacao,
                    criado_por = vendedor,
                )
        # else: sem pagamento (PEDIDOS_SEM_PAG)

        criados += 1
        if criados % 50 == 0:
            print(f'{criados} pedidos criados...')

    print(f'\n✅ {criados} pedidos criados com sucesso!')
    print(f'   {PEDIDOS_PAGOS} totalmente pagos')
    print(f'   {PEDIDOS_PENDENTES} parcialmente pagos')
    print(f'   {PEDIDOS_SEM_PAG} sem pagamento')


if __name__ == '__main__':
    main()