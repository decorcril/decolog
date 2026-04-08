from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.models import Fornecedor
from core.forms import FornecedorForm


@login_required
def fornecedor_list(request):
    q = request.GET.get('q', '')
    fornecedores = Fornecedor.objects.all()
    if q:
        fornecedores = fornecedores.filter(nome__icontains=q)
    return render(request, 'core/fornecedor/list.html', {
        'fornecedores': fornecedores,
        'q': q,
    })


@login_required
def fornecedor_create(request):
    form = FornecedorForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, 'Fornecedor cadastrado com sucesso!')
        return redirect('core:fornecedor_list')
    return render(request, 'core/fornecedor/form.html', {
        'form': form,
        'titulo': 'Novo Fornecedor',
    })


@login_required
def fornecedor_update(request, pk):
    fornecedor = get_object_or_404(Fornecedor, pk=pk)
    form = FornecedorForm(request.POST or None, instance=fornecedor)
    if form.is_valid():
        form.save()
        messages.success(request, 'Fornecedor atualizado com sucesso!')
        return redirect('core:fornecedor_list')
    return render(request, 'core/fornecedor/form.html', {
        'form': form,
        'titulo': 'Editar Fornecedor',
    })


@login_required
def fornecedor_delete(request, pk):
    fornecedor = get_object_or_404(Fornecedor, pk=pk)
    if request.method == 'POST':
        fornecedor.delete()
        messages.success(request, 'Fornecedor removido com sucesso!')
        return redirect('core:fornecedor_list')
    return render(request, 'core/fornecedor/confirm_delete.html', {
        'fornecedor': fornecedor,
    })