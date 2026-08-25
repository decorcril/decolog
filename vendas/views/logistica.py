from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone

from core.mixins import logistica_ou_gerente
from vendas.models import Pedido, UnidadePedido
from movimentacoes.models import Movimentacao
from estoque.models import Estoque
from core.models import Local
from producao_corte.services import disponibilidade_produto_final, consumir_produto_final


def _verificar_estoque_pedido(pedido):
    local = pedido.local_saida
    if not local:
        local = Local.objects.filter(tipo='fabrica').first()

    resultado = []
    tudo_ok   = True

    for item in pedido.itens.select_related('produto').all():

        # ── Produto final — peça direta, ou Kit decomposto em avulsas ──
        if item.produto.categoria == 'produto_final':
            ok, n_diretas, componentes = disponibilidade_produto_final(
                item.produto, item.quantidade
            )
            if not ok:
                tudo_ok = False
            resultado.append({
                'nome':        item.produto.nome,
                'quantidade':  item.quantidade,
                'composto':    bool(componentes),
                'disponivel':  n_diretas,
                'componentes': componentes,
                'ok':          ok,
            })

        else:
            # ── Insumo ou receita com matéria-prima — verifica Estoque normal ──
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
    """Retorna True se todos os itens são insumos OU produto_final (simples
    ou Kit) já resolvíveis com peças avulsas em estoque."""
    for item in pedido.itens.select_related('produto').all():
        if item.produto.categoria == 'insumo':
            continue
        if item.produto.categoria == 'produto_final':
            ok, _, _ = disponibilidade_produto_final(item.produto, item.quantidade)
            if ok:
                continue
        return False
    return True


def _processar_uso_estoque(pedido, local, usuario, itens_status=None):
    """
    Efetiva o uso do estoque para um pedido em AGUARD_PRODUCAO:
    - Produto final (simples ou Kit): vincula peça(s) reais via
      producao_corte.services.consumir_produto_final — direta e/ou por
      componentes avulsos, cada uma com seu próprio QR.
    - Insumo/receita com matéria-prima: debita via Movimentacao, como antes.

    Se itens_status for informado (retorno de _verificar_estoque_pedido),
    processa só os itens com ok=True — os demais seguem o fluxo normal de
    corte/montagem. Sem esse parâmetro, processa todos os itens do pedido.
    """
    ok_por_nome = (
        {s['nome']: s['ok'] for s in itens_status}
        if itens_status is not None else None
    )

    for item in pedido.itens.select_related('produto').all():
        if ok_por_nome is not None and not ok_por_nome.get(item.produto.nome, False):
            continue  # sem estoque suficiente para este item — segue fluxo normal

        if item.produto.categoria == 'produto_final':
            consumir_produto_final(item.produto, item.quantidade, pedido, usuario)

        else:
            try:
                ficha = item.produto.ficha_tecnica
                for componente in ficha.itens.select_related('material').all():
                    qtd_necessaria = componente.quantidade * item.quantidade
                    Movimentacao.objects.create(
                        produto    = componente.material,
                        local      = local,
                        tipo       = 'saida',
                        motivo     = 'venda',
                        quantidade = qtd_necessaria,
                        observacao = f'Uso de estoque — Pedido {pedido.numero} ({item.produto.nome})',
                        usuario    = usuario,
                    )
            except item.produto.__class__.ficha_tecnica.RelatedObjectDoesNotExist:
                Movimentacao.objects.create(
                    produto    = item.produto,
                    local      = local,
                    tipo       = 'saida',
                    motivo     = 'venda',
                    quantidade = item.quantidade,
                    observacao = f'Uso de estoque — Pedido {pedido.numero}',
                    usuario    = usuario,
                )


def reservar_estoque_parcial(pedido):
    """
    Chamada quando o pedido entra em AGUARD_PRODUCAO (ver Pedido.sync_status).
    Reserva automaticamente, item por item, o que já existir pronto no
    estoque — mesmo que só parte dos produtos do pedido esteja disponível.
    O restante segue o fluxo normal de corte/montagem.

    Usa pedido.criado_por como responsável pelas movimentações automáticas,
    já que não há um usuário confirmando essa ação manualmente.
    """
    itens_status, tudo_ok, local = _verificar_estoque_pedido(pedido)

    if not any(s['ok'] for s in itens_status):
        return  # nada disponível ainda — segue fluxo normal, sem chamadas extras

    with transaction.atomic():
        _processar_uso_estoque(pedido, local, pedido.criado_por, itens_status=itens_status)

        pedido.refresh_from_db()
        if tudo_ok and pedido.itens.exists():
            pedido.status = Pedido.Status.PICKING
            pedido.save(update_fields=['status', 'atualizado_em'])


@logistica_ou_gerente
def logistica_list(request):

    if request.method == 'POST':
        action    = request.POST.get('action', 'usar_estoque')
        pedido_pk = request.POST.get('pedido_pk')

        # ── Usar estoque — insumos/peças avulsas aguardando produção ──
        if action == 'usar_estoque':
            pedido = get_object_or_404(Pedido, pk=pedido_pk, status=Pedido.Status.AGUARD_PRODUCAO)
            _, tudo_ok, local = _verificar_estoque_pedido(pedido)

            if tudo_ok:
                with transaction.atomic():
                    _processar_uso_estoque(pedido, local, request.user)
                    pedido.status = Pedido.Status.PICKING
                    pedido.save(update_fields=['status', 'atualizado_em'])
                messages.success(request, f'Pedido {pedido.numero} enviado para separação!')
            else:
                messages.error(request, f'Estoque insuficiente para o pedido {pedido.numero}.')

        # ── Separar insumos ──
        elif action == 'separar_insumos':
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
        info = {
            'pedido':        pedido,
            'is_retirada':   pedido.transportadora == 'Retirada na Loja',
            'total':         pedido.status_separacao['total'],
            'separadas':     pedido.status_separacao['separadas'],
            'tudo_separado': pedido.status_separacao['tudo_separado'],
            'todos_insumos': _todos_insumos(pedido),
        }

        if info['tudo_separado']:
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