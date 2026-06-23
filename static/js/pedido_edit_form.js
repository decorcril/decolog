document.addEventListener('DOMContentLoaded', function () {

  const TIPOS_GRATUITOS = ['exchange', 'replacement', 'advertising', 'comodato'];

  // ── Helpers ──
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
    fetch(url, { method: 'POST', body, headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(r => r.json())
      .then(data => { if (data.ok) callback(data); })
      .catch(e => console.error(e));
  }

  const editItemsBody = document.getElementById('edit_items_body');
  const formAddItem   = document.getElementById('form-add-item');
  const pedidoPk      = formAddItem?.dataset.pedidoPk;
  const freteEl       = document.getElementById('id_frete');
  const descontoEl    = document.getElementById('id_desconto_edit');

  let produtoEditSelecionado = null;

  // ── Totais ──
  function atualizarTotaisEdit() {
    const tpEl = document.getElementById('edit_total_produtos');
    const tgEl = document.getElementById('edit_total_geral');
    if (!tpEl || !tgEl) return;

    const totalProdutos = parseMoeda(tpEl.textContent.replace('R$', '').trim());
    const frete         = parseMoeda(freteEl?.value);
    const desconto      = parseMoeda(descontoEl?.value);
    const total         = Math.max(0, totalProdutos - desconto + frete);

    tgEl.textContent = formatMoedaBR(total);

    const totalFreteEl = document.getElementById('edit_total_frete');
    if (totalFreteEl) totalFreteEl.textContent = formatMoedaBR(frete);
  }

  // ── Listeners frete e desconto ──
  if (freteEl) {
    freteEl.addEventListener('input',  atualizarTotaisEdit);
    freteEl.addEventListener('change', () => setTimeout(atualizarTotaisEdit, 50));
  }
  if (descontoEl) {
    descontoEl.addEventListener('input',  atualizarTotaisEdit);
    descontoEl.addEventListener('change', () => setTimeout(atualizarTotaisEdit, 50));
  }

  // ── Tom Select: Produto ──
  if (document.getElementById('id_produto_search_edit')) {
    const tsProdutoEdit = new TomSelect('#id_produto_search_edit', {
      valueField:  'value',
      labelField:  'text',
      searchField: ['text'],
      placeholder: 'Pesquisar produto...',
      load: function (query, callback) {
        if (!query.length) return callback();
        fetch(`/vendas/autocomplete/produtos/?q=${encodeURIComponent(query)}&tipo_venda=${getTipoVenda()}`)
          .then(r => r.json())
          .then(data => callback(data.results))
          .catch(() => callback());
      },
      minChars:   2,
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

    // ── Tipo de venda: limpa produto e zera preços se gratuito ──
    const tipoVendaEl = document.querySelector('[name="tipo_venda"]');
    if (tipoVendaEl) {
      tipoVendaEl.addEventListener('change', function () {
        tsProdutoEdit.clear();
        tsProdutoEdit.clearOptions();
        produtoEditSelecionado = null;
        document.getElementById('id_preco_edit').value = '';

        if (isGratuito() && editItemsBody) {
          editItemsBody.querySelectorAll('tr').forEach(tr => {
            const itemPk = tr.dataset.itemPk;
            if (!itemPk) return;
            ajaxPost(`/vendas/${pedidoPk}/itens/${itemPk}/atualizar/`, {
              quantidade:     tr.querySelector('.input-edit-qtd')?.value || 1,
              preco_unitario: '0.00',
            }, data => atualizarTabelaEdit(data.itens, data.totais));
          });
        }
      });
    }

    // ── Adicionar produto ──
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
        document.getElementById('edit_qtd').value      = 1;
      });
    });
  }

  // ── Render tabela de itens ──
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

    atualizarTotaisEdit();
    bindEditListeners();
  }

  // ── Listeners da tabela ──
  function bindEditListeners() {
    if (!editItemsBody) return;

    editItemsBody.querySelectorAll('.btn-edit-minus').forEach(btn => {
      btn.addEventListener('click', function () {
        const qtd = Math.max(1, parseInt(this.dataset.qtd) - 1);
        ajaxPost(`/vendas/${pedidoPk}/itens/${this.dataset.itemPk}/atualizar/`,
          { quantidade: qtd },
          data => atualizarTabelaEdit(data.itens, data.totais)
        );
      });
    });

    editItemsBody.querySelectorAll('.btn-edit-plus').forEach(btn => {
      btn.addEventListener('click', function () {
        const qtd = parseInt(this.dataset.qtd) + 1;
        ajaxPost(`/vendas/${pedidoPk}/itens/${this.dataset.itemPk}/atualizar/`,
          { quantidade: qtd },
          data => atualizarTabelaEdit(data.itens, data.totais)
        );
      });
    });

    editItemsBody.querySelectorAll('.input-edit-qtd').forEach(input => {
      input.addEventListener('change', function () {
        const qtd = Math.max(1, parseInt(this.value) || 1);
        ajaxPost(`/vendas/${pedidoPk}/itens/${this.dataset.itemPk}/atualizar/`,
          { quantidade: qtd },
          data => atualizarTabelaEdit(data.itens, data.totais)
        );
      });
    });

    editItemsBody.querySelectorAll('.btn-edit-remove').forEach(btn => {
      btn.addEventListener('click', function () {
        ajaxPost(`/vendas/${pedidoPk}/itens/${this.dataset.itemPk}/remover/`,
          {},
          data => atualizarTabelaEdit(data.itens, data.totais)
        );
      });
    });
  }

  if (editItemsBody) bindEditListeners();
});