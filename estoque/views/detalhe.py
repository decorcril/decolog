from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from produtos.models import Produto
from estoque.models import Estoque
from movimentacoes.models import Movimentacao


@login_required
def estoque_detalhe(request, produto_id):
    produto = get_object_or_404(Produto, pk=produto_id)

    saldos = Estoque.objects.filter(
        produto=produto
    ).select_related('local').order_by('local__nome')

    ultimas_movimentacoes = Movimentacao.objects.filter(
        produto=produto
    ).select_related('local', 'local_destino', 'fornecedor', 'usuario').order_by('-data_hora')[:10]

    return render(request, 'estoque/detalhe/detail.html', {
        'produto': produto,
        'saldos': saldos,
        'ultimas_movimentacoes': ultimas_movimentacoes,
    })