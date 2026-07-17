from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from producao_corte.models import ProdutoCortado
from movimentacoes.models import Movimentacao
from core.models import Local


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
            from vendas.models import Pedido

            pedidos_precisando = Pedido.objects.filter(
                status__in=['picking', 'aguard_producao'],
                itens__produto=peca.produto,
            ).distinct().select_related('cliente')

            if request.method == 'POST':
                pedido_pk = request.POST.get('pedido_pk')
                if pedido_pk:
                    pedido = get_object_or_404(
                        Pedido,
                        pk=pedido_pk,
                        status__in=['picking', 'aguard_producao']
                    )

                    fabrica = pedido.local_saida or Local.objects.filter(tipo='fabrica').first()

                    try:
                        ficha = peca.produto.ficha_tecnica
                        for componente in ficha.itens.select_related('material').all():
                            Movimentacao.objects.create(
                                produto    = componente.material,
                                local      = fabrica,
                                tipo       = 'saida',
                                motivo     = 'venda',
                                quantidade = componente.quantidade,
                                observacao = f'Separação — Pedido {pedido.numero} ({peca.produto.nome})',
                                usuario    = request.user,
                            )
                    except peca.produto.__class__.ficha_tecnica.RelatedObjectDoesNotExist:
                        Movimentacao.objects.create(
                            produto    = peca.produto,
                            local      = fabrica,
                            tipo       = 'saida',
                            motivo     = 'venda',
                            quantidade = 1,
                            observacao = f'Separação — Pedido {pedido.numero} ({peca.produto.nome})',
                            usuario    = request.user,
                        )

                    peca.pedido       = pedido
                    peca.status       = 'separado'
                    peca.separada_por = request.user
                    peca.separada_em  = timezone.now()
                    peca.save(update_fields=['pedido', 'status', 'separada_por', 'separada_em'])

                    # Se pedido estava em aguard_producao, vai para picking
                    if pedido.status == 'aguard_producao':
                        pedido.status = pedido.Status.PICKING
                        pedido.save(update_fields=['status', 'atualizado_em'])

                    # Verifica se todas as peças do pedido foram separadas
                    total     = ProdutoCortado.objects.filter(pedido=pedido).count()
                    separadas = ProdutoCortado.objects.filter(pedido=pedido, status='separado').count()

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
            pedido  = peca.pedido
            fabrica = pedido.local_saida or Local.objects.filter(tipo='fabrica').first()

            try:
                ficha = peca.produto.ficha_tecnica
                for componente in ficha.itens.select_related('material').all():
                    Movimentacao.objects.create(
                        produto    = componente.material,
                        local      = fabrica,
                        tipo       = 'saida',
                        motivo     = 'venda',
                        quantidade = componente.quantidade,
                        observacao = f'Separação — Pedido {pedido.numero} ({peca.produto.nome})',
                        usuario    = request.user,
                    )
            except peca.produto.__class__.ficha_tecnica.RelatedObjectDoesNotExist:
                Movimentacao.objects.create(
                    produto    = peca.produto,
                    local      = fabrica,
                    tipo       = 'saida',
                    motivo     = 'venda',
                    quantidade = 1,
                    observacao = f'Separação — Pedido {pedido.numero} ({peca.produto.nome})',
                    usuario    = request.user,
                )

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
        fabrica = Local.objects.filter(tipo='fabrica').first()

        try:
            ficha = peca.produto.ficha_tecnica
            for componente in ficha.itens.select_related('material').all():
                Movimentacao.objects.create(
                    produto    = componente.material,
                    local      = fabrica,
                    tipo       = 'entrada',
                    motivo     = 'producao',
                    quantidade = componente.quantidade,
                    observacao = f'Montagem — {peca.produto.nome}',
                    usuario    = request.user,
                )
        except peca.produto.__class__.ficha_tecnica.RelatedObjectDoesNotExist:
            Movimentacao.objects.create(
                produto    = peca.produto,
                local      = fabrica,
                tipo       = 'entrada',
                motivo     = 'producao',
                quantidade = 1,
                observacao = f'Montagem — {peca.produto.nome}',
                usuario    = request.user,
            )

        peca.status      = 'montado'
        peca.montada_por = request.user
        peca.montada_em  = timezone.now()
        peca.save(update_fields=['status', 'montada_por', 'montada_em'])

        # Verifica se todas as peças do pedido foram montadas
        if peca.pedido:
            pedido   = peca.pedido
            total    = ProdutoCortado.objects.filter(pedido=pedido).count()
            montadas = ProdutoCortado.objects.filter(pedido=pedido, status='montado').count()

            if total > 0 and montadas >= total:
                pedido.status = pedido.Status.PICKING
                pedido.save(update_fields=['status', 'atualizado_em'])

        return render(request, 'montagem/peca_montada.html', {
            'peca':   peca,
            'pedido': peca.pedido,
        })

    return render(request, 'montagem/peca_confirmar.html', {'peca': peca})