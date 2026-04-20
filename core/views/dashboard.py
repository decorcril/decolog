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
import json


@login_required
def dashboard(request):
    periodo = request.GET.get('periodo', '30')
    try:
        dias = int(periodo)
    except ValueError:
        dias = 30

    data_inicio = timezone.now() - timedelta(days=dias)

    # ══════════════════════════════════════════════════
    # INDICADORES GERAIS
    # Para adicionar novos: crie a query e passe no return render
    # ══════════════════════════════════════════════════
    total_produtos = Produto.objects.filter(ativo=True).count()
    total_itens_estoque = Estoque.objects.filter(quantidade__gt=0).count()
    total_criticos = Estoque.objects.filter(
        estoque_minimo__gt=0,
        quantidade__lte=F('estoque_minimo')
    ).count()
    total_alerta = Estoque.objects.filter(
        estoque_minimo__gt=0,
        quantidade__gt=F('estoque_minimo'),
        quantidade__lte=F('estoque_minimo') * 2
    ).count()

    # ══════════════════════════════════════════════════
    # EIXO DE DATAS
    # Lista de dias do período selecionado
    # ══════════════════════════════════════════════════
    dias_labels = []
    for i in range(dias):
        dia = (data_inicio + timedelta(days=i+1)).date()
        dias_labels.append(dia.strftime('%d/%m'))

    # ══════════════════════════════════════════════════
    # GRÁFICOS — ENTRADAS E SAÍDAS POR DIA
    # Para adicionar novos gráficos:
    # 1. Crie a query aqui
    # 2. Monte o dict com strftime('%d/%m') como chave
    # 3. Gere a lista com list comprehension usando dias_labels
    # 4. Passe no return render com json.dumps()
    # 5. Adicione data-atributo no <script id="dashboard-data"> no template
    # 6. Leia e renderize no dashboard.js
    # ══════════════════════════════════════════════════

    # Entradas por dia
    entradas = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_ENTRADA,
        data_hora__gte=data_inicio
    ).annotate(dia=TruncDate('data_hora')).values('dia').annotate(
        total=Count('id')
    ).order_by('dia')
    entradas_dict = {e['dia'].strftime('%d/%m'): e['total'] for e in entradas}
    entradas_data = [entradas_dict.get(d, 0) for d in dias_labels]

    # Saídas por dia
    saidas = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_SAIDA,
        data_hora__gte=data_inicio
    ).annotate(dia=TruncDate('data_hora')).values('dia').annotate(
        total=Count('id')
    ).order_by('dia')
    saidas_dict = {s['dia'].strftime('%d/%m'): s['total'] for s in saidas}
    saidas_data = [saidas_dict.get(d, 0) for d in dias_labels]

    # ══════════════════════════════════════════════════
    # GRÁFICOS — TRANSFERÊNCIAS (só Gerente/Admin)
    # ══════════════════════════════════════════════════

    # Transferências totais por dia
    transferencias = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_TRANSFERENCIA,
        data_hora__gte=data_inicio
    ).annotate(dia=TruncDate('data_hora')).values('dia').annotate(
        total=Count('id'),
        volume=Sum('quantidade')
    ).order_by('dia')
    transferencias_count_dict = {t['dia'].strftime('%d/%m'): t['total'] for t in transferencias}
    transferencias_volume_dict = {t['dia'].strftime('%d/%m'): float(t['volume']) for t in transferencias}
    transferencias_count_data = [transferencias_count_dict.get(d, 0) for d in dias_labels]
    transferencias_volume_data = [transferencias_volume_dict.get(d, 0) for d in dias_labels]

    # Transferências por local (origem e destino)
    transferencias_por_local = {}
    for local in Local.objects.filter(ativo=True):
        saidas_local = Movimentacao.objects.filter(
            tipo=Movimentacao.TIPO_TRANSFERENCIA,
            local=local,
            data_hora__gte=data_inicio
        ).annotate(dia=TruncDate('data_hora')).values('dia').annotate(
            total=Count('id')
        ).order_by('dia')
        saidas_local_dict = {t['dia'].strftime('%d/%m'): t['total'] for t in saidas_local}

        entradas_local = Movimentacao.objects.filter(
            tipo=Movimentacao.TIPO_TRANSFERENCIA,
            local_destino=local,
            data_hora__gte=data_inicio
        ).annotate(dia=TruncDate('data_hora')).values('dia').annotate(
            total=Count('id')
        ).order_by('dia')
        entradas_local_dict = {t['dia'].strftime('%d/%m'): t['total'] for t in entradas_local}

        transferencias_por_local[local.nome] = {
            'saidas': [saidas_local_dict.get(d, 0) for d in dias_labels],
            'entradas': [entradas_local_dict.get(d, 0) for d in dias_labels],
        }

    # ══════════════════════════════════════════════════
    # GRÁFICOS — VENDAS (só Gerente/Admin)
    # Soma quantidade vendida (não contagem de registros)
    # ══════════════════════════════════════════════════

    # Vendas por loja — soma quantidade de itens vendidos
    saidas_por_local = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_SAIDA,
        motivo='venda',
        data_hora__gte=data_inicio
    ).values('local__nome').annotate(
        total=Sum('quantidade')
    ).order_by('-total')

    # Top 10 produtos mais vendidos — soma quantidade de itens vendidos
    saidas_por_produto = Movimentacao.objects.filter(
        tipo=Movimentacao.TIPO_SAIDA,
        motivo='venda',
        data_hora__gte=data_inicio
    ).values('produto__nome').annotate(
        total=Sum('quantidade')
    ).order_by('-total')[:10]

    # ══════════════════════════════════════════════════
    # ÚLTIMAS MOVIMENTAÇÕES
    # Para mostrar mais ou menos itens, altere o [:8]
    # ══════════════════════════════════════════════════
    ultimas_movimentacoes = Movimentacao.objects.select_related(
        'produto', 'local', 'usuario'
    ).order_by('-data_hora')[:8]

    return render(request, 'core/dashboard.html', {
        # ── Indicadores ──
        'total_produtos': total_produtos,
        'total_itens_estoque': total_itens_estoque,
        'total_criticos': total_criticos,
        'total_alerta': total_alerta,
        # ── Gráficos gerais ──
        'dias_labels': json.dumps(dias_labels),
        'entradas_data': json.dumps(entradas_data),
        'saidas_data': json.dumps(saidas_data),
        # ── Gráficos transferências ──
        'transferencias_count_data': json.dumps(transferencias_count_data),
        'transferencias_volume_data': json.dumps(transferencias_volume_data),
        'transferencias_por_local': json.dumps(transferencias_por_local),
        # ── Gráficos vendas ──
        'saidas_por_local': json.dumps({
            'labels': [s['local__nome'] for s in saidas_por_local],
            'data': [float(s['total']) for s in saidas_por_local],
        }),
        'saidas_por_produto': json.dumps({
            'labels': [s['produto__nome'] for s in saidas_por_produto],
            'data': [float(s['total']) for s in saidas_por_produto],
        }),
        # ── Tabela ──
        'ultimas_movimentacoes': ultimas_movimentacoes,
        # ── Controles ──
        'periodo': periodo,
        'is_gerente': request.user.is_staff or request.user.groups.filter(name='Gerente').exists(),
    })