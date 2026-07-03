from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from core.mixins import logistica_ou_gerente
from vendas.models import Pedido
from estoque.models import Estoque
from core.models import Local


def _verificar_estoque_pedido(pedido):
    """
    Verifica se todos os itens do pedido têm estoque suficiente
    no local_saida (ou fábrica como fallback).
    Retorna lista com status de cada item.
    """
    local = pedido.local_saida
    if not local:
        local = Local.objects.filter(tipo='fabrica').first()

    resultado = []
    tudo_ok   = True

    for item in pedido.itens.select_related('produto').all():
        try:
            ficha = item.produto.ficha_tecnica
            # Produto composto — verifica componentes
            itens_ok = True
            componentes = []
            for componente in ficha.itens.select_related('material').all():
                qtd_necessaria = componente.quantidade * item.quantidade
                saldo = Estoque.objects.filter(
                    produto=componente.material, local=local
                ).first()
                disponivel = saldo.quantidade if saldo else 0
                ok = disponivel >= qtd_necessaria
                if not ok:
                    itens_ok = False
                    tudo_ok  = False
                componentes.append({
                    'nome':       componente.material.nome,
                    'necessario': qtd_necessaria,
                    'disponivel': disponivel,
                    'ok':         ok,
                })
            resultado.append({
                'nome':        item.produto.nome,
                'quantidade':  item.quantidade,
                'composto':    True,
                'componentes': componentes,
                'ok':          itens_ok,
            })
        except item.produto.__class__.ficha_tecnica.RelatedObjectDoesNotExist:
            # Produto simples
            saldo = Estoque.objects.filter(
                produto=item.produto, local=local
            ).first()
            disponivel = saldo.quantidade if saldo else 0
            ok = disponivel >= item.quantidade
            if not ok:
                tudo_ok = False
            resultado.append({
                'nome':       item.produto.nome,
                'quantidade': item.quantidade,
                'composto':   False,
                'disponivel': disponivel,
                'ok':         ok,
            })

    return resultado, tudo_ok, local


@logistica_ou_gerente
def logistica_list(request):
    # ── Ação de usar estoque ──
    if request.method == 'POST':
        pedido_pk = request.POST.get('pedido_pk')
        pedido    = get_object_or_404(Pedido, pk=pedido_pk, status=Pedido.Status.AGUARD_PRODUCAO)

        _, tudo_ok, _ = _verificar_estoque_pedido(pedido)

        if tudo_ok:
            pedido.status = Pedido.Status.PICKING
            pedido.save(update_fields=['status', 'atualizado_em'])
            messages.success(request, f'Pedido {pedido.numero} enviado para separação usando estoque disponível!')
        else:
            messages.error(request, f'Estoque insuficiente para o pedido {pedido.numero}.')

        return redirect('vendas:logistica_list')

    # ── Pedidos em picking ──
    pedidos_picking = Pedido.objects.filter(
        status=Pedido.Status.PICKING
    ).select_related('cliente', 'criado_por').prefetch_related('itens__produto')

    picking_com_info = []
    for pedido in pedidos_picking:
        picking_com_info.append({
            'pedido':      pedido,
            'is_retirada': pedido.transportadora == 'Retirada na Loja',
        })

    paginator_picking = Paginator(picking_com_info, 10)
    page_picking      = paginator_picking.get_page(request.GET.get('page_picking', 1))

    # ── Pedidos aguardando produção — verificar estoque ──
    pedidos_aguardando = Pedido.objects.filter(
        status=Pedido.Status.AGUARD_PRODUCAO
    ).select_related('cliente', 'local_saida').prefetch_related('itens__produto')

    aguardando_com_info = []
    for pedido in pedidos_aguardando:
        itens_status, tudo_ok, local = _verificar_estoque_pedido(pedido)
        aguardando_com_info.append({
            'pedido':       pedido,
            'itens_status': itens_status,
            'tudo_ok':      tudo_ok,
            'local':        local,
        })

    paginator_aguardando = Paginator(aguardando_com_info, 10)
    page_aguardando      = paginator_aguardando.get_page(request.GET.get('page_aguardando', 1))

    return render(request, 'vendas/logistica_list.html', {
        'pedidos':            page_picking,
        'page_obj':           page_picking,
        'pedidos_aguardando': page_aguardando,
        'page_aguardando':    page_aguardando,
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
        'pedidos':     page_obj,
        'page_obj':    page_obj,
        'q':           q,
        'data_inicio': data_inicio,
        'data_fim':    data_fim,
    })