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

});