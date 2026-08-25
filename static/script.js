const urlInput = document.getElementById("url");
const platformBadge = document.getElementById("platform-badge");
const urlError = document.getElementById("url-error");
const modeButtons = document.querySelectorAll(".mode-btn");
const videoOptions = document.getElementById("video-options");
const audioOptions = document.getElementById("audio-options");
const form = document.getElementById("download-form");
const downloadBtn = document.getElementById("download-btn");
const progressWrap = document.getElementById("progress-wrap");
const progressFill = document.getElementById("progress-fill");
const progressLabel = document.getElementById("progress-label");
const resultBox = document.getElementById("result");

const PLATFORM_LABELS = {
  youtube: "YouTube",
  tiktok: "TikTok",
  instagram: "Instagram",
  x: "X (Twitter)",
};

let currentMode = "video";
let detectTimer = null;

modeButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    modeButtons.forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    currentMode = btn.dataset.mode;
    videoOptions.classList.toggle("hidden", currentMode !== "video");
    audioOptions.classList.toggle("hidden", currentMode !== "audio");
  });
});

urlInput.addEventListener("input", () => {
  clearTimeout(detectTimer);
  platformBadge.classList.add("hidden");
  urlError.classList.add("hidden");
  const url = urlInput.value.trim();
  if (!url) return;
  detectTimer = setTimeout(() => detectPlatform(url), 400);
});

async function detectPlatform(url) {
  try {
    const res = await fetch("/api/detect", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await res.json();
    if (data.ok) {
      platformBadge.textContent = PLATFORM_LABELS[data.platform] || data.platform;
      platformBadge.classList.remove("hidden");
      urlError.classList.add("hidden");
    } else {
      urlError.textContent = data.error;
      urlError.classList.remove("hidden");
      platformBadge.classList.add("hidden");
    }
  } catch (e) {
    // silencioso: la validación final ocurre en el submit
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  resultBox.classList.add("hidden");
  urlError.classList.add("hidden");

  const url = urlInput.value.trim();
  const quality =
    currentMode === "video"
      ? document.getElementById("resolution").value
      : document.getElementById("audio-format").value;

  downloadBtn.disabled = true;
  downloadBtn.textContent = "Iniciando...";
  progressWrap.classList.remove("hidden");
  progressFill.style.width = "0%";
  progressLabel.textContent = "Preparando...";

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, mode: currentMode, quality }),
    });
    const data = await res.json();

    if (!data.ok) {
      showError(data.error);
      return;
    }

    pollProgress(data.job_id);
  } catch (err) {
    showError("No se pudo conectar con el servidor.");
  }
});

function pollProgress(jobId) {
  const interval = setInterval(async () => {
    try {
      const res = await fetch(`/api/progress/${jobId}`);
      const data = await res.json();

      if (!data.ok) {
        clearInterval(interval);
        showError(data.error || "Error desconocido.");
        return;
      }

      if (data.status === "downloading") {
        const pct = data.percent ?? 0;
        progressFill.style.width = `${pct}%`;
        progressLabel.textContent = `Descargando... ${pct}%${data.speed ? " (" + data.speed + ")" : ""}`;
      } else if (data.status === "processing") {
        progressFill.style.width = "100%";
        progressLabel.textContent = "Procesando (conversión / combinando audio y video)...";
      } else if (data.status === "queued") {
        progressLabel.textContent = "En cola...";
      } else if (data.status === "done") {
        clearInterval(interval);
        progressFill.style.width = "100%";
        progressLabel.textContent = "¡Completado!";
        showSuccess(jobId, data.filename);
        resetButton();
      } else if (data.status === "error") {
        clearInterval(interval);
        showError(data.error);
      }
    } catch (err) {
      clearInterval(interval);
      showError("Se perdió la conexión con el servidor.");
    }
  }, 1000);
}

function showSuccess(jobId, filename) {
  resultBox.className = "result ok";
  resultBox.innerHTML = `Listo: <strong>${escapeHtml(filename)}</strong><br><a href="/api/file/${jobId}" download>Haz clic aquí si la descarga no comenzó automáticamente</a>`;
  resultBox.classList.remove("hidden");
  const link = document.createElement("a");
  link.href = `/api/file/${jobId}`;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
}

function showError(message) {
  resultBox.className = "result error";
  resultBox.textContent = message;
  resultBox.classList.remove("hidden");
  resetButton();
}

function resetButton() {
  downloadBtn.disabled = false;
  downloadBtn.textContent = "Descargar";
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
