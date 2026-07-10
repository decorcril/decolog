from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from vendas.models import Pedido, UnidadePedido


@login_required
def separar_unidade(request, token):
    unidade = get_object_or_404(UnidadePedido, token=token)
    pedido  = unidade.item.pedido

    total     = UnidadePedido.objects.filter(item__pedido=pedido).count()
    montadas  = UnidadePedido.objects.filter(item__pedido=pedido, montada=True).count()
    separadas = UnidadePedido.objects.filter(item__pedido=pedido, separada=True).count()

    # ── Pedido em montagem ──
    if pedido.status == Pedido.Status.ASSEMBLING:
        if request.method == 'POST':
            unidade.montada    = True
            unidade.montada_em = timezone.now()
            unidade.montada_por = request.user
            unidade.save(update_fields=['montada', 'montada_em', 'montada_por'])

            montadas = UnidadePedido.objects.filter(item__pedido=pedido, montada=True).count()

            if total > 0 and montadas >= total:
                pedido.status = Pedido.Status.PICKING
                pedido.save(update_fields=['status', 'atualizado_em'])
                messages.success(request, f'Todas as unidades montadas! Pedido {pedido.numero} enviado para separação.')
            else:
                messages.success(request, f'Unidade {unidade.numero} de {unidade.item.produto.nome} montada! ({montadas}/{total})')

            return redirect('vendas:separar_unidade', token=token)

        return render(request, 'vendas/separacao_confirmar.html', {
            'pedido':   pedido,
            'unidade':  unidade,
            'total':    total,
            'progresso': montadas,
            'acao':     'montagem',
        })

    # ── Pedido em separação ──
    if pedido.status == Pedido.Status.PICKING:
        if request.method == 'POST':
            unidade.separada     = True
            unidade.separada_em  = timezone.now()
            unidade.separada_por = request.user
            unidade.save(update_fields=['separada', 'separada_em', 'separada_por'])

            separadas = UnidadePedido.objects.filter(item__pedido=pedido, separada=True).count()

            if total > 0 and separadas >= total:
                messages.success(request, f'Todas as unidades separadas! Pedido {pedido.numero} pronto para envio.')
            else:
                messages.success(request, f'Unidade {unidade.numero} de {unidade.item.produto.nome} separada! ({separadas}/{total})')

            return redirect('vendas:separar_unidade', token=token)

        return render(request, 'vendas/separacao_confirmar.html', {
            'pedido':   pedido,
            'unidade':  unidade,
            'total':    total,
            'progresso': separadas,
            'acao':     'separacao',
        })

    # ── Status inválido ──
    return render(request, 'vendas/separacao_status_invalido.html', {
        'pedido':  pedido,
        'unidade': unidade,
    })