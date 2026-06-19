document.addEventListener('DOMContentLoaded', () => {

  const dataEl = document.getElementById('corte-data');
  const data = JSON.parse(dataEl.textContent);
  const MATERIAIS = data.materiais;
  const PRODUTOS_FINAIS = data.produtos;

  const pedidoProdutosEl = document.getElementById('pedido-produtos');
  const PRODUTOS_PEDIDO = pedidoProdutosEl ? JSON.parse(pedidoProdutosEl.textContent) : [];

  let chapaCount = 0;

  function initTomSelect(el, lista) {
    const options = lista.map(p => ({
      value: p.id,
      text: p.nome,
      codigo: p.codigo || '',
    }));

    return new TomSelect(el, {
      options: options,
      placeholder: 'Buscar...',
      searchField: ['text', 'codigo'],
      maxOptions: 50,
      render: {
        option: (data) => `<div class="ts-option">${data.text}</div>`,
        item:   (data) => `<div>${data.text}</div>`,
      }
    });
  }

  function addChapa() {
    const ci = chapaCount++;
    const chapaDiv = document.createElement('div');
    chapaDiv.className = 'chapa-block mb-3 border rounded-3 p-3';
    chapaDiv.dataset.chapaIdx = ci;

    chapaDiv.innerHTML = `
      <div class="d-flex align-items-center gap-2 mb-3">
        <span class="text-muted fw-semibold small text-uppercase">Chapa</span>
        <div class="col">
          <select id="chapa-select-${ci}" name="entrada_produto_${ci}" required></select>
        </div>
        <div style="width:90px">
          <input type="number" name="entrada_quantidade_${ci}"
                 class="form-control" placeholder="Qtd" min="1" step="1" required>
        </div>
        <button type="button" class="btn btn-outline-danger btn-sm"
                onclick="this.closest('.chapa-block').remove()">✕</button>
      </div>

      <div class="ps-3 border-start border-2 border-success-subtle">
        <p class="text-muted small fw-semibold mb-2">PRODUTOS CORTADOS DESTA CHAPA</p>
        <div class="saidas-list" data-chapa-idx="${ci}" data-prod-count="0"></div>
        <button type="button" class="btn btn-sm btn-outline-success mt-1"
                onclick="window.addProduto(this, ${ci})">+ produto</button>
      </div>
    `;

    document.getElementById('chapas-container').appendChild(chapaDiv);
    initTomSelect(document.getElementById(`chapa-select-${ci}`), MATERIAIS);

    return chapaDiv;
  }

  function addProduto(btn, chapaIdx, produtoId = null, quantidade = null) {
    const lista = btn.previousElementSibling;
    const pi    = parseInt(lista.dataset.prodCount);
    lista.dataset.prodCount = pi + 1;

    const div = document.createElement('div');
    div.className = 'row g-2 mb-2 align-items-center';
    const selectId = `produto-select-${chapaIdx}-${pi}`;

    div.innerHTML = `
      <div class="col">
        <select id="${selectId}" name="saida_chapa_${chapaIdx}_produto_${pi}" required></select>
      </div>
      <div class="col-3">
        <input type="number" name="saida_chapa_${chapaIdx}_quantidade_${pi}"
               class="form-control" placeholder="Qtd" min="1" step="1"
               value="${quantidade || ''}" required>
      </div>
      <div class="col-auto">
        <button type="button" class="btn btn-outline-danger btn-sm"
                onclick="this.closest('.row').remove()">✕</button>
      </div>
    `;
    lista.appendChild(div);

    const ts = initTomSelect(document.getElementById(selectId), PRODUTOS_FINAIS);

    // Pré-seleciona o produto se fornecido
    if (produtoId) {
      ts.setValue(String(produtoId));
    }
  }

  window.addProduto = addProduto;
  document.getElementById('btn-add-chapa').addEventListener('click', addChapa);

  // ── Pré-preenche produtos do pedido ──
  if (PRODUTOS_PEDIDO.length > 0) {
    // Cria uma chapa por padrão e preenche os produtos do pedido nela
    const chapaDiv = addChapa();
    const ci       = parseInt(chapaDiv.dataset.chapaIdx);
    const btn      = chapaDiv.querySelector('.btn-outline-success');

    // Remove o produto vazio que foi adicionado automaticamente pelo addChapa
    chapaDiv.querySelector('.saidas-list').innerHTML = '';
    chapaDiv.querySelector('.saidas-list').dataset.prodCount = '0';

    // Adiciona um produto por item do pedido
    PRODUTOS_PEDIDO.forEach(item => {
      addProduto(btn, ci, item.id, item.quantidade);
    });
  } else {
    // Corte avulso — começa com uma chapa vazia e um produto vazio
    const chapaDiv = addChapa();
    const ci       = parseInt(chapaDiv.dataset.chapaIdx);
    addProduto(chapaDiv.querySelector('.btn-outline-success'), ci);
  }
});