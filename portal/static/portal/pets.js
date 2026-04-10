(function () {
  const modal = document.getElementById("petModal");
  const fab = document.getElementById("fabOpen");
  const cancel = document.getElementById("cancelModal");
  const form = document.getElementById("petForm");

  const usuarioUuidInput = document.getElementById("usuario_uuid");
  const nomeInput = document.getElementById("nome");
  const tipoInput = document.getElementById("tipo");
  const sexoInput = document.getElementById("sexo");
  const racaInput = document.getElementById("raca");
  const idadeInput = document.getElementById("idade");
  const pesoInput = document.getElementById("peso");
  const alturaInput = document.getElementById("altura");

  fab.onclick = () => modal.classList.add("show");
  cancel.onclick = () => modal.classList.remove("show");

  modal.onclick = (e) => {
    if (e.target === modal) modal.classList.remove("show");
  };

  form.onsubmit = async (e) => {
    e.preventDefault();

    const payload = {
      usuario_uuid: usuarioUuidInput.value,
      nome: nomeInput.value.trim(),
      tipo: tipoInput.value,
      sexo: sexoInput.value || null,
      raca: racaInput.value.trim() || null,
      idade: idadeInput.value ? parseInt(idadeInput.value, 10) : null,
      peso: pesoInput.value ? parseFloat(pesoInput.value) : null,
      altura: alturaInput.value ? parseFloat(alturaInput.value) : null,
    };

    const submitBtn = form.querySelector("button[type='submit']");
    submitBtn.disabled = true;

    try {
      const r = await fetch(window.PORTAL.proxyCreatePet, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (r.ok) {
        location.reload();
      } else {
        alert("Erro ao salvar pet");
        submitBtn.disabled = false;
      }
    } catch {
      alert("Erro de conexão");
      submitBtn.disabled = false;
    }
  };
})();