from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from core.models.notificacao import Notificacao
from vendas.models import Pedido


def _grupos(user):
    return set(user.groups.values_list('name', flat=True))


def _pedidos_lidos(user, tipo):
    return set(
        Notificacao.objects.filter(
            destinatario=user,
            tipo=tipo,
            lida=True,
        ).values_list('pedido_id', flat=True)
    )


def _gerar_notificacoes(user):
    grupos   = _grupos(user)
    is_staff = user.is_staff
    notificacoes = []

    # ── Financeiro / Gerente — pagamentos pendentes ──
    if is_staff or 'Financeiro' in grupos or 'Gerente' in grupos:
        lidos   = _pedidos_lidos(user, 'pagamento_pendente')
        pedidos = Pedido.objects.filter(
            status__in=['open', 'aguard_pagamento']
        ).exclude(status='canceled').exclude(pk__in=lidos).select_related('cliente')

        for pedido in pedidos:
            if pedido.saldo_restante > 0:
                notificacoes.append({
                    'tipo':      'pagamento_pendente',
                    'label':     'Pagamento pendente',
                    'pedido':    pedido.numero,
                    'cliente':   pedido.cliente.nome,
                    'url':       f'/vendas/{pedido.pk}/',
                    'pedido_pk': pedido.pk,
                })

    # ── Vendedor — seus pedidos em aberto ──
    if is_staff or 'Vendedor' in grupos:
        lidos   = _pedidos_lidos(user, 'pedido_aberto')
        pedidos = Pedido.objects.filter(
            status='open',
            criado_por=user,
        ).exclude(pk__in=lidos).select_related('cliente')

        for pedido in pedidos:
            notificacoes.append({
                'tipo':      'pedido_aberto',
                'label':     'Pedido em aberto',
                'pedido':    pedido.numero,
                'cliente':   pedido.cliente.nome,
                'url':       f'/vendas/{pedido.pk}/',
                'pedido_pk': pedido.pk,
            })

    # ── Laser — aguardando corte ──
    if is_staff or 'Operador de Laser' in grupos or 'Supervisor de Laser' in grupos or 'Gerente' in grupos:
        lidos   = _pedidos_lidos(user, 'aguard_producao')
        pedidos = Pedido.objects.filter(
            status='aguard_producao'
        ).exclude(pk__in=lidos).select_related('cliente')

        for pedido in pedidos:
            notificacoes.append({
                'tipo':      'aguard_producao',
                'label':     'Aguardando corte',
                'pedido':    pedido.numero,
                'cliente':   pedido.cliente.nome,
                'url':       '/vendas/laser/',
                'pedido_pk': pedido.pk,
            })

    # ── Montagem — aguardando montagem ──
    if is_staff or 'Operador de Montagem' in grupos or 'Supervisor de Montagem' in grupos or 'Gerente' in grupos:
        lidos   = _pedidos_lidos(user, 'aguard_montagem')
        pedidos = Pedido.objects.filter(
            status='assembling'
        ).exclude(pk__in=lidos).select_related('cliente')

        for pedido in pedidos:
            notificacoes.append({
                'tipo':      'aguard_montagem',
                'label':     'Aguardando montagem',
                'pedido':    pedido.numero,
                'cliente':   pedido.cliente.nome,
                'url':       '/vendas/montagem/',
                'pedido_pk': pedido.pk,
            })

    # ── Financeiro / Gerente — pedidos cancelados ──
    if is_staff or 'Financeiro' in grupos or 'Gerente' in grupos:
        lidos   = _pedidos_lidos(user, 'pedido_cancelado')
        pedidos = Pedido.objects.filter(
            status='canceled',
        ).exclude(pk__in=lidos).select_related('cliente', 'cancelado_por')

        for pedido in pedidos:
            notificacoes.append({
                'tipo':      'pedido_cancelado',
                'label':     f'Cancelado por {pedido.cancelado_por.get_full_name() or pedido.cancelado_por.username if pedido.cancelado_por else "—"}',
                'pedido':    pedido.numero,
                'cliente':   pedido.cliente.nome,
                'url':       f'/vendas/{pedido.pk}/',
                'pedido_pk': pedido.pk,
            })

    # ── Financeiro / Logística Loja — pedidos prontos para separação ──
    if is_staff or 'Financeiro' in grupos or 'Gerente' in grupos or 'Logistica Loja' in grupos:
        lidos   = _pedidos_lidos(user, 'picking')
        pedidos = Pedido.objects.filter(
            status='picking'
        ).exclude(pk__in=lidos).select_related('cliente')

        for pedido in pedidos:
            notificacoes.append({
                'tipo':      'picking',
                'label':     'Pronto para separação — imprimir ficha',
                'pedido':    pedido.numero,
                'cliente':   pedido.cliente.nome,
                'url':       f'/vendas/{pedido.pk}/',
                'pedido_pk': pedido.pk,
            })

    # ── Logística — produtos aguardando separação ──
    if is_staff or 'Logística' in grupos or 'Gerente' in grupos:
        lidos   = _pedidos_lidos(user, 'picking')
        pedidos = Pedido.objects.filter(
            status='picking',
        ).exclude(pk__in=lidos).select_related('cliente')

        for pedido in pedidos:
            notificacoes.append({
                'tipo':      'picking',
                'label':     'Produtos aguardando separação',
                'pedido':    pedido.numero,
                'cliente':   pedido.cliente.nome,
                'url':       '/vendas/logistica/',
                'pedido_pk': pedido.pk,
            })

    return notificacoes


@login_required
def notificacoes_lista(request):
    notificacoes = _gerar_notificacoes(request.user)
    return JsonResponse({
        'ok':    True,
        'total': len(notificacoes),
        'itens': notificacoes,
    })


@login_required
def notificacoes_marcar_lida(request, pedido_pk):
    if request.method == 'POST':
        pedido = get_object_or_404(Pedido, pk=pedido_pk)
        tipo   = request.POST.get('tipo')

        if tipo:
            Notificacao.objects.update_or_create(
                destinatario=request.user,
                pedido=pedido,
                tipo=tipo,
                defaults={'lida': True},
            )

    return JsonResponse({'ok': True})