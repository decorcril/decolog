from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from produtos.models import Produto
from produtos.models.preco import PrecoProduto
from core.mixins import gerente_ou_admin


@gerente_ou_admin
def preco_edit(request, produto_pk):
    produto = get_object_or_404(Produto, pk=produto_pk)
    
    try:
        preco = produto.preco
    except PrecoProduto.DoesNotExist:
        preco = None

    if request.method == 'POST':
        valor = request.POST.get('preco_venda', '0').replace('.', '').replace(',', '.')
        try:
            from decimal import Decimal
            valor_decimal = Decimal(valor)
            if preco:
                preco.preco_venda = valor_decimal
                preco.atualizado_por = request.user
                preco.save()
            else:
                preco = PrecoProduto.objects.create(
                    produto=produto,
                    preco_venda=valor_decimal,
                    atualizado_por=request.user,
                )
            messages.success(request, f'Preço de {produto.nome} atualizado!')
        except Exception as e:
            messages.error(request, f'Valor inválido: {e}')
        return redirect('produtos:detalhe', pk=produto.pk)

    return render(request, 'produtos/preco_form.html', {
        'produto': produto,
        'preco': preco,
    })