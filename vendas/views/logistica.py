from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from core.mixins import logistica_ou_gerente
from vendas.models import Pedido, UnidadePedido
from estoque.models import Estoque
from core.models import Local


def _verificar_estoque_pedido(pedido):
    from producao_corte.models import ProdutoCortado

    local = pedido.local_saida
    if not local:
        local = Local.objects.filter(tipo='fabrica').first()

    resultado = []
    tudo_ok   = True

    for item in pedido.itens.select_related('produto').all():

        # ── Produto final — verifica peças montadas no estoque ──
        if item.produto.categoria == 'produto_final':
            disponiveis = ProdutoCortado.objects.filter(
                produto=item.produto,
                status='montado',
                pedido=None,
            ).count()
            ok = disponiveis >= item.quantidade
            if not ok:
                tudo_ok = False
            resultado.append({
                'nome':       item.produto.nome,
                'quantidade': item.quantidade,
                'composto':   False,
                'disponivel': disponiveis,
                'ok':         ok,
            })

        else:
            # ── Insumo ou composto — verifica estoque normal ──
            try:
                ficha = item.produto.ficha_tecnica
                itens_ok    = True
                componentes = []
                for componente in ficha.itens.select_related('material').all():
                    qtd_necessaria = componente.quantidade * item.quantidade
                    saldo      = Estoque.objects.filter(produto=componente.material, local=local).first()
                    disponivel = saldo.quantidade if saldo else 0
                    ok         = disponivel >= qtd_necessaria
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
                saldo      = Estoque.objects.filter(produto=item.produto, local=local).first()
                disponivel = saldo.quantidade if saldo else 0
                ok         = disponivel >= item.quantidade
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


def _todos_insumos(pedido):
    """Retorna True se todos os itens são insumos OU produto_final com peças no estoque."""
    from producao_corte.models import ProdutoCortado
    for item in pedido.itens.select_related('produto').all():
        if item.produto.categoria == 'insumo':
            continue
        if item.produto.categoria == 'produto_final':
            disponiveis = ProdutoCortado.objects.filter(
                produto=item.produto,
                status='montado',
                pedido=None,
            ).count()
            if disponiveis >= item.quantidade:
                continue
        return False
    return True

@logistica_ou_gerente
def logistica_list(request):

    if request.method == 'POST':
        action    = request.POST.get('action', 'usar_estoque')
        pedido_pk = request.POST.get('pedido_pk')

        # ── Usar estoque — insumos aguardando produção ──
        if action == 'usar_estoque':
            pedido = get_object_or_404(Pedido, pk=pedido_pk, status=Pedido.Status.AGUARD_PRODUCAO)
            _, tudo_ok, _ = _verificar_estoque_pedido(pedido)
            if tudo_ok:
                pedido.status = Pedido.Status.PICKING
                pedido.save(update_fields=['status', 'atualizado_em'])
                messages.success(request, f'Pedido {pedido.numero} enviado para separação!')
            else:
                messages.error(request, f'Estoque insuficiente para o pedido {pedido.numero}.')

        # ── Separar insumos ──
        elif action == 'separar_insumos':
            from django.utils import timezone
            pedido   = get_object_or_404(Pedido, pk=pedido_pk, status=Pedido.Status.PICKING)
            unidades = UnidadePedido.objects.filter(item__pedido=pedido, separada=False)
            unidades.update(
                separada=True,
                separada_em=timezone.now(),
                separada_por=request.user,
            )
            messages.success(request, f'Todas as unidades do pedido {pedido.numero} foram separadas!')

        return redirect('vendas:logistica_list')

    # ── Pedidos aguardando produção ──
    pedidos_aguardando_qs = Pedido.objects.filter(
        status=Pedido.Status.AGUARD_PRODUCAO
    ).select_related('cliente', 'local_saida').prefetch_related('itens__produto')

    pedidos_aguardando = []
    for pedido in pedidos_aguardando_qs:
        itens_status, tudo_ok, local = _verificar_estoque_pedido(pedido)
        pedidos_aguardando.append({
            'pedido':        pedido,
            'itens_status':  itens_status,
            'tudo_ok':       tudo_ok,
            'local':         local,
            'todos_insumos': _todos_insumos(pedido),
        })

    # ── Pedidos em picking ──
    pedidos_picking = Pedido.objects.filter(
        status='picking',
    ).select_related('cliente', 'criado_por').prefetch_related(
        'itens__produto'
    ).order_by('criado_em')

    pedidos_separacao = []
    pedidos_envio     = []

    for pedido in pedidos_picking:
        from producao_corte.models import ProdutoCortado
        total         = ProdutoCortado.objects.filter(pedido=pedido).count()
        separadas     = ProdutoCortado.objects.filter(pedido=pedido, status='separado').count()

        # Considera também UnidadePedido para insumos
        from vendas.models import UnidadePedido as UP
        total_uni     = UP.objects.filter(item__pedido=pedido).count()
        separadas_uni = UP.objects.filter(item__pedido=pedido, separada=True).count()

        total_geral     = total + total_uni
        separadas_geral = separadas + separadas_uni
        tudo_separado   = total_geral > 0 and separadas_geral >= total_geral

        info = {
            'pedido':        pedido,
            'is_retirada':   pedido.transportadora == 'Retirada na Loja',
            'total':         total_geral,
            'separadas':     separadas_geral,
            'tudo_separado': tudo_separado,
            'todos_insumos': _todos_insumos(pedido),
        }

        if tudo_separado:
            pedidos_envio.append(info)
        else:
            pedidos_separacao.append(info)

    return render(request, 'vendas/logistica_list.html', {
        'pedidos_aguardando': pedidos_aguardando,
        'pedidos_separacao':  pedidos_separacao,
        'pedidos_envio':      pedidos_envio,
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