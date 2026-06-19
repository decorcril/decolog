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
    fetch(url, { method: 'POST', body })
      .then(r => r.json())
      .then(data => { if (data.ok) callback(data); })
      .catch(e => console.error(e));
  }

  // ── Tom Select: Cliente ──
  if (document.getElementById('id_cliente')) {
    new TomSelect('#id_cliente', {
      valueField: 'value',
      labelField: 'text',
      searchField: ['text'],
      placeholder: 'Pesquisar cliente...',
      load: function (query, callback) {
        if (!query.length) return callback();
        fetch(`/vendas/autocomplete/clientes/?q=${encodeURIComponent(query)}`)
          .then(r => r.json())
          .then(data => callback(data.results))
          .catch(() => callback());
      },
      minChars: 2,
      shouldLoad: q => q.length >= 2,
    });
  }

  // ══════════════════════════════════════════
  // CRIAÇÃO — itens via JS
  // ══════════════════════════════════════════
  if (document.getElementById('id_produto_search')) {
    let produtoSelecionado = null;
    let items = [];

    const tsProduto = new TomSelect('#id_produto_search', {
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
        const option = tsProduto.options[value];
        if (option) {
          produtoSelecionado = option;
          const preco = isGratuito() ? 0 : parseFloat(option.preco || 0);
          document.getElementById('id_preco_add').value = formatMoeda(preco);
        }
      },
    });

    // ── Listener tipo de venda — limpa produtos e itens ──
    const tipoVendaEl = document.querySelector('[name="tipo_venda"]');
    if (tipoVendaEl) {
      tipoVendaEl.addEventListener('change', function () {
        if (items.length > 0) {
          const confirma = confirm(
            'Ao trocar o tipo de venda os itens adicionados serão removidos. Deseja continuar?'
          );
          if (!confirma) {
            this.value = this.dataset.valorAnterior || '';
            return;
          }
          items = [];
        }
        // Guarda valor atual para possível rollback
        this.dataset.valorAnterior = this.value;
        // Limpa produto selecionado e preço
        tsProduto.clear();
        tsProduto.clearOptions();
        produtoSelecionado = null;
        document.getElementById('id_preco_add').value = '';
        renderItems();
      });

      // Guarda valor inicial
      tipoVendaEl.dataset.valorAnterior = tipoVendaEl.value;
    }

    function renderItems() {
      const tbody    = document.getElementById('items_body');
      const emptyRow = document.getElementById('empty_row');

      if (items.length === 0) {
        tbody.innerHTML = '';
        tbody.appendChild(emptyRow);
        emptyRow.classList.remove('d-none');
        atualizarTotais();
        return;
      }

      tbody.innerHTML = '';
      items.forEach((item, idx) => {
        const subtotal = item.quantidade * item.preco;
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="fw-semibold small">${item.nome}</td>
          <td class="text-center" style="width:150px">
            <div class="input-group input-group-sm">
              <button type="button" class="btn btn-outline-secondary btn-qtd-minus" data-idx="${idx}">−</button>
              <input type="number" class="form-control text-center btn-qtd-input"
                     value="${item.quantidade}" min="1" data-idx="${idx}" style="width:55px">
              <button type="button" class="btn btn-outline-secondary btn-qtd-plus" data-idx="${idx}">+</button>
            </div>
          </td>
          <td class="text-end text-muted small">${formatMoedaBR(item.preco)}</td>
          <td class="text-end fw-semibold">${formatMoedaBR(subtotal)}</td>
          <td class="text-end">
            <button type="button" class="btn btn-sm btn-link text-danger p-0 btn-remove" data-idx="${idx}">
              <i class="bi bi-trash"></i>
            </button>
          </td>
        `;
        tbody.appendChild(tr);
      });

      tbody.querySelectorAll('.btn-qtd-minus').forEach(btn => {
        btn.addEventListener('click', function () {
          const idx = parseInt(this.dataset.idx);
          if (items[idx].quantidade > 1) { items[idx].quantidade--; renderItems(); }
        });
      });

      tbody.querySelectorAll('.btn-qtd-plus').forEach(btn => {
        btn.addEventListener('click', function () {
          items[parseInt(this.dataset.idx)].quantidade++;
          renderItems();
        });
      });

      tbody.querySelectorAll('.btn-qtd-input').forEach(input => {
        input.addEventListener('change', function () {
          const idx = parseInt(this.dataset.idx);
          const val = parseInt(this.value) || 1;
          items[idx].quantidade = val < 1 ? 1 : val;
          renderItems();
        });
      });

      tbody.querySelectorAll('.btn-remove').forEach(btn => {
        btn.addEventListener('click', function () {
          items.splice(parseInt(this.dataset.idx), 1);
          renderItems();
        });
      });

      atualizarTotais();
    }

    function atualizarTotais() {
      const subtotal = items.reduce((s, i) => s + i.quantidade * i.preco, 0);
      const desconto = parseMoeda(document.getElementById('id_desconto').value);
      const frete    = parseMoeda(document.getElementById('id_frete').value);
      const total    = subtotal - desconto + frete;

      document.getElementById('total_produtos').textContent = formatMoeda(subtotal);
      document.getElementById('total_frete').textContent    = formatMoeda(frete);
      document.getElementById('total_geral').textContent    = formatMoeda(total > 0 ? total : 0);
    }

    document.getElementById('btn_add_item').addEventListener('click', function () {
      if (!produtoSelecionado) { alert('Selecione um produto.'); return; }

      const preco = parseMoeda(document.getElementById('id_preco_add').value);
      if (preco <= 0 && !isGratuito()) {
        alert('Este produto não tem preço cadastrado. Cadastre um preço antes de adicionar.');
        return;
      }

      const existing = items.find(i => i.id === produtoSelecionado.value);
      if (existing) {
        existing.quantidade += 1;
      } else {
        items.push({ id: produtoSelecionado.value, nome: produtoSelecionado.nome, quantidade: 1, preco });
      }

      tsProduto.clear();
      tsProduto.clearOptions();
      produtoSelecionado = null;
      document.getElementById('id_preco_add').value = '';
      renderItems();
    });

    const descontoEl = document.getElementById('id_desconto');
    const freteEl    = document.getElementById('id_frete');
    if (descontoEl) descontoEl.addEventListener('input', atualizarTotais);
    if (freteEl)    freteEl.addEventListener('input', atualizarTotais);

    document.getElementById('form-pedido').addEventListener('submit', function (e) {
      if (items.length === 0) {
        e.preventDefault();
        alert('Adicione pelo menos um produto ao pedido.');
        return;
      }
      document.getElementById('items_json_field').value = JSON.stringify(items);
    });

    renderItems();
  }

  // ══════════════════════════════════════════
  // EDIÇÃO — itens via AJAX
  // ══════════════════════════════════════════
  const editItemsBody = document.getElementById('edit_items_body');
  const formAddItem   = document.getElementById('form-add-item');
  const pedidoPk      = formAddItem ? formAddItem.dataset.pedidoPk : null;
  let produtoEditSelecionado = null;

  if (document.getElementById('id_produto_search_edit')) {
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
  }

  function atualizarTabelaEdit(itens, totais) {
    if (!editItemsBody) return;
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
    if (!editItemsBody) return;

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

  if (editItemsBody) bindEditListeners();
});