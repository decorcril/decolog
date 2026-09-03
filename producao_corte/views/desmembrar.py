from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db import transaction

from core.mixins import estoque_ou_gerente
from producao_corte.models import ProdutoCortado
from producao_corte.services import desmembrar_peca


@estoque_ou_gerente
def desmembrar_kit(request, token):
    peca = get_object_or_404(ProdutoCortado, token=token)

    if peca.status not in ('montado', 'separado'):
        messages.error(request, 'Só é possível desmembrar peças montadas ou separadas.')
        return redirect('montagem:confirmar_montagem', token=token)

    if not peca.produto.is_kit:
        messages.error(request, f'"{peca.produto.nome}" não é um Kit — não há o que desmembrar.')
        return redirect('montagem:confirmar_montagem', token=token)

    ficha       = peca.produto.ficha_tecnica
    componentes = ficha.itens.select_related('material').all()

    if request.method == 'POST':
        with transaction.atomic():
            novas = desmembrar_peca(peca, request.user)

        messages.success(
            request,
            f'{peca.produto.nome} desmembrado em {len(novas)} peça(s) avulsa(s). '
            f'Imprima as novas etiquetas.'
        )
        return render(request, 'producao_corte/desmembrar_sucesso.html', {
            'peca_original': peca,
            'pecas_novas':   novas,
        })

    return render(request, 'producao_corte/desmembrar_confirmar.html', {
        'peca':        peca,
        'componentes': componentes,
        'tinha_pedido': peca.pedido,
    })