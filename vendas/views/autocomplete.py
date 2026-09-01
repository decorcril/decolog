from django.http import JsonResponse
from django.db.models import Q
from clientes.models import Cliente
from produtos.models import Produto


def autocomplete_cliente(request):
    q = request.GET.get('q', '')
    clientes = Cliente.objects.filter(ativo=True).filter(
        Q(nome__icontains=q) |
        Q(nome_fantasia__icontains=q) |
        Q(documento__icontains=q) |
        Q(codigo__icontains=q)
    ).order_by('nome')[:20]

    return JsonResponse({
        'results': [
            {
                'value':     c.pk,
                'text':      f'{c.codigo} — {c.nome}',
                'nome':      c.nome,
                'documento': c.documento,
                'email':     c.email,
                'telefone':  c.telefone,
                'cidade':    c.cidade,
                'estado':    c.estado,
                'cep':       c.cep or '',
            }
            for c in clientes
        ]
    })

def autocomplete_produto(request):
    q = request.GET.get('q', '')

    produtos = Produto.objects.filter(
        ativo=True,
        categoria__in=['produto_final', 'insumo']
    )

    if q:
        produtos = produtos.filter(
            Q(nome__icontains=q) | Q(codigo__icontains=q)
        )

    produtos = produtos.select_related('preco').order_by('nome')[:20]

    return JsonResponse({
        'results': [
            {
                'value': p.pk,
                'text':  f'{p.codigo} — {p.nome}' if p.codigo else p.nome,
                'nome':  p.nome,
                'preco': str(p.preco.preco_venda) if hasattr(p, 'preco') and p.preco else '0',
            }
            for p in produtos
        ]
    })