from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from vendas.models import Pedido


@login_required
def expedir_pedido(request, token):
    pedido = get_object_or_404(Pedido, token_expedicao=token)

    # ── Já foi expedido ──
    if pedido.status in [Pedido.Status.SHIPPED, Pedido.Status.DELIVERED]:
        return render(request, 'vendas/expedicao_ja_confirmada.html', {
            'pedido': pedido,
        })

    # ── Não está em separação ──
    if pedido.status != Pedido.Status.PICKING:
        return render(request, 'vendas/expedicao_status_invalido.html', {
            'pedido': pedido,
        })

    # ── Confirmação ──
    if request.method == 'POST':
        from producao_corte.models import ProdutoCortado

        if pedido.transportadora == 'Retirada na Loja':
            pedido.status = Pedido.Status.DELIVERED
            pedido.save(update_fields=['status', 'atualizado_em'])
            messages.success(request, f'Retirada do pedido {pedido.numero} confirmada!')
        else:
            pedido.status = Pedido.Status.SHIPPED
            pedido.save(update_fields=['status', 'atualizado_em'])
            messages.success(request, f'Envio do pedido {pedido.numero} confirmado!')

        # Avança as peças cortadas do pedido de 'separado' para 'enviado'
        ProdutoCortado.objects.filter(
            pedido=pedido, status='separado'
        ).update(status='enviado')

        return redirect('vendas:expedir_pedido', token=token)

    return render(request, 'vendas/expedicao_confirmar.html', {
        'pedido':      pedido,
        'is_retirada': pedido.transportadora == 'Retirada na Loja',
    })