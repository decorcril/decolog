from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from produtos.models import Produto
from produtos.forms import ProdutoForm
from django.db.models.deletion import ProtectedError


@login_required
def produto_list(request):
    q = request.GET.get('q', '')
    categoria = request.GET.get('categoria', '')
    produtos = Produto.objects.all()

    if q:
        produtos = produtos.filter(nome__icontains=q)
    if categoria:
        produtos = produtos.filter(categoria=categoria)

    return render(request, 'produtos/produto/list.html', {
        'produtos': produtos,
        'q': q,
        'categoria': categoria,
        'categoria_choices': Produto.CATEGORIA_CHOICES,
    })


@login_required
def produto_create(request):
    form = ProdutoForm(request.POST or None)
    if request.method == 'POST':
        print('POST DATA:', request.POST)
        print('FORM VALID:', form.is_valid())
        print('FORM ERRORS:', form.errors)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto cadastrado com sucesso!')
            return redirect('produtos:lista')
    return render(request, 'produtos/produto/form.html', {
        'form': form,
        'titulo': 'Novo Produto',
    })


@login_required
def produto_update(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    form = ProdutoForm(request.POST or None, instance=produto)

    if request.method == 'GET':
        # Formata estoque_minimo
        form.initial['estoque_minimo'] = int(produto.estoque_minimo) if produto.estoque_minimo == produto.estoque_minimo.to_integral_value() else produto.estoque_minimo

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

@login_required
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