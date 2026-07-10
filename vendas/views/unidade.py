from django.shortcuts import render, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from vendas.models import Pedido, UnidadePedido
from estoque.models import Estoque


def _montar_unidade(request, token, unidade, pedido):
    from core.models import Local
    from movimentacoes.models import Movimentacao

    total    = UnidadePedido.objects.filter(item__pedido=pedido).count()
    montadas = UnidadePedido.objects.filter(item__pedido=pedido, montada=True).count()

    if request.method == 'POST':
        fabrica = Local.objects.filter(tipo='fabrica').first()
        produto = unidade.item.produto

        # ── Registra entrada no estoque ──
        try:
            ficha = produto.ficha_tecnica
            for componente in ficha.itens.select_related('material').all():
                Movimentacao.objects.create(
                    produto    = componente.material,
                    local      = fabrica,
                    tipo       = 'entrada',
                    motivo     = 'producao',
                    quantidade = componente.quantidade,
                    observacao = f'Montagem — Pedido {pedido.numero} ({produto.nome}) Unidade {unidade.numero}',
                    usuario    = request.user,
                )
        except produto.__class__.ficha_tecnica.RelatedObjectDoesNotExist:
            Movimentacao.objects.create(
                produto    = produto,
                local      = fabrica,
                tipo       = 'entrada',
                motivo     = 'producao',
                quantidade = 1,
                observacao = f'Montagem — Pedido {pedido.numero} ({produto.nome}) Unidade {unidade.numero}',
                usuario    = request.user,
            )

        unidade.montada     = True
        unidade.montada_em  = timezone.now()
        unidade.montada_por = request.user
        unidade.save(update_fields=['montada', 'montada_em', 'montada_por'])

        montadas = UnidadePedido.objects.filter(item__pedido=pedido, montada=True).count()

        if total > 0 and montadas >= total:
            pedido.status = Pedido.Status.PICKING
            pedido.save(update_fields=['status', 'atualizado_em'])

        return render(request, 'vendas/montagem_confirmada.html', {
            'pedido':   pedido,
            'unidade':  unidade,
            'montadas': montadas,
            'total':    total,
            'completo': montadas >= total,
        })

    return render(request, 'vendas/montar_confirmar.html', {
        'pedido':   pedido,
        'unidade':  unidade,
        'montadas': montadas,
        'total':    total,
    })


def _separar_unidade(request, token, unidade, pedido):
    total     = UnidadePedido.objects.filter(item__pedido=pedido).count()
    separadas = UnidadePedido.objects.filter(item__pedido=pedido, separada=True).count()

    if request.method == 'POST':
        from core.models import Local
        from movimentacoes.models import Movimentacao

        fabrica = pedido.local_saida or Local.objects.filter(tipo='fabrica').first()
        produto = unidade.item.produto

        # ── Baixa estoque ──
        try:
            ficha = produto.ficha_tecnica
            for componente in ficha.itens.select_related('material').all():
                saldo = Estoque.objects.filter(produto=componente.material, local=fabrica).first()
                local_usar = fabrica if saldo and saldo.quantidade >= componente.quantidade else Local.objects.filter(tipo='fabrica').first()
                Movimentacao.objects.create(
                    produto    = componente.material,
                    local      = local_usar,
                    tipo       = 'saida',
                    motivo     = 'venda',
                    quantidade = componente.quantidade,
                    observacao = f'Separação — Pedido {pedido.numero} ({produto.nome}) Unidade {unidade.numero}',
                    usuario    = request.user,
                )
        except produto.__class__.ficha_tecnica.RelatedObjectDoesNotExist:
            saldo = Estoque.objects.filter(produto=produto, local=fabrica).first()
            local_usar = fabrica if saldo and saldo.quantidade >= 1 else Local.objects.filter(tipo='fabrica').first()
            Movimentacao.objects.create(
                produto    = produto,
                local      = local_usar,
                tipo       = 'saida',
                motivo     = 'venda',
                quantidade = 1,
                observacao = f'Separação — Pedido {pedido.numero} ({produto.nome}) Unidade {unidade.numero}',
                usuario    = request.user,
            )

        unidade.separada     = True
        unidade.separada_em  = timezone.now()
        unidade.separada_por = request.user
        unidade.save(update_fields=['separada', 'separada_em', 'separada_por'])

        separadas = UnidadePedido.objects.filter(item__pedido=pedido, separada=True).count()

        return render(request, 'vendas/separacao_confirmada.html', {
            'pedido':    pedido,
            'unidade':   unidade,
            'separadas': separadas,
            'total':     total,
            'completo':  separadas >= total,
        })

    return render(request, 'vendas/separacao_confirmar.html', {
        'pedido':    pedido,
        'unidade':   unidade,
        'separadas': separadas,
        'total':     total,
    })

@login_required
def unidade_pedido(request, token):
    unidade = get_object_or_404(UnidadePedido, token=token)
    pedido  = unidade.item.pedido

    if pedido.status == Pedido.Status.ASSEMBLING:
        return _montar_unidade(request, token, unidade, pedido)

    if pedido.status == Pedido.Status.PICKING:
        return _separar_unidade(request, token, unidade, pedido)

    return render(request, 'vendas/unidade_status_invalido.html', {
        'pedido':  pedido,
        'unidade': unidade,
    })