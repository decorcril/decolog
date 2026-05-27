document.addEventListener('DOMContentLoaded', () => {

  const produtoEl = document.getElementById('id_produto');
  if (produtoEl) {
    new TomSelect(produtoEl, {
      placeholder: 'Buscar por nome ou código...',
      searchField: ['text'],
      maxOptions: 50,
      render: {
        option: function(data) {
          return `<div class="ts-option">${data.text}</div>`;
        },
        item: function(data) {
          return `<div>${data.text}</div>`;
        }
      }
    });
  }

  const fornecedorEl = document.getElementById('id_fornecedor');
  if (fornecedorEl) {
    new TomSelect(fornecedorEl, {
      placeholder: 'Selecione um fornecedor...',
      allowEmptyOption: true,
    });
  }

  const localEl = document.getElementById('id_local');
  if (localEl) {
    new TomSelect(localEl, {
      placeholder: 'Selecione um local...',
    });
  }

});