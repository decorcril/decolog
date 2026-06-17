document.addEventListener('DOMContentLoaded', function () {
  const produtoSelect = document.querySelector('select[name="produto"]');
  const precoInput    = document.getElementById('preco_unitario');

  if (produtoSelect && precoInput) {
    produtoSelect.addEventListener('change', function () {
      const option = this.options[this.selectedIndex];
      const preco  = option.getAttribute('data-preco') || '0';
      const num    = parseFloat(preco);
      precoInput.value = !isNaN(num) ? num.toFixed(2).replace('.', ',') : '';
    });
  }
});