from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from core.mixins import estoquista_ou_admin
from produtos.models import Produto
from produtos.forms import ProdutoForm
from estoque.models import Estoque


@login_required
def produto_list(request):
    q = request.GET.get('q', '')
    categoria = request.GET.get('categoria', '')

    produtos = Produto.objects.all()

    if q:
        produtos = produtos.filter(
            Q(nome__icontains=q) | Q(codigo__icontains=q)
        )
    if categoria:
        produtos = produtos.filter(categoria=categoria)

    produtos = produtos.order_by('nome')

    paginator = Paginator(produtos, 24)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for produto in page_obj:
        produto.saldos_por_local = Estoque.objects.filter(
            produto=produto, quantidade__gt=0
        ).select_related('local')

    return render(request, 'produtos/produto/list.html', {
        'produtos': page_obj,
        'page_obj': page_obj,
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