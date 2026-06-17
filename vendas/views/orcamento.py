import json
from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from clientes.models import Cliente
from core.mixins import vendedor_ou_gerente
from vendas.models import Pedido, ItemPedido
from vendas.models.orcamento import Orcamento, ItemOrcamento


TRANSPORTADORA_CHOICES = [
    'Contratação Remetente - CIF',
    'Contratação Destinatário - FOB',
    'Envio pela Decorcril',
    'Retirada na Loja',
]


@vendedor_ou_gerente
def orcamento_list(request):
    q      = request.GET.get('q', '')
    status = request.GET.get('status', '')

    orcamentos = Orcamento.objects.select_related('cliente', 'criado_por').all()

    if not request.user.is_staff:
        grupos = request.user.groups.values_list('name', flat=True)
        if 'Vendedor' in grupos and 'Gerente' not in grupos:
            orcamentos = orcamentos.filter(criado_por=request.user)

    if q:
        orcamentos = orcamentos.filter(
            Q(numero__icontains=q) |
            Q(cliente__nome__icontains=q)
        )

    if status:
        orcamentos = orcamentos.filter(status=status)

    # Marca expirados automaticamente
    Orcamento.objects.filter(
        status='draft',
        validade__lt=timezone.now().date()
    ).update(status='expired')

    paginator  = Paginator(orcamentos, 20)
    page       = request.GET.get('page', 1)
    orcamentos = paginator.get_page(page)

    return render(request, 'vendas/orcamento_list.html', {
        'orcamentos':     orcamentos,
        'q':              q,
        'status':         status,
        'status_choices': Orcamento.Status.choices,
    })


@vendedor_ou_gerente
def orcamento_create(request):
    if request.method == 'POST':
        cliente_id           = request.POST.get('cliente')
        tipo_venda           = request.POST.get('tipo_venda')
        condicao_pagamento   = request.POST.get('condicao_pagamento', '')
        contato              = request.POST.get('contato', '')
        percentual_entrada   = request.POST.get('percentual_entrada', '0') or '0'
        total_desconto       = request.POST.get('total_desconto', '0').replace('.', '').replace(',', '.') or '0'
        observacoes          = request.POST.get('observacoes', '')
        observacoes_internas = request.POST.get('observacoes_internas', '')
        items_json           = request.POST.get('items_json', '[]')

        # Transportadora — Melhor Envio tem prioridade sobre o select
        transportadora = request.POST.get('transportadora_frete') or request.POST.get('transportadora', '')

        # Frete vem com máscara: "200,00" → "200.00"
        try:
            frete = Decimal(
                request.POST.get('frete', '0').replace('.', '').replace(',', '.') or '0'
            )
        except Exception:
            frete = Decimal('0')

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
                messages.error(request, 'Adicione pelo menos um produto ao orçamento.')
            else:
                cliente   = get_object_or_404(Cliente, pk=cliente_id)
                orcamento = Orcamento.objects.create(
                    cliente              = cliente,
                    tipo_venda           = tipo_venda,
                    condicao_pagamento   = condicao_pagamento,
                    contato              = contato,
                    transportadora       = transportadora,
                    frete                = frete,
                    percentual_entrada   = Decimal(percentual_entrada),
                    total_desconto       = Decimal(total_desconto),
                    observacoes          = observacoes,
                    observacoes_internas = observacoes_internas,
                    criado_por           = request.user,
                )
                for item in items:
                    ItemOrcamento.objects.create(
                        orcamento      = orcamento,
                        produto_id     = item['id'],
                        quantidade     = item['quantidade'],
                        preco_unitario = Decimal(str(item['preco'])),
                    )
                messages.success(request, f'Orçamento {orcamento.numero} criado com sucesso!')
                return redirect('vendas:orcamento_detail', pk=orcamento.pk)

    return render(request, 'vendas/orcamento_form.html', {
        'titulo':                 'Novo Orçamento',
        'tipo_venda_choices':     Orcamento._meta.get_field('tipo_venda').choices,
        'transportadora_choices': TRANSPORTADORA_CHOICES,
    })


@vendedor_ou_gerente
def orcamento_detail(request, pk):
    orcamento = get_object_or_404(
        Orcamento.objects.select_related('cliente', 'criado_por')
                         .prefetch_related('itens__produto'),
        pk=pk
    )
    return render(request, 'vendas/orcamento_detail.html', {
        'orcamento': orcamento,
    })


@vendedor_ou_gerente
def orcamento_aprovar(request, pk):
    orcamento = get_object_or_404(Orcamento, pk=pk)

    if orcamento.status != Orcamento.Status.DRAFT:
        messages.error(request, 'Só é possível aprovar orçamentos em elaboração.')
        return redirect('vendas:orcamento_detail', pk=orcamento.pk)

    if orcamento.expirado:
        orcamento.status = Orcamento.Status.EXPIRED
        orcamento.save()
        messages.error(request, 'Este orçamento está expirado.')
        return redirect('vendas:orcamento_detail', pk=orcamento.pk)

    if request.method == 'POST':
        pedido = Pedido.objects.create(
            cliente              = orcamento.cliente,
            tipo_venda           = orcamento.tipo_venda,
            condicao_pagamento   = orcamento.condicao_pagamento,
            contato              = orcamento.contato,
            transportadora       = orcamento.transportadora,
            frete                = orcamento.frete,
            percentual_entrada   = orcamento.percentual_entrada,
            total_desconto       = orcamento.total_desconto,
            observacoes          = orcamento.observacoes,
            observacoes_internas = orcamento.observacoes_internas,
            criado_por           = orcamento.criado_por,
        )
        for item in orcamento.itens.all():
            ItemPedido.objects.create(
                pedido         = pedido,
                produto        = item.produto,
                quantidade     = item.quantidade,
                preco_unitario = item.preco_unitario,
            )

        orcamento.status = Orcamento.Status.APPROVED
        orcamento.pedido = pedido
        orcamento.save()

        messages.success(request, f'Orçamento aprovado! Pedido {pedido.numero} criado.')
        return redirect('vendas:pedido_detail', pk=pedido.pk)

    return redirect('vendas:orcamento_detail', pk=orcamento.pk)


@vendedor_ou_gerente
def orcamento_rejeitar(request, pk):
    orcamento = get_object_or_404(Orcamento, pk=pk)

    if orcamento.status != Orcamento.Status.DRAFT:
        messages.error(request, 'Só é possível rejeitar orçamentos em elaboração.')
        return redirect('vendas:orcamento_detail', pk=orcamento.pk)

    if request.method == 'POST':
        orcamento.status = Orcamento.Status.REJECTED
        orcamento.save()
        messages.success(request, f'Orçamento {orcamento.numero} rejeitado.')
        return redirect('vendas:orcamento_list')

    return redirect('vendas:orcamento_detail', pk=orcamento.pk)