from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from core.models import Fornecedor, TagFornecedor
from core.forms import FornecedorForm
from django.db.models import Count
from core.models import Fornecedor, TagFornecedor

@login_required
def fornecedor_list(request):
    q = request.GET.get('q', '')
    tag_id = request.GET.get('tag', '')
    fornecedores = Fornecedor.objects.prefetch_related('tags').all()

    if q:
        fornecedores = fornecedores.filter(nome__icontains=q)
    if tag_id:
        fornecedores = fornecedores.filter(tags__id=tag_id)

    tags = TagFornecedor.objects.all()

    return render(request, 'core/fornecedor/list.html', {
        'fornecedores': fornecedores,
        'tags': tags,
        'q': q,
        'tag_selecionada': tag_id,
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

@login_required
def tag_list(request):
    tags = TagFornecedor.objects.annotate(total=Count('fornecedores'))
    return render(request, 'core/fornecedor/tags.html', {'tags': tags})


@login_required
def tag_delete(request, pk):
    tag = get_object_or_404(TagFornecedor, pk=pk)
    if request.method == 'POST':
        tag.delete()
        messages.success(request, f'Tag "{tag.nome}" removida com sucesso!')
        return redirect('core:tag_list')
    return render(request, 'core/fornecedor/tag_confirm_delete.html', {'tag': tag})