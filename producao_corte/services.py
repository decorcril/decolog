from django.utils import timezone

from movimentacoes.models import Movimentacao
from estoque.models import Estoque
from core.models import Local


def _kit_que_contem(produto):
    """
    Retorna o produto Kit (produto_final) cuja ficha inclui `produto` como
    componente, se houver um Kit reconhecido (is_kit=True) contendo-o.
    Usado pro "desmembramento reverso": pedido de 1 componente solto (ex:
    Cubo P) sem avulsa própria, mas com um Kit inteiro (Trio) disponível
    que o contém.
    """
    from produtos.models import FichaTecnica
    fichas = FichaTecnica.objects.filter(itens__material=produto).distinct()
    for ficha in fichas:
        if ficha.is_kit:
            return ficha.produto
    return None


def disponibilidade_produto_final(produto, quantidade):
    """
    Verifica quantas unidades de `produto` (produto_final) já estão prontas
    em estoque avulso, sem precisar cortar de novo.

    Combina, nessa ordem:
    1. Peças cortadas diretamente como esse produto.
    2. Se sobrar quantidade e o produto for Kit: peças avulsas dos
       componentes, decompostas via FichaTecnica.
    3. Se sobrar quantidade e o produto NÃO for Kit, mas for componente de
       algum Kit: Kits inteiros disponíveis que podem ser desmembrados pra
       liberar esse componente.

    Retorna (ok, n_diretas, componentes).
    """
    from producao_corte.models import ProdutoCortado

    fabrica = Local.objects.filter(tipo='fabrica').first()

    def _disponivel_real(prod):
        n_pecas = ProdutoCortado.objects.filter(
            produto=prod, status='montado', pedido=None,
        ).count()

        if prod.is_kit:
            # Kit não tem Estoque próprio por design — a entrada da peça
            # pronta é pulada de propósito na montagem (confirmar_montagem_peca).
            return n_pecas

        saldo = Estoque.objects.filter(produto=prod, local=fabrica).first()
        n_estoque = int(saldo.quantidade) if saldo else 0
        return min(n_pecas, n_estoque)

    n_diretas = min(_disponivel_real(produto), quantidade)
    restante  = quantidade - n_diretas

    if restante <= 0:
        return True, n_diretas, []

    if produto.is_kit:
        ficha = produto.ficha_tecnica
        componentes = []
        ok = True
        for item in ficha.itens.select_related('material').all():
            necessario = item.quantidade * restante
            disponivel = _disponivel_real(item.material)
            item_ok    = disponivel >= necessario
            if not item_ok:
                ok = False
            componentes.append({
                'nome':       item.material.nome,
                'necessario': necessario,
                'disponivel': disponivel,
                'ok':         item_ok,
            })
        return ok, n_diretas, componentes

    # ── Produto não é Kit — checa se é componente de algum Kit disponível ──
    kit = _kit_que_contem(produto)
    if not kit:
        return False, n_diretas, []

    disponivel_kit = _disponivel_real(kit)
    ok = disponivel_kit >= restante
    componentes = [{
        'nome':       f'{kit.nome} (desmembrar)',
        'necessario': restante,
        'disponivel': disponivel_kit,
        'ok':         ok,
    }]
    return ok, n_diretas, componentes


def _local_com_saldo(produto, local_preferido, local_fallback, quantidade):
    """
    Usa o local preferido se ele tiver saldo suficiente do produto;
    caso contrário, cai para o local de fallback (fábrica).
    """
    if local_preferido:
        saldo = Estoque.objects.filter(produto=produto, local=local_preferido).first()
        if saldo and saldo.quantidade >= quantidade:
            return local_preferido
    return local_fallback


def debitar_componentes_ficha(peca, pedido, usuario):
    """
    Ao separar uma peça (ProdutoCortado), debita do Estoque agregado:
    1. A própria peça pronta (pulado se for Kit — não tem estoque próprio).
    2. Os materiais/peças da ficha técnica, se houver.
    """
    fabrica_padrao  = Local.objects.filter(tipo='fabrica').first()
    local_preferido = pedido.local_saida if pedido else None

    ficha  = getattr(peca.produto, 'ficha_tecnica', None)
    eh_kit = peca.produto.is_kit

    if not eh_kit:
        local_peca = _local_com_saldo(peca.produto, local_preferido, fabrica_padrao, 1)
        Movimentacao.objects.create(
            produto    = peca.produto,
            local      = local_peca,
            tipo       = 'saida',
            motivo     = 'venda',
            quantidade = 1,
            observacao = (
                f'Separação — Pedido {pedido.numero} ({peca.produto.nome})'
                if pedido else f'Separação — {peca.produto.nome}'
            ),
            usuario    = usuario,
        )

    if ficha:
        for componente in ficha.itens.select_related('material').all():
            local_usar = _local_com_saldo(
                componente.material, local_preferido, fabrica_padrao, componente.quantidade
            )
            Movimentacao.objects.create(
                produto    = componente.material,
                local      = local_usar,
                tipo       = 'saida',
                motivo     = 'venda',
                quantidade = componente.quantidade,
                observacao = (
                    f'Separação — Pedido {pedido.numero} ({peca.produto.nome})'
                    if pedido else f'Separação — {peca.produto.nome}'
                ),
                usuario    = usuario,
            )


def desmembrar_peca(peca, usuario):
    """
    Desmembra uma peça Kit (ProdutoCortado) em peças avulsas novas, uma por
    componente da FichaTecnica (respeitando a quantidade de cada um).
    Marca a peça original como 'desmembrado' (mantida pra auditoria, sai
    das contagens de disponibilidade e de status_separacao) e cria uma
    ProdutoCortado nova por componente, com origem_desmembramento apontando
    pra ela.

    Pressupõe peca.produto.is_kit — não revalida.
    Usada tanto pelo desmembramento manual (producao_corte/views/desmembrar.py)
    quanto pelo desmembramento automático em consumir_produto_final, quando
    um pedido de componente solto só pode ser resolvido quebrando um Kit
    inteiro.

    Retorna a lista de ProdutoCortado novas.
    """
    from producao_corte.models import ProdutoCortado

    agora = timezone.now()
    ficha = peca.produto.ficha_tecnica
    novas = []

    for item in ficha.itens.select_related('material').all():
        for _ in range(int(item.quantidade)):
            nova = ProdutoCortado.objects.create(
                item_corte=peca.item_corte,
                produto=item.material,
                status='montado',
                cortada_por=peca.cortada_por,
                montada_por=peca.montada_por,
                montada_em=peca.montada_em,
                origem_desmembramento=peca,
                observacao=(
                    f'Gerada por desmembramento de {peca.produto.nome} '
                    f'(peça {peca.token[:8]})'
                ),
            )
            novas.append(nova)

    peca.status          = 'desmembrado'
    peca.desmembrada_por = usuario
    peca.desmembrada_em  = agora
    peca.save(update_fields=['status', 'desmembrada_por', 'desmembrada_em'])

    return novas


def consumir_produto_final(produto, quantidade, pedido, usuario):
    """
    Vincula ao `pedido` peças ProdutoCortado reais que resolvem `quantidade`
    unidades de `produto` — direta, via componentes de Kit, ou via
    desmembramento automático de um Kit inteiro (quando `produto` é um
    componente avulso sem estoque próprio suficiente) — marcando cada uma
    como 'separado' e debitando o Estoque agregado correspondente.

    Pressupõe que disponibilidade_produto_final(produto, quantidade) já
    retornou ok=True; não revalida.

    Retorna a lista de ProdutoCortado vinculados.
    """
    from producao_corte.models import ProdutoCortado

    agora      = timezone.now()
    vinculadas = []

    def _vincular(peca):
        debitar_componentes_ficha(peca, pedido, usuario)
        peca.pedido       = pedido
        peca.status       = 'separado'
        peca.separada_por = usuario
        peca.separada_em  = agora
        peca.save(update_fields=['pedido', 'status', 'separada_por', 'separada_em'])
        vinculadas.append(peca)

    _, n_diretas, _ = disponibilidade_produto_final(produto, quantidade)

    diretas = ProdutoCortado.objects.filter(
        produto=produto, status='montado', pedido=None,
    ).order_by('id')[:n_diretas]
    for peca in diretas:
        _vincular(peca)

    restante = quantidade - n_diretas
    if restante <= 0:
        return vinculadas

    if produto.is_kit:
        ficha = produto.ficha_tecnica
        for comp in ficha.itens.select_related('material').all():
            qtd_necessaria = int(comp.quantidade * restante)
            pecas_comp = ProdutoCortado.objects.filter(
                produto=comp.material, status='montado', pedido=None,
            ).order_by('id')[:qtd_necessaria]
            for peca in pecas_comp:
                _vincular(peca)
        return vinculadas

    # ── Componente solto sem avulsa própria — desmembra Kit(s) inteiro(s) ──
    kit = _kit_que_contem(produto)
    if kit:
        kits_disponiveis = ProdutoCortado.objects.filter(
            produto=kit, status='montado', pedido=None,
        ).order_by('id')[:restante]
        for kit_peca in kits_disponiveis:
            novas = desmembrar_peca(kit_peca, usuario)
            for nova in novas:
                if restante > 0 and nova.produto_id == produto.id:
                    _vincular(nova)
                    restante -= 1
                # demais componentes (ex: M, G) ficam avulsas — já nasceram
                # 'montado', pedido=None — disponíveis pra outros pedidos.

    return vinculadas


def pedidos_precisando_peca(peca):
    """
    Encontra pedidos (picking/aguard_producao) que precisam desta peça
    avulsa — direto (item do pedido = produto da peça) OU como componente
    de um Kit ainda não totalmente resolvido.
    """
    from vendas.models import Pedido
    from producao_corte.models import ProdutoCortado

    diretos = Pedido.objects.filter(
        status__in=['picking', 'aguard_producao'],
        itens__produto=peca.produto,
    )

    candidatos_kit = Pedido.objects.filter(
        status__in=['picking', 'aguard_producao'],
        itens__produto__ficha_tecnica__itens__material=peca.produto,
    ).distinct().prefetch_related('itens__produto')

    kits_ids = []
    for pedido in candidatos_kit:
        for item in pedido.itens.select_related('produto').all():
            if not item.produto.is_kit:
                continue
            componente = item.produto.ficha_tecnica.itens.filter(material=peca.produto).first()
            if not componente:
                continue
            necessario = int(componente.quantidade * item.quantidade)
            ja_vinculadas = ProdutoCortado.objects.filter(
                pedido=pedido, produto=peca.produto,
            ).exclude(status='desmembrado').count()
            if ja_vinculadas < necessario:
                kits_ids.append(pedido.pk)
                break

    return (diretos | Pedido.objects.filter(pk__in=kits_ids)).distinct().select_related('cliente')


def confirmar_montagem_peca(peca, usuario):
    """
    Confirma a montagem de uma peça (ProdutoCortado): aguardando -> montado.
    Dá entrada no Estoque agregado — peça pronta (pulado se Kit) + componentes
    da ficha técnica, se houver. Avança o pedido pra PICKING se essa era a
    última peça faltando montar.
    """
    from producao_corte.models import ProdutoCortado

    fabrica = Local.objects.filter(tipo='fabrica').first()
    eh_kit  = peca.produto.is_kit

    ficha = getattr(peca.produto, 'ficha_tecnica', None)
    if ficha:
        for componente in ficha.itens.select_related('material').all():
            Movimentacao.objects.create(
                produto    = componente.material,
                local      = fabrica,
                tipo       = 'entrada',
                motivo     = 'producao',
                quantidade = componente.quantidade,
                observacao = f'Montagem — {peca.produto.nome}',
                usuario    = usuario,
            )

    if not eh_kit:
        Movimentacao.objects.create(
            produto    = peca.produto,
            local      = fabrica,
            tipo       = 'entrada',
            motivo     = 'producao',
            quantidade = 1,
            observacao = f'Montagem — {peca.produto.nome} (peça pronta)',
            usuario    = usuario,
        )

    peca.status      = 'montado'
    peca.montada_por = usuario
    peca.montada_em  = timezone.now()
    peca.save(update_fields=['status', 'montada_por', 'montada_em'])

    if peca.pedido:
        pedido   = peca.pedido
        total    = ProdutoCortado.objects.filter(pedido=pedido).count()
        montadas = ProdutoCortado.objects.filter(pedido=pedido, status='montado').count()
        if total > 0 and montadas >= total:
            pedido.status = pedido.Status.PICKING
            pedido.save(update_fields=['status', 'atualizado_em'])

    return peca