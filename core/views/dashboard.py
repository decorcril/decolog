from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from movimentacoes.models import Movimentacao
from estoque.models import Estoque
from produtos.models import Produto
from core.models import Local
from producao_corte.models import RegistroCorte
import json


@login_required
def dashboard(request):
    periodo = request.GET.get('periodo', '30')
    try:
        dias = int(periodo)
    except ValueError:
        dias = 30

    data_inicio = timezone.now() - timedelta(days=dias)

    user = request.user
    is_gerente = user.is_staff or user.groups.filter(name='Gerente').exists()
    is_supervisor_laser = user.is_staff or user.groups.filter(name='Supervisor de Laser').exists()
    is_operador_laser = user.groups.filter(name='Operador laser').exists()
    is_laser = is_supervisor_laser or is_operador_laser

    # ── Indicadores gerais ──
    total_produtos = Produto.objects.filter(ativo=True).count()
    total_itens_estoque = Estoque.objects.filter(quantidade__gt=0).count()
    total_criticos = Estoque.objects.filter(
        estoque_minimo__gt=0, quantidade__lte=F('estoque_minimo')
    ).count()
    total_alerta = Estoque.objects.filter(
        estoque_minimo__gt=0,
        quantidade__gt=F('estoque_minimo'),
        quantidade__lte=F('estoque_minimo') * 2
    ).count()

    # ── Indicadores laser ──
    total_chapas_estoque = Estoque.objects.filter(
        produto__categoria='chapa', quantidade__gt=0
    ).count()
    total_cortes_periodo = RegistroCorte.objects.filter(
        data__gte=data_inicio.date()
    ).count()
    meus_cortes_periodo = RegistroCorte.objects.filter(
        operador=user, data__gte=data_inicio.date()
    ).count()

    # ── Eixo de datas ──
    dias_labels = [
        (data_inicio + timedelta(days=i+1)).date().strftime('%d/%m')
        for i in range(dias)
    ]

    # ── Gráficos gerais ──
    entradas = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_ENTRADA, data_hora__gte=data_inicio
    ).annotate(dia=TruncDate('data_hora')).values('dia').annotate(
        total=Count('id')
    ).order_by('dia')
    entradas_dict = {e['dia'].strftime('%d/%m'): e['total'] for e in entradas}
    entradas_data = [entradas_dict.get(d, 0) for d in dias_labels]

    saidas = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_SAIDA, data_hora__gte=data_inicio
    ).annotate(dia=TruncDate('data_hora')).values('dia').annotate(
        total=Count('id')
    ).order_by('dia')
    saidas_dict = {s['dia'].strftime('%d/%m'): s['total'] for s in saidas}
    saidas_data = [saidas_dict.get(d, 0) for d in dias_labels]

    # ── Gráficos gerente ──
    transferencias = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_TRANSFERENCIA, data_hora__gte=data_inicio
    ).annotate(dia=TruncDate('data_hora')).values('dia').annotate(
        total=Count('id'), volume=Sum('quantidade')
    ).order_by('dia')
    transferencias_count_dict = {t['dia'].strftime('%d/%m'): t['total'] for t in transferencias}
    transferencias_volume_dict = {t['dia'].strftime('%d/%m'): float(t['volume'] or 0) for t in transferencias}
    transferencias_count_data = [transferencias_count_dict.get(d, 0) for d in dias_labels]
    transferencias_volume_data = [transferencias_volume_dict.get(d, 0) for d in dias_labels]

    transferencias_por_local = {}
    for local in Local.objects.filter(ativo=True):
        saidas_local = Movimentacao.objects.filter(
            tipo=Movimentacao.TIPO_TRANSFERENCIA, local=local, data_hora__gte=data_inicio
        ).annotate(dia=TruncDate('data_hora')).values('dia').annotate(total=Count('id')).order_by('dia')
        entradas_local = Movimentacao.objects.filter(
            tipo=Movimentacao.TIPO_TRANSFERENCIA, local_destino=local, data_hora__gte=data_inicio
        ).annotate(dia=TruncDate('data_hora')).values('dia').annotate(total=Count('id')).order_by('dia')
        transferencias_por_local[local.nome] = {
            'saidas': [{t['dia'].strftime('%d/%m'): t['total'] for t in saidas_local}.get(d, 0) for d in dias_labels],
            'entradas': [{t['dia'].strftime('%d/%m'): t['total'] for t in entradas_local}.get(d, 0) for d in dias_labels],
        }

    saidas_por_local = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_SAIDA, motivo='venda', data_hora__gte=data_inicio
    ).values('local__nome').annotate(total=Sum('quantidade')).order_by('-total')

    saidas_por_produto = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_SAIDA, motivo='venda', data_hora__gte=data_inicio
    ).values('produto__nome').annotate(total=Sum('quantidade')).order_by('-total')[:10]

    # ── Últimas movimentações ──
    ultimas_movimentacoes = Movimentacao.objects.select_related(
        'produto', 'local', 'usuario'
    ).order_by('-data_hora')[:8]

    # ── Cortes recentes ──
    if is_gerente or is_supervisor_laser:
        cortes_recentes = RegistroCorte.objects.prefetch_related(
            'itens__chapa', 'itens__produtos_cortados__produto'
        ).select_related('operador').order_by('-data', '-criado_em')[:8]
    elif is_operador_laser:
        cortes_recentes = RegistroCorte.objects.filter(
            operador=user
        ).prefetch_related(
            'itens__chapa', 'itens__produtos_cortados__produto'
        ).select_related('operador').order_by('-data', '-criado_em')[:8]
    else:
        cortes_recentes = None

    return render(request, 'core/dashboard.html', {
        'total_produtos': total_produtos,
        'total_itens_estoque': total_itens_estoque,
        'total_criticos': total_criticos,
        'total_alerta': total_alerta,
        'total_chapas_estoque': total_chapas_estoque,
        'total_cortes_periodo': total_cortes_periodo,
        'meus_cortes_periodo': meus_cortes_periodo,
        'dias_labels': json.dumps(dias_labels),
        'entradas_data': json.dumps(entradas_data),
        'saidas_data': json.dumps(saidas_data),
        'transferencias_count_data': json.dumps(transferencias_count_data),
        'transferencias_volume_data': json.dumps(transferencias_volume_data),
        'transferencias_por_local': json.dumps(transferencias_por_local),
        'saidas_por_local': json.dumps({
            'labels': [s['local__nome'] for s in saidas_por_local],
            'data': [float(s['total']) for s in saidas_por_local],
        }),
        'saidas_por_produto': json.dumps({
            'labels': [s['produto__nome'] for s in saidas_por_produto],
            'data': [float(s['total']) for s in saidas_por_produto],
        }),
        'ultimas_movimentacoes': ultimas_movimentacoes,
        'cortes_recentes': cortes_recentes,
        'periodo': periodo,
        'is_gerente': is_gerente,
        'is_supervisor_laser': is_supervisor_laser,
        'is_operador_laser': is_operador_laser,
        'is_laser': is_laser,
    })