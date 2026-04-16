from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from core.mixins import estoque_ou_gerente
from movimentacoes.models import Movimentacao
from core.models import Local, Fornecedor
from produtos.models import Produto


@estoque_ou_gerente
def historico_list(request):
    q = request.GET.get('q', '')
    tipo = request.GET.get('tipo', '')
    local_id = request.GET.get('local', '')
    fornecedor_id = request.GET.get('fornecedor', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')

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

    return render(request, 'movimentacoes/historico/list.html', {
        'movimentacoes': movimentacoes,
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