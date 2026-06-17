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

  function lerDimensoesDaTela() {
    document.querySelectorAll('.dim-input').forEach(input => {
      const idx = parseInt(input.dataset.idx);
      const dim = input.dataset.dim;
      if (items[idx] !== undefined) {
        items[idx][dim] = parseFloat(input.value) || 0;
      }
    });
  }

  function setFrete(preco) {
    const freteEl = document.getElementById('id_frete');
    if (freteEl) {
      // Atualiza o campo com máscara
      freteEl.value = formatMoeda(preco);
      // Dispara o evento input para a máscara processar
      freteEl.dispatchEvent(new Event('input'));
    }
    const totalFreteEl = document.getElementById('total_frete');
    if (totalFreteEl) totalFreteEl.textContent = formatMoeda(preco);
  }

  // ── Tom Select: Cliente ──
  let clienteSelecionado = null;

  const tsCliente = new TomSelect('#id_cliente', {
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
    onItemAdd: function (value) {
      const option = tsCliente.options[value];
      if (option) {
        clienteSelecionado = option;
        if (option.cep) {
          document.getElementById('cep_destino').value = option.cep;
        }
      }
    },
  });

  // ── Tom Select: Produto ──
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

  // ── Itens ──
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
        <td class="text-end">
          <input type="number" class="form-control form-control-sm text-end dim-input"
                 value="${item.peso || ''}" min="0" step="0.01"
                 placeholder="kg" data-idx="${idx}" data-dim="peso"
                 style="width:75px; margin-left:auto;">
        </td>
        <td class="text-end">
          <input type="number" class="form-control form-control-sm text-end dim-input"
                 value="${item.largura || ''}" min="0" step="0.1"
                 placeholder="cm" data-idx="${idx}" data-dim="largura"
                 style="width:75px; margin-left:auto;">
        </td>
        <td class="text-end">
          <input type="number" class="form-control form-control-sm text-end dim-input"
                 value="${item.altura || ''}" min="0" step="0.1"
                 placeholder="cm" data-idx="${idx}" data-dim="altura"
                 style="width:75px; margin-left:auto;">
        </td>
        <td class="text-end">
          <input type="number" class="form-control form-control-sm text-end dim-input"
                 value="${item.comprimento || ''}" min="0" step="0.1"
                 placeholder="cm" data-idx="${idx}" data-dim="comprimento"
                 style="width:75px; margin-left:auto;">
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
        lerDimensoesDaTela();
        const idx = parseInt(this.dataset.idx);
        if (items[idx].quantidade > 1) { items[idx].quantidade--; renderItems(); }
      });
    });

    tbody.querySelectorAll('.btn-qtd-plus').forEach(btn => {
      btn.addEventListener('click', function () {
        lerDimensoesDaTela();
        items[parseInt(this.dataset.idx)].quantidade++;
        renderItems();
      });
    });

    tbody.querySelectorAll('.btn-qtd-input').forEach(input => {
      input.addEventListener('change', function () {
        lerDimensoesDaTela();
        const idx = parseInt(this.dataset.idx);
        items[idx].quantidade = Math.max(1, parseInt(this.value) || 1);
        renderItems();
      });
    });

    tbody.querySelectorAll('.dim-input').forEach(input => {
      input.addEventListener('change', function () {
        const idx = parseInt(this.dataset.idx);
        const dim = this.dataset.dim;
        if (items[idx] !== undefined) {
          items[idx][dim] = parseFloat(this.value) || 0;
        }
      });
    });

    tbody.querySelectorAll('.btn-remove').forEach(btn => {
      btn.addEventListener('click', function () {
        lerDimensoesDaTela();
        items.splice(parseInt(this.dataset.idx), 1);
        renderItems();
      });
    });

    atualizarTotais();
  }

  function atualizarTotais() {
    const subtotal = items.reduce((s, i) => s + i.quantidade * i.preco, 0);
    const desconto = parseMoeda(document.getElementById('id_desconto')?.value || '0');
    const frete    = parseMoeda(document.getElementById('id_frete')?.value || '0');
    const total    = subtotal - desconto + frete;

    document.getElementById('total_produtos').textContent = formatMoeda(subtotal);
    const totalFreteEl = document.getElementById('total_frete');
    if (totalFreteEl) totalFreteEl.textContent = formatMoeda(frete);
    document.getElementById('total_geral').textContent = formatMoeda(total > 0 ? total : 0);
  }

  // ── Adicionar item ──
  document.getElementById('btn_add_item').addEventListener('click', function () {
    if (!produtoSelecionado) { alert('Selecione um produto.'); return; }

    const preco = parseMoeda(document.getElementById('id_preco_add').value);
    if (preco <= 0 && !isGratuito()) {
      alert('Este produto não tem preço cadastrado. Cadastre um preço antes de adicionar.');
      return;
    }

    const existing = items.find(i => i.id === produtoSelecionado.value);
    if (existing) {
      lerDimensoesDaTela();
      existing.quantidade += 1;
    } else {
      items.push({
        id:          produtoSelecionado.value,
        nome:        produtoSelecionado.nome,
        quantidade:  1,
        preco:       preco,
        peso:        0,
        largura:     0,
        altura:      0,
        comprimento: 0,
      });
    }

    tsProduto.clear();
    tsProduto.clearOptions();
    produtoSelecionado = null;
    document.getElementById('id_preco_add').value = '';
    renderItems();
  });

  document.getElementById('id_desconto').addEventListener('input', atualizarTotais);
  document.getElementById('id_frete').addEventListener('input', atualizarTotais);

  // ── Calcular Frete ──
  document.getElementById('btn_calcular_frete').addEventListener('click', function () {
    const cep = document.getElementById('cep_destino').value.replace(/\D/g, '');

    if (!cep || cep.length !== 8) {
      alert('Selecione um cliente com CEP cadastrado para calcular o frete.');
      return;
    }

    if (items.length === 0) {
      alert('Adicione produtos antes de calcular o frete.');
      return;
    }

    lerDimensoesDaTela();

    const itensSemDimensao = items.filter(i =>
      !i.peso || !i.largura || !i.altura || !i.comprimento
    );
    if (itensSemDimensao.length > 0) {
      alert('Informe peso, largura, altura e comprimento de todos os produtos.');
      return;
    }

    const btn = this;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Calculando...';

    const produtos = items.map(item => ({
      id:            String(item.id),
      width:         item.largura,
      height:        item.altura,
      length:        item.comprimento,
      weight:        item.peso,
      quantity:      item.quantidade,
      unitary_value: item.preco,
    }));

    fetch('/vendas/frete/calcular/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
      },
      body: JSON.stringify({ cep_destino: cep, produtos }),
    })
    .then(r => r.json())
    .then(data => {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-truck me-1"></i> Calcular Frete';

      const container = document.getElementById('frete_opcoes');

      if (!data.ok) {
        container.innerHTML = `<div class="alert alert-danger small py-2">${data.erro}</div>`;
        return;
      }

      if (!data.opcoes.length) {
        container.innerHTML = '<div class="alert alert-warning small py-2">Nenhuma opção de frete disponível.</div>';
        return;
      }

      container.innerHTML = data.opcoes.map(op => `
        <div class="card mb-2 frete-opcao" style="cursor:pointer"
             data-preco="${op.preco}"
             data-transportadora="${(op.transportadora || '') + ' — ' + (op.nome || '')}">
          <div class="card-body p-3 d-flex justify-content-between align-items-center">
            <div class="d-flex align-items-center gap-3">
              ${op.logo ? `<img src="${op.logo}" height="24" alt="${op.transportadora}">` : ''}
              <div>
                <p class="fw-semibold mb-0 small">${op.transportadora} — ${op.nome}</p>
                <p class="text-muted mb-0 small">Prazo: ${op.prazo} dia(s)</p>
              </div>
            </div>
            <span class="fw-bold text-primary">R$ ${parseFloat(op.preco).toFixed(2).replace('.', ',')}</span>
          </div>
        </div>
      `).join('');

      container.querySelectorAll('.frete-opcao').forEach(card => {
        card.addEventListener('click', function () {
          const preco              = parseFloat(this.dataset.preco);
          const nomeTransportadora = this.dataset.transportadora;
          setFrete(preco);
          atualizarTotais();
          const el = document.getElementById('id_transportadora_frete');
          if (el) el.value = nomeTransportadora;
          container.querySelectorAll('.frete-opcao').forEach(c => c.classList.remove('border-primary'));
          this.classList.add('border-primary');
        });
      });
    })
    .catch(() => {
      btn.disabled = false;
      btn.innerHTML = '<i class="bi bi-truck me-1"></i> Calcular Frete';
      document.getElementById('frete_opcoes').innerHTML =
        '<div class="alert alert-danger small py-2">Erro ao calcular frete. Tente novamente.</div>';
    });
  });

  // ── Submit ──
  document.getElementById('form-orcamento').addEventListener('submit', function (e) {
    if (items.length === 0) {
      e.preventDefault();
      alert('Adicione pelo menos um produto ao orçamento.');
      return;
    }
    lerDimensoesDaTela();
    document.getElementById('items_json_field').value = JSON.stringify(items);
  });

  renderItems();
});