from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from clientes.models import Cliente
from core.mixins import acesso_vendas, financeiro_ou_gerente, vendedor_ou_gerente
from core.models import Local
from movimentacoes.models import Movimentacao
from produtos.models import Produto
from vendas.models import Pedido, ItemPedido


def _parse_decimal(val, default='0'):
    try:
        return Decimal(
            (val or default)
            .replace('.', '')
            .replace(',', '.')
        )
    except Exception:
        return Decimal(default)


def _serializar_itens(pedido):
    return [
        {
            'pk':         item.pk,
            'nome':       item.produto.nome,
            'quantidade': item.quantidade,
            'preco':      float(item.preco_unitario),
            'subtotal':   float(item.subtotal),
        }
        for item in pedido.itens.select_related('produto').all()
    ]


def _serializar_totais(pedido):
    return {
        'total_produtos': float(pedido.total_produtos),
        'total_desconto': float(pedido.total_desconto),
        'total_impostos': float(pedido.total_impostos),
        'frete':          float(pedido.frete),
        'total_geral':    float(pedido.total_geral),
        'total_pago':     float(pedido.total_pago),
        'saldo_restante': float(pedido.saldo_restante),
    }


def _recalcular_total_geral(pedido):
    total = (
        pedido.total_produtos
        - pedido.total_desconto
        + pedido.total_impostos
        + pedido.frete
    )
    pedido.total_geral = max(Decimal('0'), total)
    pedido.save(update_fields=['total_geral', 'atualizado_em'])


def _baixar_estoque_pedido(pedido, user):
    """Registra saída de estoque quando pedido é enviado/entregue."""
    local = pedido.local_saida
    if not local:
        local = Local.objects.filter(tipo='fabrica').first()
    if not local:
        return

    fabrica = Local.objects.filter(tipo='fabrica').first()

    for item in pedido.itens.select_related('produto').all():
        try:
            ficha = item.produto.ficha_tecnica
            for componente in ficha.itens.select_related('material').all():
                quantidade_total = componente.quantidade * item.quantidade
                # Usa local_saida se tiver estoque suficiente, senão usa fábrica
                from estoque.models import Estoque
                saldo = Estoque.objects.filter(produto=componente.material, local=local).first()
                local_usar = local if saldo and saldo.quantidade >= quantidade_total else fabrica
                Movimentacao.objects.create(
                    produto    = componente.material,
                    local      = local_usar,
                    tipo       = Movimentacao.TIPO_SAIDA,
                    motivo     = 'venda',
                    quantidade = quantidade_total,
                    observacao = f'Separação — Pedido {pedido.numero} ({item.produto.nome})',
                    usuario    = user,
                )
        except item.produto.__class__.ficha_tecnica.RelatedObjectDoesNotExist:
            from estoque.models import Estoque
            saldo = Estoque.objects.filter(produto=item.produto, local=local).first()
            local_usar = local if saldo and saldo.quantidade >= item.quantidade else fabrica
            Movimentacao.objects.create(
                produto    = item.produto,
                local      = local_usar,
                tipo       = Movimentacao.TIPO_SAIDA,
                motivo     = 'venda',
                quantidade = item.quantidade,
                observacao = f'Separação — Pedido {pedido.numero}',
                usuario    = user,
            )

def _estornar_estoque_pedido(pedido, user):
    """Estorna saída de estoque ao cancelar pedido em picking/shipped/delivered."""
    local = pedido.local_saida
    if not local:
        local = Local.objects.filter(tipo='fabrica').first()
    if not local:
        return

    for item in pedido.itens.select_related('produto').all():
        Movimentacao.objects.create(
            produto    = item.produto,
            local      = local,
            tipo       = Movimentacao.TIPO_ENTRADA,
            motivo     = 'uso_interno',
            quantidade = item.quantidade,
            observacao = f'Estorno — Pedido {pedido.numero} cancelado',
            usuario    = user,
        )


TRANSPORTADORA_CHOICES = [
    'Contratação Remetente - CIF',
    'Contratação Destinatário - FOB',
    'Envio pela Decorcril',
    'Retirada na Loja',
]


@acesso_vendas
def pedido_list(request):
    q           = request.GET.get('q', '')
    status      = request.GET.get('status', '')
    pendentes   = request.GET.get('pendentes', '')
    transacao   = request.GET.get('transacao', '')
    tipo_venda  = request.GET.get('tipo_venda', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim    = request.GET.get('data_fim', '')

    pedidos = Pedido.objects.select_related('cliente', 'criado_por').all()

    if tipo_venda:
        pedidos = pedidos.filter(tipo_venda=tipo_venda)

    if not request.user.is_staff:
        grupos = request.user.groups.values_list('name', flat=True)
        if 'Vendedor' in grupos and 'Financeiro' not in grupos and 'Gerente' not in grupos:
            pedidos = pedidos.filter(criado_por=request.user)

    if q:
        pedidos = pedidos.filter(
            Q(numero__icontains=q) | Q(cliente__nome__icontains=q)
        )

    if status:
        pedidos = pedidos.filter(status=status)

    if data_inicio:
        pedidos = pedidos.filter(criado_em__date__gte=data_inicio)

    if data_fim:
        pedidos = pedidos.filter(criado_em__date__lte=data_fim)

    if pendentes == '1':
        pedidos = pedidos.annotate(
            total_pago_ann=Coalesce(Sum('pagamentos__valor'), Decimal('0.00'))
        ).filter(
            total_pago_ann__lt=F('total_geral')
        ).exclude(status='canceled')

    if transacao:
        from vendas.models.pagamento import Pagamento
        pedido_ids = Pagamento.objects.filter(
            transacao__icontains=transacao
        ).values_list('pedido_id', flat=True)
        pedidos = pedidos.filter(pk__in=pedido_ids)

    paginator = Paginator(pedidos, 20)
    pedidos   = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'vendas/pedido_list.html', {
        'pedidos':            pedidos,
        'q':                  q,
        'status':             status,
        'pendentes':          pendentes,
        'transacao':          transacao,
        'tipo_venda':         tipo_venda,
        'data_inicio':        data_inicio,
        'data_fim':           data_fim,
        'status_choices':     Pedido.Status.choices,
        'tipo_venda_choices': Pedido.TipoVenda.choices,
    })


@vendedor_ou_gerente
def pedido_create(request):
    if request.method == 'POST':
        import json

        cliente_id           = request.POST.get('cliente')
        tipo_venda           = request.POST.get('tipo_venda')
        condicao_pagamento   = request.POST.get('condicao_pagamento', '')
        contato              = request.POST.get('contato', '')
        transportadora       = request.POST.get('transportadora', '')
        local_saida_id       = request.POST.get('local_saida', '') or None
        frete                = _parse_decimal(request.POST.get('frete', '0'))
        percentual_entrada   = _parse_decimal(request.POST.get('percentual_entrada', '0'))
        total_desconto       = _parse_decimal(request.POST.get('total_desconto', '0'))
        observacoes          = request.POST.get('observacoes', '')
        observacoes_internas = request.POST.get('observacoes_internas', '')
        items_json           = request.POST.get('items_json', '[]')

        if not cliente_id:
            messages.error(request, 'Selecione um cliente.')
        elif not tipo_venda:
            messages.error(request, 'Selecione o tipo de venda.')
        else:
            try:
                items = json.loads(items_json)
            except Exception:
                items = []

            if not items:
                messages.error(request, 'Adicione pelo menos um produto ao pedido.')
            else:
                cliente     = get_object_or_404(Cliente, pk=cliente_id)
                local_saida = Local.objects.filter(pk=local_saida_id).first() if local_saida_id else None

                pedido = Pedido.objects.create(
                    cliente              = cliente,
                    tipo_venda           = tipo_venda,
                    condicao_pagamento   = condicao_pagamento,
                    contato              = contato,
                    transportadora       = transportadora,
                    local_saida          = local_saida,
                    frete                = frete,
                    percentual_entrada   = percentual_entrada,
                    total_desconto       = total_desconto,
                    observacoes          = observacoes,
                    observacoes_internas = observacoes_internas,
                    criado_por           = request.user,
                )
                for item in items:
                    ItemPedido.objects.create(
                        pedido         = pedido,
                        produto_id     = item['id'],
                        quantidade     = item['quantidade'],
                        preco_unitario = Decimal(str(item['preco'])),
                    )
                pedido.sync_status()
                messages.success(request, f'Pedido {pedido.numero} criado com sucesso!')
                return redirect('vendas:pedido_detail', pk=pedido.pk)

    locais = Local.objects.all().order_by('nome')
    return render(request, 'vendas/pedido_form.html', {
        'titulo':                 'Novo Pedido',
        'tipo_venda_choices':     Pedido.TipoVenda.choices,
        'transportadora_choices': TRANSPORTADORA_CHOICES,
        'locais':                 locais,
    })


@acesso_vendas
def pedido_detail(request, pk):
    from vendas.models import UnidadePedido

    pedido = get_object_or_404(
        Pedido.objects.select_related('cliente', 'criado_por', 'responsavel', 'local_saida')
                      .prefetch_related('itens__produto', 'pagamentos'),
        pk=pk
    )

    if not request.user.is_staff:
        grupos = request.user.groups.values_list('name', flat=True)
        if 'Vendedor' in grupos and 'Financeiro' not in grupos and 'Gerente' not in grupos:
            if pedido.criado_por != request.user:
                raise PermissionDenied

    # ── Progresso de separação ──
    total_unidades     = UnidadePedido.objects.filter(item__pedido=pedido).count()
    separadas          = UnidadePedido.objects.filter(item__pedido=pedido, separada=True).count()
    tudo_separado      = total_unidades > 0 and separadas >= total_unidades

    return render(request, 'vendas/pedido_detail.html', {
        'pedido':          pedido,
        'status_choices':  Pedido.Status.choices,
        'total_unidades':  total_unidades,
        'separadas':       separadas,
        'tudo_separado':   tudo_separado,
    })


@vendedor_ou_gerente
def pedido_edit(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)

    if not request.user.is_staff:
        grupos = request.user.groups.values_list('name', flat=True)
        if 'Gerente' not in grupos:
            if pedido.criado_por != request.user:
                raise PermissionDenied
            if pedido.status != Pedido.Status.OPEN:
                messages.error(request, 'Só é possível editar pedidos em aberto.')
                return redirect('vendas:pedido_detail', pk=pedido.pk)

    if request.method == 'POST':
        local_saida_id = request.POST.get('local_saida', '') or None
        local_saida    = Local.objects.filter(pk=local_saida_id).first() if local_saida_id else None

        pedido.tipo_venda           = request.POST.get('tipo_venda', pedido.tipo_venda)
        pedido.condicao_pagamento   = request.POST.get('condicao_pagamento', '')
        pedido.contato              = request.POST.get('contato', '')
        pedido.transportadora       = request.POST.get('transportadora', '')
        pedido.local_saida          = local_saida
        pedido.frete                = _parse_decimal(request.POST.get('frete', '0'))
        pedido.percentual_entrada   = _parse_decimal(request.POST.get('percentual_entrada', '0'))
        pedido.total_desconto       = _parse_decimal(request.POST.get('total_desconto', '0'))
        pedido.observacoes          = request.POST.get('observacoes', '')
        pedido.observacoes_internas = request.POST.get('observacoes_internas', '')
        pedido.save()
        _recalcular_total_geral(pedido)
        messages.success(request, f'Pedido {pedido.numero} atualizado!')
        return redirect('vendas:pedido_detail', pk=pedido.pk)

    locais = Local.objects.all().order_by('nome')
    return render(request, 'vendas/pedido_edit_form.html', {
        'titulo':                 f'Editar Pedido {pedido.numero}',
        'pedido':                 pedido,
        'tipo_venda_choices':     Pedido.TipoVenda.choices,
        'transportadora_choices': TRANSPORTADORA_CHOICES,
        'locais':                 locais,
    })


@acesso_vendas
def pedido_status(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)

    if request.method == 'POST':
        novo_status = request.POST.get('status')

        # ── Cancelamento ──
        if novo_status == 'canceled':
            grupos = request.user.groups.values_list('name', flat=True)
            pode_cancelar = (
                request.user.is_staff or
                'Gerente' in grupos or
                'Financeiro' in grupos or
                pedido.criado_por == request.user
            )
            if not pode_cancelar:
                messages.error(request, 'Você não tem permissão para cancelar este pedido.')
                return redirect('vendas:pedido_detail', pk=pedido.pk)

            motivo = request.POST.get('motivo_cancelamento', '').strip()
            if not motivo:
                messages.error(request, 'Informe o motivo do cancelamento.')
                return redirect('vendas:pedido_detail', pk=pedido.pk)

            # Estorna estoque se já estava em shipped ou delivered
            if pedido.status in [
                Pedido.Status.SHIPPED,
                Pedido.Status.DELIVERED,
            ]:
                _estornar_estoque_pedido(pedido, request.user)

            pedido.status              = Pedido.Status.CANCELED
            pedido.cancelado_por       = request.user
            pedido.motivo_cancelamento = motivo
            pedido.cancelado_em        = timezone.now()
            pedido.save(update_fields=[
                'status', 'cancelado_por', 'motivo_cancelamento',
                'cancelado_em', 'atualizado_em'
            ])

            from core.models.notificacao import Notificacao
            Notificacao.objects.filter(pedido=pedido, tipo='pedido_cancelado').delete()
            messages.success(request, f'Pedido {pedido.numero} cancelado.')
            return redirect('vendas:pedido_detail', pk=pedido.pk)

        if novo_status in dict(Pedido.Status.choices):

            # ── Reabrir pedido cancelado ──
            if pedido.status == Pedido.Status.CANCELED:
                from core.models.notificacao import Notificacao
                pedido.cancelado_por       = None
                pedido.motivo_cancelamento = ''
                pedido.cancelado_em        = None
                pedido.status              = novo_status
                pedido.save(update_fields=[
                    'status', 'cancelado_por', 'motivo_cancelamento',
                    'cancelado_em', 'atualizado_em'
                ])
                Notificacao.objects.filter(pedido=pedido, tipo='pedido_cancelado').delete()
                messages.success(request, f'Status atualizado para {pedido.get_status_display()}.')
                return redirect('vendas:pedido_detail', pk=pedido.pk)

            # ── Picking — só muda status, sem baixar estoque ──
            if novo_status == 'picking':
                if pedido.status != Pedido.Status.ASSEMBLING:
                    messages.error(request, 'O pedido precisa estar em montagem para ir para separação.')
                    return redirect('vendas:pedido_detail', pk=pedido.pk)

                pedido.status = Pedido.Status.PICKING
                pedido.save(update_fields=['status', 'atualizado_em'])
                messages.success(request, f'Pedido {pedido.numero} em separação.')
                return redirect('vendas:pedido_detail', pk=pedido.pk)

            # ── Envio / Entrega — baixa estoque ──
            if novo_status in ['shipped', 'delivered']:
                if pedido.status != Pedido.Status.PICKING:
                    messages.error(request, 'O pedido precisa estar em separação para ser enviado ou entregue.')
                    return redirect('vendas:pedido_detail', pk=pedido.pk)

                if pedido.saldo_restante > 0 and not pedido.is_free_sale:
                    messages.error(
                        request,
                        f'Não é possível enviar o pedido com saldo pendente de {pedido.saldo_restante}. '
                        f'Quite o pagamento antes de prosseguir.'
                    )
                    return redirect('vendas:pedido_detail', pk=pedido.pk)

                if novo_status == 'shipped' and pedido.transportadora == 'Retirada na Loja':
                    novo_status = 'delivered'
                    messages.success(request, f'Pedido {pedido.numero} marcado como entregue (retirada na loja).')
                else:
                    messages.success(request, f'Status atualizado para {pedido.get_status_display()}.')

                pedido.status = novo_status
                pedido.save(update_fields=['status', 'atualizado_em'])
                _baixar_estoque_pedido(pedido, request.user)
                return redirect('vendas:pedido_detail', pk=pedido.pk)

            # ── Status normal ──
            pedido.status = novo_status
            pedido.save(update_fields=['status', 'atualizado_em'])
            messages.success(request, f'Status atualizado para {pedido.get_status_display()}.')

        else:
            messages.error(request, 'Status inválido.')

    return redirect('vendas:pedido_detail', pk=pedido.pk)


@acesso_vendas
def item_remove(request, pk, item_pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    item   = get_object_or_404(ItemPedido, pk=item_pk, pedido=pedido)

    if request.method == 'POST':
        item.delete()
        pedido.refresh_from_db()
        return JsonResponse({
            'ok':    True,
            'itens': _serializar_itens(pedido),
            'totais': _serializar_totais(pedido),
        })

    return JsonResponse({'ok': False})


@acesso_vendas
def item_update(request, pk, item_pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    item   = get_object_or_404(ItemPedido, pk=item_pk, pedido=pedido)

    if request.method == 'POST':
        quantidade = max(1, int(request.POST.get('quantidade', 1)))
        item.quantidade = quantidade

        preco_unitario = request.POST.get('preco_unitario')
        if preco_unitario is not None:
            item.preco_unitario = Decimal(preco_unitario)

        item.save()
        pedido.refresh_from_db()
        return JsonResponse({
            'ok':    True,
            'itens': _serializar_itens(pedido),
            'totais': _serializar_totais(pedido),
        })

    return JsonResponse({'ok': False})


@acesso_vendas
def item_add(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)

    if request.method == 'POST':
        produto_id     = request.POST.get('produto')
        quantidade     = int(request.POST.get('quantidade', 1))
        preco_unitario = Decimal(request.POST.get('preco_unitario', '0'))
        produto        = get_object_or_404(Produto, pk=produto_id)

        item_existente = pedido.itens.filter(produto=produto).first()
        if item_existente:
            item_existente.quantidade += quantidade
            item_existente.save()
        else:
            ItemPedido.objects.create(
                pedido         = pedido,
                produto        = produto,
                quantidade     = quantidade,
                preco_unitario = preco_unitario,
            )

        pedido.refresh_from_db()
        return JsonResponse({
            'ok':    True,
            'itens': _serializar_itens(pedido),
            'totais': _serializar_totais(pedido),
        })

    return JsonResponse({'ok': False})