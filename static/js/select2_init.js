$(document).ready(function() {
  // Busca por nome e código no campo produto
  $('#id_produto').select2({
    placeholder: 'Buscar por nome ou código...',
    allowClear: true,
    language: {
      noResults: () => 'Nenhum produto encontrado',
      searching: () => 'Buscando...',
    }
  });

  // Select2 simples para fornecedor
  $('#id_fornecedor').select2({
    placeholder: 'Selecione um fornecedor...',
    allowClear: true,
    language: {
      noResults: () => 'Nenhum fornecedor encontrado',
    }
  });
});