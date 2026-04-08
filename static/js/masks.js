function maskTelefone(v) {
  v = v.replace(/\D/g, '');
  if (v.length === 0) return '';
  if (v.length <= 10) {
    v = v.replace(/^(\d{2})(\d{4})(\d{0,4}).*/, '($1) $2-$3');
  } else {
    v = v.replace(/^(\d{2})(\d{5})(\d{0,4}).*/, '($1) $2-$3');
  }
  return v;
}

function maskDocumento(v) {
  v = v.replace(/\D/g, '');
  if (v.length === 0) return '';
  if (v.length <= 11) {
    v = v.replace(/^(\d{3})(\d{0,3})/, '$1.$2');
    v = v.replace(/^(\d{3})\.(\d{3})(\d{0,3})/, '$1.$2.$3');
    v = v.replace(/^(\d{3})\.(\d{3})\.(\d{3})(\d{0,2})/, '$1.$2.$3-$4');
  } else {
    v = v.replace(/^(\d{2})(\d{0,3})/, '$1.$2');
    v = v.replace(/^(\d{2})\.(\d{3})(\d{0,3})/, '$1.$2.$3');
    v = v.replace(/^(\d{2})\.(\d{3})\.(\d{3})(\d{0,4})/, '$1.$2.$3/$4');
    v = v.replace(/^(\d{2})\.(\d{3})\.(\d{3})\/(\d{4})(\d{0,2})/, '$1.$2.$3/$4-$5');
  }
  return v;
}

function applyMask(input, maskFn) {
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace' || e.key === 'Delete') {
      // Remove último dígito numérico ao apagar
      let pos = input.selectionStart;
      let v = input.value;
      // Se o caractere antes do cursor é separador, pula ele
      while (pos > 0 && /\D/.test(v[pos - 1])) {
        pos--;
      }
      if (pos > 0) {
        input.value = v.slice(0, pos - 1) + v.slice(pos);
        input.setSelectionRange(pos - 1, pos - 1);
      }
      e.preventDefault();
      input.value = maskFn(input.value);
    }
  });

  input.addEventListener('input', (e) => {
    if (e.inputType === 'deleteContentBackward' || e.inputType === 'deleteContentForward') return;
    const pos = input.selectionStart;
    const prev = input.value.length;
    input.value = maskFn(input.value);
    const diff = input.value.length - prev;
    input.setSelectionRange(pos + diff, pos + diff);
  });
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('input[name="telefone"]').forEach(input => {
    applyMask(input, maskTelefone);
  });
  document.querySelectorAll('input[name="documento"]').forEach(input => {
    applyMask(input, maskDocumento);
  });
});