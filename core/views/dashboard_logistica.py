from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta

from vendas.models import Pedido


@login_required
def dashboard_logistica(request):
    from vendas.views.logistica import _todos_insumos

    hoje   = timezone.localdate()
    semana = hoje - timedelta(days=hoje.weekday())

    pedidos_com_info = []

    # ── Pedidos já em separação (picking) ──
    pedidos_picking = Pedido.objects.filter(
        status='picking',
    ).select_related('cliente', 'criado_por').prefetch_related('itens__produto').order_by('criado_em')

    for pedido in pedidos_picking:
        sep = pedido.status_separacao
        pedidos_com_info.append({
            'pedido':             pedido,
            'is_retirada':        pedido.transportadora == 'Retirada na Loja',
            'total':              sep['total'],
            'separadas':          sep['separadas'],
            'tudo_separado':      sep['tudo_separado'],
            'aguardando_vinculo': False,
        })

    # ── Pedidos aguardando produção, mas já atendíveis por estoque
    #     (peça avulsa disponível, ainda não vinculada — falta ler o QR code) ──
    pedidos_aguard_producao = Pedido.objects.filter(
        status='aguard_producao',
    ).select_related('cliente', 'criado_por').prefetch_related('itens__produto').order_by('criado_em')

    for pedido in pedidos_aguard_producao:
        if _todos_insumos(pedido):
            total_itens = sum(item.quantidade for item in pedido.itens.all())
            pedidos_com_info.append({
                'pedido':             pedido,
                'is_retirada':        pedido.transportadora == 'Retirada na Loja',
                'total':              total_itens,
                'separadas':          0,
                'tudo_separado':      False,
                'aguardando_vinculo': True,
            })

    aguardando_separacao = [p for p in pedidos_com_info if not p['tudo_separado']]
    aguardando_envio     = [p for p in pedidos_com_info if p['tudo_separado']]

    # ── Enviados hoje ──
    enviados_hoje = Pedido.objects.filter(
        status__in=['shipped', 'delivered'],
        atualizado_em__date=hoje,
    ).count()

    # ── Enviados na semana ──
    enviados_semana = Pedido.objects.filter(
        status__in=['shipped', 'delivered'],
        atualizado_em__date__gte=semana,
        atualizado_em__date__lte=hoje,
    ).count()

    # ── Histórico recente ──
    historico = Pedido.objects.filter(
        status__in=['shipped', 'delivered'],
    ).select_related('cliente', 'criado_por').order_by('-atualizado_em')[:10]

    return render(request, 'core/dashboard_logistica.html', {
        'aguardando_separacao': aguardando_separacao,
        'aguardando_envio':     aguardando_envio,
        'enviados_hoje':        enviados_hoje,
        'enviados_semana':      enviados_semana,
        'historico':            historico,
        'hoje':                 hoje,
    })