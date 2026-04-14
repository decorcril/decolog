from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from estoque.models import Estoque
from estoque.forms import EstoqueMinimoForm


@login_required
def estoque_minimo_edit(request, pk):
    estoque = get_object_or_404(Estoque, pk=pk)
    form = EstoqueMinimoForm(request.POST or None, instance=estoque)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(
            request,
            f'Estoque mínimo de "{estoque.produto.nome}" '
            f'em "{estoque.local.nome}" atualizado!'
        )
        return redirect('estoque:lista')

    return render(request, 'estoque/editar/form.html', {
        'form': form,
        'estoque': estoque,
    })