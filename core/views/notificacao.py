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


def _pedidos_nao_lidos(user, tipo, queryset):
    """Filtra um queryset de Pedido, removendo os que o usuário já marcou como lidos para esse tipo."""
    lidos = _pedidos_lidos(user, tipo)
    return queryset.exclude(pk__in=lidos).select_related('cliente')


def _pode_ver(user, grupos, *nomes_grupos):
    return user.is_staff or any(nome in grupos for nome in nomes_grupos)


def _notificacao_pagamento_pendente(user, grupos):
    if not _pode_ver(user, grupos, 'Financeiro', 'Gerente'):
        return []

    pedidos = _pedidos_nao_lidos(
        user, 'pagamento_pendente',
        Pedido.objects.filter(status__in=['open', 'aguard_pagamento']).exclude(status='canceled'),
    )

    return [
        {
            'tipo':      'pagamento_pendente',
            'label':     'Pagamento pendente',
            'pedido':    pedido.numero,
            'cliente':   pedido.cliente.nome,
            'url':       f'/vendas/{pedido.pk}/',
            'pedido_pk': pedido.pk,
        }
        for pedido in pedidos
        if pedido.saldo_restante > 0
    ]


def _notificacao_pedido_aberto(user, grupos):
    if not _pode_ver(user, grupos, 'Vendedor'):
        return []

    pedidos = _pedidos_nao_lidos(
        user, 'pedido_aberto',
        Pedido.objects.filter(status='open', criado_por=user),
    )

    return [
        {
            'tipo':      'pedido_aberto',
            'label':     'Pedido em aberto',
            'pedido':    pedido.numero,
            'cliente':   pedido.cliente.nome,
            'url':       f'/vendas/{pedido.pk}/',
            'pedido_pk': pedido.pk,
        }
        for pedido in pedidos
    ]


def _notificacao_aguardando_corte(user, grupos):
    """Avisa o laser só quando o pedido realmente precisa de corte —
    se já dá pra atender inteiramente pelo estoque, quem é avisado é a
    logística (ver _notificacao_estoque_disponivel), não o laser."""
    if not _pode_ver(user, grupos, 'Operador de Laser', 'Supervisor de Laser', 'Gerente'):
        return []

    from vendas.views.logistica import _todos_insumos

    pedidos = _pedidos_nao_lidos(
        user, 'aguard_producao',
        Pedido.objects.filter(status='aguard_producao'),
    )

    return [
        {
            'tipo':      'aguard_producao',
            'label':     'Aguardando corte',
            'pedido':    pedido.numero,
            'cliente':   pedido.cliente.nome,
            'url':       '/vendas/laser/',
            'pedido_pk': pedido.pk,
        }
        for pedido in pedidos
        if not _todos_insumos(pedido)
    ]


def _notificacao_estoque_disponivel(user, grupos):
    """Avisa a logística quando um pedido aguardando produção já pode ser
    atendido inteiramente pelo estoque (peça avulsa pronta ou insumo em
    estoque), sem precisar passar por corte/montagem."""
    if not _pode_ver(user, grupos, 'Logística', 'Logistica Loja', 'Gerente'):
        return []

    from vendas.views.logistica import _todos_insumos

    pedidos = _pedidos_nao_lidos(
        user, 'estoque_disponivel',
        Pedido.objects.filter(status='aguard_producao'),
    )

    return [
        {
            'tipo':      'estoque_disponivel',
            'label':     'Estoque disponível para este pedido',
            'pedido':    pedido.numero,
            'cliente':   pedido.cliente.nome,
            'url':       '/vendas/logistica/',
            'pedido_pk': pedido.pk,
        }
        for pedido in pedidos
        if _todos_insumos(pedido)
    ]


def _notificacao_aguardando_montagem(user, grupos):
    """
    Lê notificações já persistidas (criadas no momento em que o pedido entrou
    em 'assembling'), em vez de recalcular pelo status atual do pedido. Isso
    evita perder o alerta quando a montagem é rápida e o pedido já muda para
    'picking' antes de alguém ver a notificação.
    """
    if not _pode_ver(user, grupos, 'Operador de Montagem', 'Supervisor de Montagem', 'Gerente'):
        return []

    pendentes = Notificacao.objects.filter(
        destinatario=user,
        tipo='aguard_montagem',
        lida=False,
    ).select_related('pedido__cliente')

    return [
        {
            'tipo':      'aguard_montagem',
            'label':     'Aguardando montagem',
            'pedido':    n.pedido.numero,
            'cliente':   n.pedido.cliente.nome,
            'url':       '/vendas/montagem/',
            'pedido_pk': n.pedido.pk,
        }
        for n in pendentes
    ]


def _notificacao_pedido_cancelado(user, grupos):
    if not _pode_ver(user, grupos, 'Financeiro', 'Gerente'):
        return []

    pedidos = _pedidos_nao_lidos(
        user, 'pedido_cancelado',
        Pedido.objects.filter(status='canceled').select_related('cancelado_por'),
    )

    resultado = []
    for pedido in pedidos:
        cancelado_por = pedido.cancelado_por
        nome = (cancelado_por.get_full_name() or cancelado_por.username) if cancelado_por else '—'
        resultado.append({
            'tipo':      'pedido_cancelado',
            'label':     f'Cancelado por {nome}',
            'pedido':    pedido.numero,
            'cliente':   pedido.cliente.nome,
            'url':       f'/vendas/{pedido.pk}/',
            'pedido_pk': pedido.pk,
        })
    return resultado


def _notificacao_pronto_para_envio(user, grupos):
    """Dispara só quando o pedido em picking já está com tudo separado."""
    if not _pode_ver(user, grupos, 'Financeiro', 'Gerente', 'Logistica Loja'):
        return []

    pedidos = _pedidos_nao_lidos(user, 'picking', Pedido.objects.filter(status='picking'))

    return [
        {
            'tipo':      'picking',
            'label':     'Pronto para envio — imprimir ficha',
            'pedido':    pedido.numero,
            'cliente':   pedido.cliente.nome,
            'url':       f'/vendas/{pedido.pk}/',
            'pedido_pk': pedido.pk,
        }
        for pedido in pedidos
        if pedido.status_separacao['tudo_separado']
    ]


def _notificacao_aguardando_separacao(user, grupos):
    """Dispara só enquanto o pedido em picking ainda tiver algo pendente de separar."""
    if not _pode_ver(user, grupos, 'Logística', 'Gerente'):
        return []

    pedidos = _pedidos_nao_lidos(user, 'picking', Pedido.objects.filter(status='picking'))

    return [
        {
            'tipo':      'picking',
            'label':     'Produtos aguardando separação',
            'pedido':    pedido.numero,
            'cliente':   pedido.cliente.nome,
            'url':       '/vendas/logistica/',
            'pedido_pk': pedido.pk,
        }
        for pedido in pedidos
        if not pedido.status_separacao['tudo_separado']
    ]


def _gerar_notificacoes(user):
    grupos = _grupos(user)

    blocos = [
        _notificacao_pagamento_pendente,
        _notificacao_pedido_aberto,
        _notificacao_aguardando_corte,
        _notificacao_estoque_disponivel,
        _notificacao_aguardando_montagem,
        _notificacao_pedido_cancelado,
        _notificacao_pronto_para_envio,
        _notificacao_aguardando_separacao,
    ]

    notificacoes = []
    for bloco in blocos:
        notificacoes.extend(bloco(user, grupos))
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
            # .update() funciona com 0, 1 ou vários registros encontrados —
            # diferente de update_or_create (que usa .get() internamente e
            # quebra com MultipleObjectsReturned se houver duplicatas).
            atualizados = Notificacao.objects.filter(
                destinatario=request.user,
                pedido=pedido,
                tipo=tipo,
            ).update(lida=True)

            # Se não existia nenhum registro (tipos "ao vivo", sem persistência
            # prévia), cria um novo já marcado como lido.
            if atualizados == 0:
                Notificacao.objects.create(
                    destinatario=request.user,
                    pedido=pedido,
                    tipo=tipo,
                    lida=True,
                )

    return JsonResponse({'ok': True})