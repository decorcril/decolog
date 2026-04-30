from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.core.paginator import Paginator
from movimentacoes.models import Movimentacao, OrdemTransferencia
from core.models import Local, Fornecedor
from produtos.models import Produto


@login_required
def historico_list(request):
    q = request.GET.get('q', '')
    tipo = request.GET.get('tipo', '')
    local_id = request.GET.get('local', '')
    fornecedor_id = request.GET.get('fornecedor', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')

    # ── Movimentações simples ──
    movimentacoes = Movimentacao.objects.select_related(
        'produto', 'local', 'local_destino', 'fornecedor', 'usuario'
    ).order_by('-data_hora')

    if q:
        movimentacoes = movimentacoes.filter(
            Q(produto__nome__icontains=q) | Q(produto__codigo__icontains=q)
        )
    if tipo:
        movimentacoes = movimentacoes.filter(tipo=tipo)
    if local_id:
        movimentacoes = movimentacoes.filter(
            Q(local__id=local_id) | Q(local_destino__id=local_id)
        )
    if fornecedor_id:
        movimentacoes = movimentacoes.filter(fornecedor__id=fornecedor_id)
    if data_inicio:
        movimentacoes = movimentacoes.filter(data_hora__date__gte=data_inicio)
    if data_fim:
        movimentacoes = movimentacoes.filter(data_hora__date__lte=data_fim)

    paginator_mov = Paginator(movimentacoes, 25)
    page_mov = request.GET.get('page_mov')
    page_obj_mov = paginator_mov.get_page(page_mov)

    # ── Ordens de transferência ──
    ordens = OrdemTransferencia.objects.select_related(
        'local_origem', 'local_destino', 'criado_por'
    ).order_by('-data_envio')

    if local_id:
        ordens = ordens.filter(
            Q(local_origem__id=local_id) | Q(local_destino__id=local_id)
        )
    if data_inicio:
        ordens = ordens.filter(data_envio__date__gte=data_inicio)
    if data_fim:
        ordens = ordens.filter(data_envio__date__lte=data_fim)
    if q:
        ordens = ordens.filter(
            itens__produto__nome__icontains=q
        ).distinct()

    paginator_ord = Paginator(ordens, 10)
    page_ord = request.GET.get('page_ord')
    page_obj_ord = paginator_ord.get_page(page_ord)

    return render(request, 'movimentacoes/historico/list.html', {
        'movimentacoes': page_obj_mov,
        'ordens': page_obj_ord,
        'page_obj_mov': page_obj_mov,
        'page_obj_ord': page_obj_ord,
        'locais': Local.objects.filter(ativo=True),
        'fornecedores': Fornecedor.objects.filter(ativo=True),
        'tipo_choices': Movimentacao.TIPO_CHOICES,
        'q': q,
        'tipo': tipo,
        'local_id': local_id,
        'fornecedor_id': fornecedor_id,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    })