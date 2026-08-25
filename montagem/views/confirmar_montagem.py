from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from producao_corte.models import ProdutoCortado
from producao_corte.services import (
    debitar_componentes_ficha,
    pedidos_precisando_peca,
    confirmar_montagem_peca,
)

@login_required
def confirmar_montagem(request, token):
    peca = get_object_or_404(ProdutoCortado, token=token)

    # ── Peça já separada ──
    if peca.status == 'separado':
        return render(request, 'vendas/peca_ja_separada.html', {'peca': peca})

    # ── Peça montada — separação ──
    if peca.status == 'montado':

        # Peça avulsa — vincular a um pedido
        if not peca.pedido:
            pedidos_precisando = pedidos_precisando_peca(peca)

            if request.method == 'POST':
                pedido_pk = request.POST.get('pedido_pk')
                if pedido_pk:
                    from vendas.models import Pedido
                    pedido = get_object_or_404(
                        Pedido,
                        pk=pedido_pk,
                        status__in=['picking', 'aguard_producao']
                    )

                    debitar_componentes_ficha(peca, pedido, request.user)

                    peca.pedido       = pedido
                    peca.status       = 'separado'
                    peca.separada_por = request.user
                    peca.separada_em  = timezone.now()
                    peca.save(update_fields=['pedido', 'status', 'separada_por', 'separada_em'])

                    # Se pedido estava em aguard_producao, vai para picking
                    if pedido.status == 'aguard_producao':
                        pedido.status = pedido.Status.PICKING
                        pedido.save(update_fields=['status', 'atualizado_em'])

                    return render(request, 'vendas/peca_separada.html', {
                        'peca':   peca,
                        'pedido': pedido,
                    })

            return render(request, 'vendas/peca_vincular_pedido.html', {
                'peca':               peca,
                'pedidos_precisando': pedidos_precisando,
            })

        # Peça com pedido — confirmar separação
        if request.method == 'POST':
            pedido = peca.pedido

            debitar_componentes_ficha(peca, pedido, request.user)

            peca.status       = 'separado'
            peca.separada_por = request.user
            peca.separada_em  = timezone.now()
            peca.save(update_fields=['status', 'separada_por', 'separada_em'])

            return render(request, 'vendas/peca_separada.html', {
                'peca':   peca,
                'pedido': pedido,
            })

        return render(request, 'vendas/peca_confirmar_separacao.html', {'peca': peca})

    # ── Peça aguardando montagem ──
    if request.method == 'POST':
        confirmar_montagem_peca(peca, request.user)
        return render(request, 'montagem/peca_montada.html', {
            'peca':   peca,
            'pedido': peca.pedido,
        })

    return render(request, 'montagem/peca_confirmar.html', {'peca': peca})