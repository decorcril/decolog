document.addEventListener('DOMContentLoaded', function () {
  const paisSelect = document.getElementById('id_pais');
  if (!paisSelect) return;

  const camposBR   = document.getElementById('campos_br');
  const camposIntl = document.getElementById('campos_intl');
  const cep        = document.getElementById('id_cep');
  const tipoPessoa = document.getElementById('id_tipo_pessoa');
  const labelDoc   = document.getElementById('label_documento');

  const itiConfig = {
    initialCountry: paisSelect.value.toLowerCase() || 'br',
    separateDialCode: true,
    preferredCountries: ['br', 'ar', 'cl', 'py', 'uy', 'us'],
    utilsScript: 'https://cdn.jsdelivr.net/npm/intl-tel-input@23/build/js/utils.js',
  };

  window.intlTelInput(document.getElementById('id_telefone'), itiConfig);
  window.intlTelInput(document.getElementById('id_whatsapp'), itiConfig);

  const formEl = document.getElementById('form-cliente');

  formEl.addEventListener('submit', function (e) {
    e.preventDefault();
    const form = this;

    const telEl = document.getElementById('id_telefone');
    const waEl  = document.getElementById('id_whatsapp');

    const instances = window.intlTelInput.instances;
    const itiTel = Object.values(instances).find(i => i.a === telEl);
    const itiWa  = Object.values(instances).find(i => i.a === waEl);

    if (itiTel) {
      const dialCode = '+' + itiTel.getSelectedCountryData().dialCode;
      const numero = telEl.value.replace(/\D/g, '');
      if (numero) telEl.value = dialCode + numero;
    }

    if (itiWa) {
      const dialCode = '+' + itiWa.getSelectedCountryData().dialCode;
      const numero = waEl.value.replace(/\D/g, '');
      if (numero) waEl.value = dialCode + numero;
    }

    form.submit();
  });

  function isBrasil() {
    return paisSelect.value === 'BR';
  }

  function sincronizarPais() {
    const codigo = paisSelect.value.toLowerCase();
    const instances = window.intlTelInput.instances;
    const telEl = document.getElementById('id_telefone');
    const waEl  = document.getElementById('id_whatsapp');
    const itiTel = Object.values(instances).find(i => i.a === telEl);
    const itiWa  = Object.values(instances).find(i => i.a === waEl);
    if (itiTel) itiTel.setCountry(codigo);
    if (itiWa)  itiWa.setCountry(codigo);
  }

  function atualizarCampos() {
    if (isBrasil()) {
      camposBR.style.removeProperty('display');
      camposIntl.style.setProperty('display', 'none', 'important');
      cep.setAttribute('data-mask', '00000-000');
      labelDoc.textContent = tipoPessoa.value === 'PF' ? 'CPF' : 'CNPJ';
    } else {
      camposBR.style.setProperty('display', 'none', 'important');
      camposIntl.style.removeProperty('display');
      cep.removeAttribute('data-mask');
      labelDoc.textContent = 'Documento';
    }
    if (typeof initMasks === 'function') initMasks();
    sincronizarPais();
  }

  paisSelect.addEventListener('change', atualizarCampos);
  tipoPessoa.addEventListener('change', () => {
    if (isBrasil()) {
      labelDoc.textContent = tipoPessoa.value === 'PF' ? 'CPF' : 'CNPJ';
    }
  });

  atualizarCampos();
});