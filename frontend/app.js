"use strict";

const form = document.querySelector("#shorten-form");
const input = document.querySelector("#original-url");
const submit = document.querySelector("#submit-button");
const message = document.querySelector("#message");
const result = document.querySelector("#result");
const link = document.querySelector("#short-url");
const copyStatus = document.querySelector("#copy-status");

function showError(text) {
  message.textContent = text;
  message.hidden = false;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  message.hidden = true;
  result.hidden = true;
  copyStatus.textContent = "";
  let original;
  let api;
  try {
    original = new URL(input.value.trim());
    api = new URL(window.APP_CONFIG.API_BASE_URL);
    if (!["http:", "https:"].includes(original.protocol) || original.username || original.password) {
      throw new Error("invalid-url");
    }
    if (!["http:", "https:"].includes(api.protocol)) throw new Error("invalid-config");
  } catch {
    showError("Revisa la URL y la configuración de la API. Usa una dirección HTTP o HTTPS sin credenciales.");
    return;
  }
  if (location.protocol === "https:" && api.protocol === "http:") {
    showError("La página usa HTTPS y la API HTTP. Configura HTTPS en la API para permitir la conexión.");
    return;
  }

  submit.disabled = true;
  submit.textContent = "Creando enlace…";
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const response = await fetch(`${api.href.replace(/\/$/, "")}/shorten`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ original_url: original.href }),
      signal: controller.signal,
    });
    if (!response.ok) {
      const errors = {
        422: "La dirección ingresada no es válida. Revisa el enlace e inténtalo de nuevo.",
        503: "El almacenamiento no está disponible temporalmente. Inténtalo más tarde.",
      };
      throw new Error(errors[response.status] || "No fue posible crear el enlace. Inténtalo más tarde.");
    }
    const data = await response.json();
    const shortUrl = new URL(data.short_url);
    if (!["http:", "https:"].includes(shortUrl.protocol)) throw new Error("Respuesta inválida de la API.");
    link.href = shortUrl.href;
    link.textContent = shortUrl.href;
    result.hidden = false;
  } catch (error) {
    showError(error.name === "AbortError"
      ? "El servidor tardó demasiado en responder. Inténtalo otra vez."
      : error instanceof TypeError
        ? "No se pudo conectar con la API. Revisa tu conexión o la configuración del servidor y CORS."
        : error.message);
  } finally {
    clearTimeout(timeout);
    submit.disabled = false;
    submit.textContent = "Crear enlace ↗";
  }
});

document.querySelector("#copy-button").addEventListener("click", async () => {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(link.href);
    } else {
      // El sitio web estático de S3 usa HTTP: la API moderna del portapapeles no está disponible.
      const field = document.createElement("textarea");
      field.value = link.href;
      field.setAttribute("readonly", "");
      field.style.position = "fixed";
      field.style.opacity = "0";
      document.body.append(field);
      field.select();
      let copied;
      try { copied = document.execCommand("copy"); } finally { field.remove(); }
      if (!copied) throw new Error("copy-failed");
    }
    copyStatus.textContent = "Enlace copiado. Ya puedes compartirlo.";
  } catch {
    copyStatus.textContent = "Selecciona el enlace y usa Ctrl+C (o mantén pulsado para copiar).";
    const selection = window.getSelection();
    const range = document.createRange();
    range.selectNodeContents(link);
    selection.removeAllRanges();
    selection.addRange(range);
    link.focus();
  }
});
