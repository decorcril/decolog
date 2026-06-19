document.addEventListener('DOMContentLoaded', function () {

  const TIPOS_GRATUITOS = ['exchange', 'replacement', 'advertising', 'comodato'];

  function parseMoeda(str) {
    return parseFloat((str || '0').replace(/\./g, '').replace(',', '.')) || 0;
  }

  function formatMoeda(val) {
    return val.toFixed(2).replace('.', ',').replace(/(\d)(?=(\d{3})+,)/g, '$1.');
  }

  function formatMoedaBR(val) {
    return 'R$ ' + formatMoeda(val);
  }

  function getTipoVenda() {
    return document.querySelector('[name="tipo_venda"]')?.value || '';
  }

  function isGratuito() {
    return TIPOS_GRATUITOS.includes(getTipoVenda());
  }

  function getCsrf() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
  }

  function ajaxPost(url, data, callback) {
    const body = new FormData();
    body.append('csrfmiddlewaretoken', getCsrf());
    for (const [k, v] of Object.entries(data)) body.append(k, v);
    fetch(url, {
      method: 'POST',
      body,
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
      .then(r => r.json())
      .then(data => { if (data.ok) callback(data); })
      .catch(e => console.error(e));
  }

  // ── Totais da edição ──
  function atualizarTotaisEdit() {
    const tpEl      = document.getElementById('edit_total_produtos');
    const tgEl      = document.getElementById('edit_total_geral');
    const freteEl   = document.getElementById('id_frete');
    const descontoEl = document.getElementById('id_desconto_edit');

    if (!tpEl || !tgEl) return;

    // Remove "R$ " antes de parsear
    const totalProdutos = parseMoeda(tpEl.textContent.replace('R$', '').trim());
    const frete         = freteEl   ? parseMoeda(freteEl.value)     : 0;
    const desconto      = descontoEl ? parseMoeda(descontoEl.value) : 0;
    const total         = totalProdutos - desconto + frete;

    tgEl.textContent = formatMoedaBR(total > 0 ? total : 0);

    const totalFreteEl = document.getElementById('edit_total_frete');
    if (totalFreteEl) totalFreteEl.textContent = formatMoedaBR(frete);
}

  // Listeners frete e desconto
  const freteEl    = document.getElementById('id_frete');
  const descontoEl = document.getElementById('id_desconto_edit');
  if (freteEl)    freteEl.addEventListener('input', atualizarTotaisEdit);
  if (descontoEl) descontoEl.addEventListener('input', atualizarTotaisEdit);

  const editItemsBody = document.getElementById('edit_items_body');
  const formAddItem   = document.getElementById('form-add-item');
  const pedidoPk      = formAddItem ? formAddItem.dataset.pedidoPk : null;
  let produtoEditSelecionado = null;

  const tsProdutoEdit = new TomSelect('#id_produto_search_edit', {
    valueField: 'value',
    labelField: 'text',
    searchField: ['text'],
    placeholder: 'Pesquisar produto...',
    load: function (query, callback) {
      if (!query.length) return callback();
      fetch(`/vendas/autocomplete/produtos/?q=${encodeURIComponent(query)}&tipo_venda=${getTipoVenda()}`)
        .then(r => r.json())
        .then(data => callback(data.results))
        .catch(() => callback());
    },
    minChars: 2,
    shouldLoad: q => q.length >= 2,
    onItemAdd: function (value) {
      const option = tsProdutoEdit.options[value];
      if (option) {
        produtoEditSelecionado = option;
        const preco = isGratuito() ? 0 : parseFloat(option.preco || 0);
        document.getElementById('id_preco_edit').value = formatMoeda(preco);
      }
    },
  });

  // ── Listener tipo de venda — limpa produto e preço ao trocar ──
  const tipoVendaEl = document.querySelector('[name="tipo_venda"]');
if (tipoVendaEl) {
  tipoVendaEl.addEventListener('change', function () {
    tsProdutoEdit.clear();
    tsProdutoEdit.clearOptions();
    produtoEditSelecionado = null;
    document.getElementById('id_preco_edit').value = '';

    // Se tipo gratuito, zera preço de todos os itens na tela
    if (isGratuito()) {
      editItemsBody.querySelectorAll('tr').forEach(tr => {
        const itemPk = tr.dataset.itemPk;
        if (!itemPk) return;
        ajaxPost(`/vendas/${pedidoPk}/itens/${itemPk}/atualizar/`, {
          quantidade:     tr.querySelector('.input-edit-qtd')?.value || 1,
          preco_unitario: '0.00',
        }, data => {
          atualizarTabelaEdit(data.itens, data.totais);
        });
      });
    }
  });
}

  function atualizarTabelaEdit(itens, totais) {
    editItemsBody.innerHTML = '';
    itens.forEach(item => {
      const tr = document.createElement('tr');
      tr.dataset.itemPk = item.pk;
      tr.innerHTML = `
        <td class="fw-semibold small">${item.nome}</td>
        <td class="text-center" style="width:150px">
          <div class="input-group input-group-sm">
            <button type="button" class="btn btn-outline-secondary btn-edit-minus"
                    data-item-pk="${item.pk}" data-qtd="${item.quantidade}"
                    ${item.quantidade <= 1 ? 'disabled' : ''}>−</button>
            <input type="number" class="form-control text-center input-edit-qtd"
                   value="${item.quantidade}" min="1"
                   data-item-pk="${item.pk}" style="width:55px">
            <button type="button" class="btn btn-outline-secondary btn-edit-plus"
                    data-item-pk="${item.pk}" data-qtd="${item.quantidade}">+</button>
          </div>
        </td>
        <td class="text-end text-muted small">${formatMoedaBR(item.preco)}</td>
        <td class="text-end fw-semibold">${formatMoedaBR(item.subtotal)}</td>
        <td class="text-end">
          <button type="button" class="btn btn-sm btn-link text-danger p-0 btn-edit-remove"
                  data-item-pk="${item.pk}">
            <i class="bi bi-trash"></i>
          </button>
        </td>
      `;
      editItemsBody.appendChild(tr);
    });

    if (totais) {
      const tp = document.getElementById('edit_total_produtos');
      const tg = document.getElementById('edit_total_geral');
      if (tp) tp.textContent = formatMoedaBR(totais.total_produtos);
      if (tg) tg.textContent = formatMoedaBR(totais.total_geral);
    }

    // Recalcula totais com frete atual do form
    atualizarTotaisEdit();
    bindEditListeners();
  }

  function bindEditListeners() {
    editItemsBody.querySelectorAll('.btn-edit-minus').forEach(btn => {
      btn.addEventListener('click', function () {
        const itemPk = this.dataset.itemPk;
        const qtd    = Math.max(1, parseInt(this.dataset.qtd) - 1);
        ajaxPost(`/vendas/${pedidoPk}/itens/${itemPk}/atualizar/`, { quantidade: qtd }, data => {
          atualizarTabelaEdit(data.itens, data.totais);
        });
      });
    });

    editItemsBody.querySelectorAll('.btn-edit-plus').forEach(btn => {
      btn.addEventListener('click', function () {
        const itemPk = this.dataset.itemPk;
        const qtd    = parseInt(this.dataset.qtd) + 1;
        ajaxPost(`/vendas/${pedidoPk}/itens/${itemPk}/atualizar/`, { quantidade: qtd }, data => {
          atualizarTabelaEdit(data.itens, data.totais);
        });
      });
    });

    editItemsBody.querySelectorAll('.input-edit-qtd').forEach(input => {
      input.addEventListener('change', function () {
        const itemPk = this.dataset.itemPk;
        const qtd    = Math.max(1, parseInt(this.value) || 1);
        ajaxPost(`/vendas/${pedidoPk}/itens/${itemPk}/atualizar/`, { quantidade: qtd }, data => {
          atualizarTabelaEdit(data.itens, data.totais);
        });
      });
    });

    editItemsBody.querySelectorAll('.btn-edit-remove').forEach(btn => {
      btn.addEventListener('click', function () {
        const itemPk = this.dataset.itemPk;
        ajaxPost(`/vendas/${pedidoPk}/itens/${itemPk}/remover/`, {}, data => {
          atualizarTabelaEdit(data.itens, data.totais);
        });
      });
    });
  }

  document.getElementById('btn_add_item_edit').addEventListener('click', function () {
    if (!produtoEditSelecionado) { alert('Selecione um produto.'); return; }

    const preco = parseMoeda(document.getElementById('id_preco_edit').value);
    if (preco <= 0 && !isGratuito()) {
      alert('Este produto não tem preço cadastrado.');
      return;
    }

    const qtd = parseInt(document.getElementById('edit_qtd').value) || 1;

    ajaxPost(`/vendas/${pedidoPk}/itens/adicionar/`, {
      produto:        produtoEditSelecionado.value,
      quantidade:     qtd,
      preco_unitario: preco.toFixed(2),
    }, data => {
      atualizarTabelaEdit(data.itens, data.totais);
      tsProdutoEdit.clear();
      tsProdutoEdit.clearOptions();
      produtoEditSelecionado = null;
      document.getElementById('id_preco_edit').value = '';
      document.getElementById('edit_qtd').value = 1;
    });
  });

  bindEditListeners();
});