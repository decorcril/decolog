document.addEventListener('DOMContentLoaded', function () {
  const paisSelect = document.getElementById('id_pais');
  if (!paisSelect) return;

  const camposBR   = document.getElementById('campos_br');
  const camposIntl = document.getElementById('campos_intl');
  const cepInput   = document.getElementById('id_cep');
  const tipoPessoa = document.getElementById('id_tipo_pessoa');
  const labelDoc   = document.getElementById('label_documento');

  // ── intl-tel-input ──
  const itiConfig = {
    initialCountry: paisSelect.value.toLowerCase() || 'br',
    separateDialCode: true,
    preferredCountries: ['br', 'ar', 'cl', 'py', 'uy', 'us'],
    utilsScript: 'https://cdn.jsdelivr.net/npm/intl-tel-input@23/build/js/utils.js',
  };
  window.intlTelInput(document.getElementById('id_telefone'), itiConfig);
  window.intlTelInput(document.getElementById('id_whatsapp'), itiConfig);

  // ── Submit — formata telefones antes de enviar ──
  document.getElementById('form-cliente').addEventListener('submit', function (e) {
    e.preventDefault();
    const telEl = document.getElementById('id_telefone');
    const waEl  = document.getElementById('id_whatsapp');
    const instances = window.intlTelInput.instances;
    const itiTel = Object.values(instances).find(i => i.a === telEl);
    const itiWa  = Object.values(instances).find(i => i.a === waEl);
    if (itiTel) {
      const numero = telEl.value.replace(/\D/g, '');
      if (numero) telEl.value = '+' + itiTel.getSelectedCountryData().dialCode + numero;
    }
    if (itiWa) {
      const numero = waEl.value.replace(/\D/g, '');
      if (numero) waEl.value = '+' + itiWa.getSelectedCountryData().dialCode + numero;
    }
    this.submit();
  });

  // ── Helpers ──
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
      cepInput.setAttribute('data-mask', '00000-000');
      labelDoc.textContent = tipoPessoa.value === 'PF' ? 'CPF' : 'CNPJ';
    } else {
      camposBR.style.setProperty('display', 'none', 'important');
      camposIntl.style.removeProperty('display');
      cepInput.removeAttribute('data-mask');
      labelDoc.textContent = 'Documento';
    }
    if (typeof initMasks === 'function') initMasks();
    sincronizarPais();
  }

  // ── Autocomplete CEP via ViaCEP ──
  function buscarCep(cep) {
    const cepLimpo = cep.replace(/\D/g, '');
    if (cepLimpo.length !== 8) return;

    fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`)
      .then(r => r.json())
      .then(data => {
        if (data.erro) return;
        const set = (id, val) => {
          const el = document.getElementById(id);
          if (el && val) el.value = val;
        };
        set('id_logradouro', data.logradouro);
        set('id_bairro',     data.bairro);
        set('id_cidade',     data.localidade);
        set('id_estado',     data.uf);
        document.getElementById('id_numero')?.focus();
      })
      .catch(() => {});
  }

  // Busca ao sair do campo
  cepInput.addEventListener('blur', function () {
    if (isBrasil()) buscarCep(this.value);
  });

  // Busca ao pressionar Enter no campo CEP — sem submeter o form
  cepInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') {
      e.preventDefault();
      buscarCep(this.value);
    }
  });

  // ── Busca de documento (CPF e CNPJ) ──
  const docInput = document.getElementById('id_documento');
  if (docInput) {
    docInput.addEventListener('blur', function () {
      if (!isBrasil()) return;
      const doc = this.value.replace(/\D/g, '');

      // CPF — 11 dígitos
      if (tipoPessoa.value === 'PF' && doc.length === 11) {
        fetch(`https://brasilapi.com.br/api/cpf/v1/${doc}`)
          .then(r => r.ok ? r.json() : null)
          .then(data => {
            if (data?.nome) {
              const nomeEl = document.getElementById('id_nome');
              if (nomeEl && !nomeEl.value) nomeEl.value = data.nome;
            }
          })
          .catch(() => {});
      }

      // CNPJ — 14 dígitos
      if (tipoPessoa.value === 'PJ' && doc.length === 14) {
        fetch(`https://brasilapi.com.br/api/cnpj/v1/${doc}`)
          .then(r => r.ok ? r.json() : null)
          .then(data => {
            if (!data) return;
            const set = (id, val) => {
              const el = document.getElementById(id);
              if (el && val && !el.value) el.value = val;
            };
            set('id_nome',         data.razao_social);
            set('id_nome_fantasia', data.nome_fantasia);
            set('id_email',        data.email);
            set('id_cep',          data.cep?.replace(/\D/g, ''));
            if (data.cep) buscarCep(data.cep);
          })
          .catch(() => {});
      }
    });
  }

  // ── Listeners ──
  paisSelect.addEventListener('change', atualizarCampos);
  tipoPessoa.addEventListener('change', () => {
    if (isBrasil()) {
      labelDoc.textContent = tipoPessoa.value === 'PF' ? 'CPF' : 'CNPJ';
    }
  });

  atualizarCampos();
});