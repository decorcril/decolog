from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from vendas.models import Pedido


@login_required
def separar_pedido(request, token):
    pedido = get_object_or_404(Pedido, token_separacao=token)

    # ── Não está em picking ──
    if pedido.status != Pedido.Status.PICKING:
        return render(request, 'vendas/separacao_status_invalido.html', {
            'pedido': pedido,
        })

    # ── Já foi separado ──
    if pedido.separado:
        return render(request, 'vendas/separacao_ja_confirmada.html', {
            'pedido': pedido,
        })

    # ── Confirmação ──
    if request.method == 'POST':
        pedido.separado = True
        pedido.save(update_fields=['separado', 'atualizado_em'])
        messages.success(request, f'Separação do pedido {pedido.numero} confirmada!')
        return redirect('vendas:separar_pedido', token=token)

    return render(request, 'vendas/separacao_confirmar.html', {
        'pedido': pedido,
    })