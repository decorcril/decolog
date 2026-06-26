from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.models import User

from core.mixins import laser_ou_gerente, montagem_ou_gerente
from vendas.models import Pedido


# ══════════════════════════════════════════
# LASER
# ══════════════════════════════════════════

@laser_ou_gerente
def laser_list(request):
    user          = request.user
    is_supervisor = (
        user.is_staff or
        user.groups.filter(name__in=['Supervisor de Laser', 'Gerente']).exists()
    )

    if is_supervisor:
        pedidos_aguardando = Pedido.objects.filter(
            status='aguard_producao',
        ).select_related('cliente', 'criado_por', 'operador_corte').order_by('criado_em')

        pedidos_em_corte = Pedido.objects.filter(
            status='cutting',
        ).select_related('cliente', 'criado_por', 'operador_corte').order_by('criado_em')

        operadores = User.objects.filter(
            groups__name='Operador de Laser',
            is_active=True,
        ).order_by('first_name', 'last_name')

    else:
        pedidos_aguardando = Pedido.objects.filter(
            status='aguard_producao',
            operador_corte=user,
        ).select_related('cliente', 'criado_por').order_by('criado_em')

        pedidos_em_corte = Pedido.objects.filter(
            status='cutting',
            operador_corte=user,
        ).select_related('cliente', 'criado_por').order_by('criado_em')

        operadores = None

    return render(request, 'vendas/laser_list.html', {
        'pedidos_aguardando': pedidos_aguardando,
        'pedidos_em_corte':   pedidos_em_corte,
        'operadores':         operadores,
        'is_supervisor':      is_supervisor,
    })


@laser_ou_gerente
def laser_atribuir(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk, status__in=['aguard_producao', 'cutting'])

    if request.method == 'POST':
        operador_id = request.POST.get('operador_id')
        if operador_id:
            operador = get_object_or_404(User, pk=operador_id)
            pedido.operador_corte = operador
            pedido.save(update_fields=['operador_corte', 'atualizado_em'])
            messages.success(
                request,
                f'Pedido {pedido.numero} atribuído para {operador.get_full_name() or operador.username}.'
            )
        else:
            pedido.operador_corte = None
            pedido.save(update_fields=['operador_corte', 'atualizado_em'])
            messages.success(request, f'Atribuição do pedido {pedido.numero} removida.')

    return redirect('vendas:laser_list')


@laser_ou_gerente
def laser_confirmar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    return redirect(f'/producao/novo/?pedido_pk={pedido.pk}')


@laser_ou_gerente
def laser_finalizar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    return redirect(f'/producao/novo/?pedido_pk={pedido.pk}')


# ══════════════════════════════════════════
# MONTAGEM
# ══════════════════════════════════════════

@montagem_ou_gerente
def montagem_list(request):
    pedidos = Pedido.objects.filter(
        status='assembling',
    ).select_related('cliente', 'criado_por').order_by('criado_em')

    pedidos_com_progresso = []
    for pedido in pedidos:
        pedidos_com_progresso.append({
            'pedido':             pedido,
            'progresso_montagem': pedido.progresso_montagem,
        })

    return render(request, 'vendas/montagem_list.html', {
        'pedidos': pedidos_com_progresso,
    })


@montagem_ou_gerente
def montagem_finalizar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    return redirect(f'/montagem/registrar/?pedido_pk={pedido.pk}')