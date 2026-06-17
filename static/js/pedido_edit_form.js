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