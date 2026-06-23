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

  // ── Tom Select: Cliente ──
  if (document.getElementById('id_cliente')) {
    new TomSelect('#id_cliente', {
      valueField:  'value',
      labelField:  'text',
      searchField: ['text'],
      placeholder: 'Pesquisar cliente...',
      load: function (query, callback) {
        if (!query.length) return callback();
        fetch(`/vendas/autocomplete/clientes/?q=${encodeURIComponent(query)}`)
          .then(r => r.json())
          .then(data => callback(data.results))
          .catch(() => callback());
      },
      minChars:   2,
      shouldLoad: q => q.length >= 2,
    });
  }

  // ── Criação de pedido ──
  if (!document.getElementById('id_produto_search')) return;

  let produtoSelecionado = null;
  let items              = [];

  const freteEl    = document.getElementById('id_frete');
  const descontoEl = document.getElementById('id_desconto');

  // ── Tom Select: Produto ──
  const tsProduto = new TomSelect('#id_produto_search', {
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
      const option = tsProduto.options[value];
      if (option) {
        produtoSelecionado = option;
        const preco = isGratuito() ? 0 : parseFloat(option.preco || 0);
        document.getElementById('id_preco_add').value = formatMoeda(preco);
      }
    },
  });

  // ── Tipo de venda: limpa itens ao trocar ──
  const tipoVendaEl = document.querySelector('[name="tipo_venda"]');
  if (tipoVendaEl) {
    tipoVendaEl.dataset.valorAnterior = tipoVendaEl.value;
    tipoVendaEl.addEventListener('change', function () {
      if (items.length > 0) {
        const confirma = confirm('Ao trocar o tipo de venda os itens adicionados serão removidos. Deseja continuar?');
        if (!confirma) {
          this.value = this.dataset.valorAnterior || '';
          return;
        }
        items = [];
      }
      this.dataset.valorAnterior = this.value;
      tsProduto.clear();
      tsProduto.clearOptions();
      produtoSelecionado = null;
      document.getElementById('id_preco_add').value = '';
      renderItems();
    });
  }

  // ── Totais ──
  function atualizarTotais() {
    const subtotal = items.reduce((s, i) => s + i.quantidade * i.preco, 0);
    const desconto = parseMoeda(descontoEl?.value);
    const frete    = parseMoeda(freteEl?.value);
    const total    = Math.max(0, subtotal - desconto + frete);

    document.getElementById('total_produtos').textContent = formatMoeda(subtotal);
    document.getElementById('total_frete').textContent    = formatMoeda(frete);
    document.getElementById('total_geral').textContent    = formatMoeda(total);
  }

  // ── Render da tabela de itens ──
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
      const tr       = document.createElement('tr');
      tr.innerHTML = `
        <td class="fw-semibold small">${item.nome}</td>
        <td class="text-center" style="width:150px">
          <div class="input-group input-group-sm">
            <button type="button" class="btn btn-outline-secondary btn-qtd-minus" data-idx="${idx}"
                    ${item.quantidade <= 1 ? 'disabled' : ''}>−</button>
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

  // ── Adicionar produto ──
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
      items.push({
        id:         produtoSelecionado.value,
        nome:       produtoSelecionado.nome || produtoSelecionado.text,
        quantidade: 1,
        preco,
      });
    }

    tsProduto.clear();
    tsProduto.clearOptions();
    produtoSelecionado = null;
    document.getElementById('id_preco_add').value = '';
    renderItems();
  });

  // ── Listeners frete e desconto — change + input para garantir atualização ──
  if (freteEl) {
    freteEl.addEventListener('input',  atualizarTotais);
    freteEl.addEventListener('change', () => setTimeout(atualizarTotais, 50));
  }
  if (descontoEl) {
    descontoEl.addEventListener('input',  atualizarTotais);
    descontoEl.addEventListener('change', () => setTimeout(atualizarTotais, 50));
  }

  // ── Submit: serializa itens ──
  document.getElementById('form-pedido').addEventListener('submit', function (e) {
    if (items.length === 0) {
      e.preventDefault();
      alert('Adicione pelo menos um produto ao pedido.');
      return;
    }
    document.getElementById('items_json_field').value = JSON.stringify(items);
  });

  renderItems();
});