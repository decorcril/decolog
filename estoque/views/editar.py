from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from core.mixins import estoquista_ou_admin, loja_do_usuario
from estoque.models import Estoque
from estoque.forms import EstoqueMinimoForm


@estoquista_ou_admin
def estoque_minimo_edit(request, pk):
    estoque = get_object_or_404(Estoque, pk=pk)

    loja_restrita = loja_do_usuario(request.user)
    if loja_restrita and estoque.local != loja_restrita:
        raise PermissionDenied('Você só pode editar o estoque da sua loja.')

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