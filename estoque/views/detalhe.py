from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from core.mixins import loja_do_usuario
from produtos.models import Produto
from estoque.models import Estoque
from movimentacoes.models import Movimentacao


@login_required
def estoque_detalhe(request, produto_id):
    produto = get_object_or_404(Produto, pk=produto_id)
    loja_restrita = loja_do_usuario(request.user)

    saldos = Estoque.objects.filter(
        produto=produto
    ).select_related('local').order_by('local__nome')

    ultimas_movimentacoes = Movimentacao.objects.filter(
        produto=produto
    ).select_related('local', 'local_destino', 'fornecedor', 'usuario').order_by('-data_hora')

    if loja_restrita:
        saldos = saldos.filter(local=loja_restrita)
        # Mostra movimentações onde a loja do usuário é origem OU destino
        # (ex: transferência recebida por essa loja).
        ultimas_movimentacoes = ultimas_movimentacoes.filter(
            Q(local=loja_restrita) | Q(local_destino=loja_restrita)
        )

    return render(request, 'estoque/detalhe/detail.html', {
        'produto': produto,
        'saldos': saldos,
        'ultimas_movimentacoes': ultimas_movimentacoes[:10],
        'loja_restrita': loja_restrita,
    })