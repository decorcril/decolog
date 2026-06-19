from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q, Sum, F
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from clientes.models import Cliente
from core.mixins import acesso_vendas, financeiro_ou_gerente, vendedor_ou_gerente
from produtos.models import Produto
from vendas.models import Pedido, ItemPedido


@acesso_vendas
def pedido_list(request):
    q         = request.GET.get('q', '')
    status    = request.GET.get('status', '')
    pendentes = request.GET.get('pendentes', '')
    transacao = request.GET.get('transacao', '')

    pedidos = Pedido.objects.select_related('cliente', 'criado_por').all()

    tipo_venda = request.GET.get('tipo_venda', '')

    if tipo_venda:
        pedidos = pedidos.filter(tipo_venda=tipo_venda)

    if not request.user.is_staff:
        grupos = request.user.groups.values_list('name', flat=True)
        if 'Vendedor' in grupos and 'Financeiro' not in grupos and 'Gerente' not in grupos:
            pedidos = pedidos.filter(criado_por=request.user)

    if q:
        pedidos = pedidos.filter(
            Q(numero__icontains=q) |
            Q(cliente__nome__icontains=q)
        )

    if status:
        pedidos = pedidos.filter(status=status)

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
    page      = request.GET.get('page', 1)
    pedidos   = paginator.get_page(page)

    return render(request, 'vendas/pedido_list.html', {
        'pedidos':        pedidos,
        'q':              q,
        'status':         status,
        'pendentes':      pendentes,
        'transacao':      transacao,
        'status_choices': Pedido.Status.choices,
        'tipo_venda':        tipo_venda,
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
        frete                = request.POST.get('frete', '0').replace('.', '').replace(',', '.') or '0'
        percentual_entrada   = request.POST.get('percentual_entrada', '0') or '0'
        total_desconto       = request.POST.get('total_desconto', '0').replace('.', '').replace(',', '.') or '0'
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
                cliente = get_object_or_404(Cliente, pk=cliente_id)
                pedido  = Pedido.objects.create(
                    cliente              = cliente,
                    tipo_venda           = tipo_venda,
                    condicao_pagamento   = condicao_pagamento,
                    contato              = contato,
                    transportadora       = transportadora,
                    frete                = Decimal(frete),
                    percentual_entrada   = Decimal(percentual_entrada),
                    total_desconto       = Decimal(total_desconto),
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

    TRANSPORTADORA_CHOICES = [
        'Contratação Remetente - CIF',
        'Contratação Destinatário - FOB',
        'Envio pela Decorcril',
        'Retirada na Loja',
    ]

    return render(request, 'vendas/pedido_form.html', {
        'titulo':                 'Novo Pedido',
        'tipo_venda_choices':     Pedido.TipoVenda.choices,
        'transportadora_choices': TRANSPORTADORA_CHOICES,
    })


@acesso_vendas
def pedido_detail(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.select_related('cliente', 'criado_por', 'responsavel')
                      .prefetch_related('itens__produto', 'pagamentos'),
        pk=pk
    )

    if not request.user.is_staff:
        grupos = request.user.groups.values_list('name', flat=True)
        if 'Vendedor' in grupos and 'Financeiro' not in grupos and 'Gerente' not in grupos:
            if pedido.criado_por != request.user:
                raise PermissionDenied

    produtos = Produto.objects.filter(
        ativo=True, categoria='produto_final'
    ).select_related('preco').order_by('nome')

    return render(request, 'vendas/pedido_detail.html', {
        'pedido':         pedido,
        'produtos':       produtos,
        'status_choices': Pedido.Status.choices,
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
        frete          = request.POST.get('frete', '0').replace('.', '').replace(',', '.') or '0'
        total_desconto = request.POST.get('total_desconto', '0').replace('.', '').replace(',', '.') or '0'

        pedido.tipo_venda          = request.POST.get('tipo_venda', pedido.tipo_venda)
        pedido.condicao_pagamento  = request.POST.get('condicao_pagamento', '')
        pedido.contato             = request.POST.get('contato', '')
        pedido.transportadora      = request.POST.get('transportadora', '')
        pedido.frete               = Decimal(frete)
        pedido.percentual_entrada  = Decimal(request.POST.get('percentual_entrada', '0') or '0')
        pedido.total_desconto      = Decimal(total_desconto)
        pedido.observacoes         = request.POST.get('observacoes', '')
        pedido.observacoes_internas = request.POST.get('observacoes_internas', '')
        pedido.save()
        messages.success(request, f'Pedido {pedido.numero} atualizado!')
        return redirect('vendas:pedido_detail', pk=pedido.pk)

    TRANSPORTADORA_CHOICES = [
        'Contratação Remetente - CIF',
        'Contratação Destinatário - FOB',
        'Envio pela Decorcril',
        'Retirada na Loja',
    ]

    return render(request, 'vendas/pedido_edit_form.html', {
    'titulo':                 f'Editar Pedido {pedido.numero}',
    'pedido':                 pedido,
    'tipo_venda_choices':     Pedido.TipoVenda.choices,
    'transportadora_choices': TRANSPORTADORA_CHOICES,
    })


@acesso_vendas
def pedido_status(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)

    if request.method == 'POST':
        novo_status = request.POST.get('status')

        # Cancelamento — só vendedor do pedido, gerente ou admin
        if novo_status == 'canceled':
            grupos = request.user.groups.values_list('name', flat=True)
            pode_cancelar = (
                request.user.is_staff or
                'Gerente' in grupos or
                pedido.criado_por == request.user
            )
            if not pode_cancelar:
                messages.error(request, 'Você não tem permissão para cancelar este pedido.')
                return redirect('vendas:pedido_detail', pk=pedido.pk)

        if novo_status in dict(Pedido.Status.choices):
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
        quantidade = int(request.POST.get('quantidade', 1))
        if quantidade < 1:
            quantidade = 1
        item.quantidade = quantidade

        # Atualiza preço se enviado
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

@acesso_vendas
def item_add(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)

    if request.method == 'POST':
        produto_id     = request.POST.get('produto')
        quantidade     = int(request.POST.get('quantidade', 1))
        preco_unitario = Decimal(request.POST.get('preco_unitario', '0'))

        produto = get_object_or_404(Produto, pk=produto_id)

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