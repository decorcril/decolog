from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from core.mixins import logistica_ou_gerente
from vendas.models import Pedido


@logistica_ou_gerente
def logistica_list(request):
    pedidos = Pedido.objects.filter(
        status=Pedido.Status.PICKING
    ).select_related('cliente', 'criado_por').prefetch_related('itens__produto')

    pedidos_com_info = []
    for pedido in pedidos:
        pedidos_com_info.append({
            'pedido':             pedido,
            'progresso_corte':    pedido.progresso_corte,
            'progresso_montagem': pedido.progresso_montagem,
            'is_retirada':        pedido.transportadora == 'Retirada na Loja',
        })

    paginator = Paginator(pedidos_com_info, 10)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'vendas/logistica_list.html', {
        'pedidos':  page_obj,
        'page_obj': page_obj,
    })

@logistica_ou_gerente
def logistica_historico(request):
    q           = request.GET.get('q', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim    = request.GET.get('data_fim', '')

    pedidos = Pedido.objects.filter(
        status__in=['shipped', 'delivered'],
    ).select_related('cliente', 'criado_por').order_by('-atualizado_em')

    if q:
        pedidos = pedidos.filter(
            Q(numero__icontains=q) | Q(cliente__nome__icontains=q)
        )

    if data_inicio:
        pedidos = pedidos.filter(atualizado_em__date__gte=data_inicio)

    if data_fim:
        pedidos = pedidos.filter(atualizado_em__date__lte=data_fim)

    paginator = Paginator(pedidos, 20)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'vendas/logistica_historico.html', {
        'pedidos':      page_obj,
        'page_obj':     page_obj,
        'q':            q,
        'data_inicio':  data_inicio,
        'data_fim':     data_fim,
    })