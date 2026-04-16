from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.mixins import estoquista_ou_admin
from produtos.models import Produto
from produtos.forms import ProdutoForm
from django.db.models.deletion import ProtectedError


@login_required
def produto_list(request):
    q = request.GET.get('q', '')
    categoria = request.GET.get('categoria', '')
    produtos = Produto.objects.all()

    if q:
        from django.db.models import Q
        produtos = produtos.filter(
            Q(nome__icontains=q) | Q(codigo__icontains=q)
        )
    if categoria:
        produtos = produtos.filter(categoria=categoria)

    # Adiciona saldos por local em cada produto
    from estoque.models import Estoque
    for produto in produtos:
        produto.saldos_por_local = Estoque.objects.filter(
            produto=produto, quantidade__gt=0
        ).select_related('local')

    return render(request, 'produtos/produto/list.html', {
        'produtos': produtos,
        'q': q,
        'categoria': categoria,
        'categoria_choices': Produto.CATEGORIA_CHOICES,
    })


@estoquista_ou_admin
def produto_create(request):
    form = ProdutoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Produto cadastrado com sucesso!')
        return redirect('produtos:lista')
    return render(request, 'produtos/produto/form.html', {
        'form': form,
        'titulo': 'Novo Produto',
    })


@estoquista_ou_admin
def produto_update(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    form = ProdutoForm(request.POST or None, instance=produto)

    if request.method == 'GET':
        # Formata campos de dimensão removendo zeros desnecessários
        campos_decimal = [
            'largura_mm', 'comprimento_mm', 'espessura_mm',
            'largura_cm', 'comprimento_cm', 'altura_cm',
            'diametro_cm', 'profundidade_cm', 'curvatura_cm',
        ]
        for campo in campos_decimal:
            valor = getattr(produto, campo)
            if valor is not None:
                form.initial[campo] = int(valor) if valor == valor.to_integral_value() else valor

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Produto atualizado com sucesso!')
        return redirect('produtos:lista')

    return render(request, 'produtos/produto/form.html', {
        'form': form,
        'titulo': 'Editar Produto',
    })


@estoquista_ou_admin
def produto_delete(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        try:
            produto.delete()
            messages.success(request, 'Produto removido com sucesso!')
        except ProtectedError:
            messages.error(
                request,
                f'Não é possível excluir "{produto.nome}" pois possui '
                f'movimentações ou estoque vinculado. '
                f'Desative o produto em vez de excluí-lo.'
            )
        return redirect('produtos:lista')
    return render(request, 'produtos/produto/confirm_delete.html', {'produto': produto})