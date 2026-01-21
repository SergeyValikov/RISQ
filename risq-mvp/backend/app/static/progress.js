const stepEl = document.getElementById("step");
const errorEl = document.getElementById("error");

const steps = [
  "Извлечение текста…",
  "Анализ структуры…",
  "Формирование отчёта…",
];

let stepIndex = 0;

function rotateStep() {
  if (!stepEl) return;
  stepEl.textContent = steps[stepIndex % steps.length];
  stepIndex += 1;
}

async function pollJob() {
  if (!window.RISQ_JOB_ID) return;
  try {
    const response = await fetch(`/api/job/${window.RISQ_JOB_ID}`);
    if (!response.ok) return;
    const data = await response.json();
    if (data.step) {
      stepEl.textContent = data.step;
    }
    if (data.status === "done") {
      window.location.href = `/report/${window.RISQ_JOB_ID}`;
      return;
    }
    if (data.status === "error") {
      errorEl.textContent = data.error || "Произошла ошибка";
      errorEl.classList.remove("hidden");
    }
  } catch (error) {
    console.error(error);
  }
}

rotateStep();
setInterval(rotateStep, 2400);
setInterval(pollJob, 2000);
