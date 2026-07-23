document.addEventListener('DOMContentLoaded', () => {

  const dataEl = document.getElementById('corte-data');
  const data = JSON.parse(dataEl.textContent);
  const MATERIAIS = data.materiais;
  const PRODUTOS_FINAIS = data.produtos;

  const pedidoProdutosEl = document.getElementById('pedido-produtos');
  const PRODUTOS_PEDIDO = pedidoProdutosEl ? JSON.parse(pedidoProdutosEl.textContent) : [];

  const container   = document.getElementById('produtos-container');
  const contadorEl   = document.getElementById('produtos-count');

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

  // ── Renumera tudo após qualquer inclusão/remoção, evitando índices "com
  //     buraco" que fariam o servidor perder dados silenciosamente ──
  function renumerar() {
    const produtos = container.querySelectorAll('.produto-block');

    produtos.forEach((produtoDiv, pi) => {
      produtoDiv.querySelector('.produto-numero').textContent = pi + 1;
      produtoDiv.querySelector('.produto-select').name = `produto_produto_${pi}`;
      produtoDiv.querySelector('.produto-qtd').name    = `produto_quantidade_${pi}`;

      const chapasList = produtoDiv.querySelector('.chapas-list');
      const linhas = chapasList.querySelectorAll('.chapa-linha');

      linhas.forEach((linha, ci) => {
        linha.querySelector('.chapa-select').name = `produto_chapa_${pi}_produto_${ci}`;
        linha.querySelector('.chapa-qtd').name    = `produto_chapa_${pi}_quantidade_${ci}`;
      });
    });

    contadorEl.textContent = produtos.length;
  }

  function addProduto(produtoId = null, quantidade = null) {
    const produtoDiv = document.createElement('div');
    produtoDiv.className = 'produto-block mb-3 border rounded-3 p-3';

    produtoDiv.innerHTML = `
      <div class="d-flex align-items-center gap-2 mb-3">
        <span class="badge bg-success rounded-pill">
          Produto <span class="produto-numero">?</span>
        </span>
        <div class="col">
          <select class="produto-select" required></select>
        </div>
        <div style="width:90px">
          <input type="number" class="form-control produto-qtd" placeholder="Qtd" min="1" step="1"
                 value="${quantidade || ''}" required>
        </div>
        <button type="button" class="btn btn-outline-secondary btn-sm btn-duplicar-produto" title="Duplicar este produto">
          <i class="bi bi-files"></i>
        </button>
        <button type="button" class="btn btn-outline-danger btn-sm btn-remover-produto" title="Remover produto">✕</button>
      </div>

      <div class="ps-3 border-start border-2 border-primary-subtle">
        <p class="text-muted small fw-semibold mb-2">CHAPAS USADAS NESTE PRODUTO</p>
        <div class="chapas-list"></div>
        <button type="button" class="btn btn-sm btn-outline-primary mt-1 btn-add-chapa">+ chapa</button>
      </div>
    `;

    container.appendChild(produtoDiv);
    const ts = initTomSelect(produtoDiv.querySelector('.produto-select'), PRODUTOS_FINAIS);
    if (produtoId) ts.setValue(String(produtoId));

    produtoDiv.querySelector('.btn-add-chapa').addEventListener('click', () => addChapa(produtoDiv));
    produtoDiv.querySelector('.btn-remover-produto').addEventListener('click', () => {
      produtoDiv.remove();
      renumerar();
    });
    produtoDiv.querySelector('.btn-duplicar-produto').addEventListener('click', () => duplicarProduto(produtoDiv));

    renumerar();
    return produtoDiv;
  }

  function addChapa(produtoDiv, chapaId = null, quantidade = null) {
    const lista = produtoDiv.querySelector('.chapas-list');

    const div = document.createElement('div');
    div.className = 'row g-2 mb-2 align-items-center chapa-linha';
    div.innerHTML = `
      <div class="col">
        <select class="chapa-select" required></select>
      </div>
      <div class="col-3">
        <input type="number" class="form-control chapa-qtd" placeholder="Qtd" min="1" step="1"
               value="${quantidade || ''}" required>
      </div>
      <div class="col-auto">
        <button type="button" class="btn btn-outline-danger btn-sm btn-remover-chapa">✕</button>
      </div>
    `;
    lista.appendChild(div);

    const ts = initTomSelect(div.querySelector('.chapa-select'), MATERIAIS);
    if (chapaId) ts.setValue(String(chapaId));

    div.querySelector('.btn-remover-chapa').addEventListener('click', () => {
      div.remove();
      renumerar();
    });

    renumerar();
  }

  // ── Duplica um produto inteiro (seleção + chapas), útil quando o mesmo
  //     produto se repete no mesmo corte ──
  function duplicarProduto(produtoDivOriginal) {
    const tsOriginal = produtoDivOriginal.querySelector('.produto-select').tomselect;
    const qtdOriginal = produtoDivOriginal.querySelector('.produto-qtd').value;

    const novoProduto = addProduto(
      tsOriginal ? tsOriginal.getValue() : null,
      qtdOriginal
    );

    const linhasOriginais = produtoDivOriginal.querySelectorAll('.chapa-linha');
    linhasOriginais.forEach(linha => {
      const tsChapa = linha.querySelector('.chapa-select').tomselect;
      const qtd     = linha.querySelector('.chapa-qtd').value;
      addChapa(novoProduto, tsChapa ? tsChapa.getValue() : null, qtd);
    });

    renumerar();
  }

  document.getElementById('btn-add-produto').addEventListener('click', () => {
    const produtoDiv = addProduto();
    addChapa(produtoDiv);
  });

  // ── Pré-preenche produtos do pedido, cada um já com uma linha de chapa vazia ──
  if (PRODUTOS_PEDIDO.length > 0) {
    PRODUTOS_PEDIDO.forEach(item => {
      const produtoDiv = addProduto(item.id, item.quantidade);
      addChapa(produtoDiv);
    });
  } else {
    const produtoDiv = addProduto();
    addChapa(produtoDiv);
  }
});