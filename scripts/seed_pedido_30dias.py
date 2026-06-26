import os
import sys
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from clientes.models import Cliente
from produtos.models import Produto
from vendas.models import Pedido, ItemPedido


def main():
    vendedor = User.objects.filter(groups__name='Vendedor', is_active=True).first()
    if not vendedor:
        print('Nenhum vendedor encontrado.')
        return

    cliente = Cliente.objects.filter(ativo=True).first()
    if not cliente:
        print('Nenhum cliente encontrado.')
        return

    produto = Produto.objects.filter(categoria='produto_final', ativo=True).first()
    if not produto:
        print('Nenhum produto encontrado.')
        return

    pedido = Pedido.objects.create(
        cliente    = cliente,
        criado_por = vendedor,
        tipo_venda = 'direct',
        status     = 'open',
        observacoes = 'Pedido de teste — 30 dias sem pagamento',
    )

    ItemPedido.objects.create(
        pedido         = pedido,
        produto        = produto,
        quantidade     = 1,
        preco_unitario = Decimal('500.00'),
    )

    # Força data para 31 dias atrás
    Pedido.objects.filter(pk=pedido.pk).update(
        criado_em=timezone.now() - timedelta(days=31)
    )

    print(f'✅ Pedido {pedido.numero} criado para {vendedor.username}')
    print(f'   Cliente: {cliente.nome}')
    print(f'   Data simulada: {(timezone.now() - timedelta(days=31)).strftime("%d/%m/%Y")}')
    print(f'   Abra o sininho como Financeiro ou Vendedor para ver a notificação!')


if __name__ == '__main__':
    main()