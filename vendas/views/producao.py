from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse

from core.mixins import laser_ou_gerente, montagem_ou_gerente
from vendas.models import Pedido


@laser_ou_gerente
def laser_list(request):
    aguardando = Pedido.objects.filter(
        status=Pedido.Status.AGUARD_PRODUCAO
    ).select_related('cliente', 'criado_por').prefetch_related('itens__produto')

    em_corte = Pedido.objects.filter(
        status=Pedido.Status.CUTTING
    ).select_related('cliente', 'criado_por').prefetch_related('itens__produto')

    em_corte_com_progresso = []
    for pedido in em_corte:
        progresso = pedido.progresso_corte
        em_corte_com_progresso.append({
            'pedido':      pedido,
            'progresso':   progresso,
            'incompletos': [p for p in progresso if not p['completo']],
        })

    return render(request, 'vendas/laser_list.html', {
        'aguardando': aguardando,
        'em_corte':   em_corte_com_progresso,
    })

@laser_ou_gerente
def laser_confirmar(request, pk):
    pedido = get_object_or_404(
        Pedido, pk=pk,
        status__in=[Pedido.Status.AGUARD_PRODUCAO, Pedido.Status.CUTTING]
    )

    if request.method == 'POST':
        url = reverse('producao_corte:create') + f'?pedido_pk={pedido.pk}'
        return redirect(url)

    return redirect('vendas:laser_list')


@laser_ou_gerente
def laser_finalizar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk, status=Pedido.Status.CUTTING)

    if request.method == 'POST':
        pedido.status = Pedido.Status.ASSEMBLING
        pedido.save(update_fields=['status', 'atualizado_em'])
        messages.success(request, f'Pedido {pedido.numero} enviado para montagem.')
        return redirect('vendas:laser_list')

    return redirect('vendas:laser_list')


@montagem_ou_gerente
def montagem_list(request):
    pedidos = Pedido.objects.filter(
        status=Pedido.Status.ASSEMBLING
    ).select_related('cliente', 'criado_por').prefetch_related('itens__produto')

    pedidos_com_progresso = []
    for pedido in pedidos:
        pedidos_com_progresso.append({
            'pedido':    pedido,
            'progresso': pedido.progresso_montagem,
        })

    return render(request, 'vendas/montagem_list.html', {
        'pedidos': pedidos_com_progresso,
    })


@montagem_ou_gerente
def montagem_finalizar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk, status=Pedido.Status.ASSEMBLING)

    if request.method == 'POST':
        url = reverse('montagem:registrar') + f'?pedido_pk={pedido.pk}'
        return redirect(url)

    return redirect('vendas:montagem_list')