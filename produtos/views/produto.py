from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.urls import reverse
from functools import reduce
import operator
from core.mixins import estoquista_ou_admin, supervisor_laser_ou_admin
from produtos.models import Produto
from produtos.forms import ProdutoForm
from estoque.models import Estoque


def pode_gerir_produtos(user):
    return (
        user.is_staff or
        user.groups.filter(name__in=['Estoquista', 'Gerente', 'Supervisor de Laser']).exists()
    )


def is_supervisor_laser(user):
    return not user.is_staff and user.groups.filter(name='Supervisor de Laser').exists() and \
           not user.groups.filter(name__in=['Estoquista', 'Gerente']).exists()


def _url_lista_com_filtros(q='', categoria='', page=''):
    url = reverse('produtos:lista')
    params = []
    if q:
        params.append(f'q={q}')
    if categoria:
        params.append(f'categoria={categoria}')
    if page and page != '1':
        params.append(f'page={page}')
    if params:
        url += '?' + '&'.join(params)
    return url


@login_required
def produto_list(request):
    q = request.GET.get('q', '')
    categoria = request.GET.get('categoria', '')

    produtos = Produto.objects.all()

    if is_supervisor_laser(request.user):
        produtos = produtos.filter(categoria='produto_final')
        categoria = 'produto_final'

    if q:
        termos = q.split()
        queries = [Q(nome__icontains=t) | Q(codigo__istartswith=t) for t in termos]
        produtos = produtos.filter(reduce(operator.and_, queries))

    if categoria and not is_supervisor_laser(request.user):
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
        'is_supervisor_laser': is_supervisor_laser(request.user),
        'pode_gerir': pode_gerir_produtos(request.user),
    })


@login_required
def produto_create(request):
    if not pode_gerir_produtos(request.user):
        messages.error(request, 'Você não tem permissão para cadastrar produtos.')
        return redirect('produtos:lista')

    form = ProdutoForm(request.POST or None)

    if is_supervisor_laser(request.user):
        form.fields['categoria'].initial = 'produto_final'
        form.fields['categoria'].widget.attrs['disabled'] = True

    if request.method == 'POST' and form.is_valid():
        produto = form.save(commit=False)
        if is_supervisor_laser(request.user):
            produto.categoria = 'produto_final'
        produto.save()
        messages.success(request, 'Produto cadastrado com sucesso!')
        return redirect('produtos:lista')

    return render(request, 'produtos/produto/form.html', {
        'form': form,
        'titulo': 'Novo Produto',
        'is_supervisor_laser': is_supervisor_laser(request.user),
        'q': '',
        'categoria': '',
        'page': '',
    })


@login_required
def produto_update(request, pk):
    if not pode_gerir_produtos(request.user):
        messages.error(request, 'Você não tem permissão para editar produtos.')
        return redirect('produtos:lista')

    produto = get_object_or_404(Produto, pk=pk)

    if is_supervisor_laser(request.user) and produto.categoria != 'produto_final':
        messages.error(request, 'Você só pode editar produtos finais.')
        return redirect('produtos:lista')

    q = request.GET.get('q', '')
    categoria = request.GET.get('categoria', '')
    page = request.GET.get('page', '')

    form = ProdutoForm(request.POST or None, instance=produto)

    if is_supervisor_laser(request.user):
        form.fields['categoria'].widget.attrs['disabled'] = True

    if request.method == 'POST' and form.is_valid():
        produto = form.save(commit=False)
        if is_supervisor_laser(request.user):
            produto.categoria = 'produto_final'
        produto.save()
        messages.success(request, 'Produto atualizado com sucesso!')
        return redirect(_url_lista_com_filtros(q, categoria, page))

    return render(request, 'produtos/produto/form.html', {
        'form': form,
        'titulo': 'Editar Produto',
        'is_supervisor_laser': is_supervisor_laser(request.user),
        'q': q,
        'categoria': categoria,
        'page': page,
    })


@login_required
def produto_delete(request, pk):
    if not pode_gerir_produtos(request.user):
        messages.error(request, 'Você não tem permissão para excluir produtos.')
        return redirect('produtos:lista')

    produto = get_object_or_404(Produto, pk=pk)

    if is_supervisor_laser(request.user) and produto.categoria != 'produto_final':
        messages.error(request, 'Você só pode excluir produtos finais.')
        return redirect('produtos:lista')

    q = request.GET.get('q', '')
    categoria = request.GET.get('categoria', '')
    page = request.GET.get('page', '')

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
        return redirect(_url_lista_com_filtros(q, categoria, page))

    return render(request, 'produtos/produto/confirm_delete.html', {
        'produto': produto,
        'q': q,
        'categoria': categoria,
        'page': page,
    })
    
@login_required
def produto_detail(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    saldos  = Estoque.objects.filter(
        produto=produto, quantidade__gt=0
    ).select_related('local')

    aba = request.GET.get('aba', 'estoque')

    q         = request.GET.get('q', '')
    categoria = request.GET.get('categoria', '')
    page      = request.GET.get('page', '')

    # Ficha técnica
    from produtos.models import FichaTecnica
    ficha = FichaTecnica.objects.filter(produto=produto).prefetch_related('itens__material').first()

    # Produtos disponíveis para composição
    produtos_finais = Produto.objects.filter(
        categoria='produto_final', ativo=True
    ).exclude(pk=pk).order_by('nome')

    return render(request, 'produtos/produto/detail.html', {
        'produto':        produto,
        'saldos':         saldos,
        'pode_gerir':     pode_gerir_produtos(request.user),
        'aba':            aba,
        'ficha':          ficha,
        'produtos_finais': produtos_finais,
        'q':              q,
        'categoria':      categoria,
        'page':           page,
    })

@login_required
def ficha_tecnica_edit(request, pk):
    if not pode_gerir_produtos(request.user):
        messages.error(request, 'Você não tem permissão para editar fichas técnicas.')
        return redirect('produtos:detalhe', pk=pk)

    produto = get_object_or_404(Produto, pk=pk)

    if produto.categoria != 'produto_final':
        messages.error(request, 'Somente produtos finais podem ter ficha técnica.')
        return redirect('produtos:detalhe', pk=pk)

    from produtos.models import FichaTecnica, ItemFichaTecnica

    ficha, _ = FichaTecnica.objects.get_or_create(produto=produto)

    if request.method == 'POST':
        action = request.POST.get('action')

        # ── Adicionar componente ──
        if action == 'add':
            material_id = request.POST.get('material')
            quantidade  = request.POST.get('quantidade', '1').replace(',', '.')
            observacao  = request.POST.get('observacao', '')

            if not material_id:
                messages.error(request, 'Selecione um material.')
            elif material_id == str(pk):
                messages.error(request, 'Um produto não pode ser componente de si mesmo.')
            else:
                try:
                    from decimal import Decimal
                    material = get_object_or_404(Produto, pk=material_id)
                    ItemFichaTecnica.objects.update_or_create(
                        ficha=ficha,
                        material=material,
                        defaults={
                            'quantidade':  Decimal(quantidade),
                            'observacao':  observacao,
                        }
                    )
                    messages.success(request, f'{material.nome} adicionado à composição.')
                except Exception as e:
                    messages.error(request, f'Erro ao adicionar: {e}')

        # ── Remover componente ──
        elif action == 'remove':
            item_pk = request.POST.get('item_pk')
            ItemFichaTecnica.objects.filter(pk=item_pk, ficha=ficha).delete()
            messages.success(request, 'Componente removido.')

        return redirect('produtos:detalhe', pk=pk)

    return redirect('produtos:detalhe', pk=pk)