/* SpoofVane — dashboard interactions */

document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector(".triage-form");
  if (!form) return;

  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const alertId = form.dataset.alertId;
    const feedback = form.querySelector(".triage-feedback");
    const data = new FormData(form);
    const body = {
      status: data.get("status"),
      notes: data.get("notes") || null,
      triaged_by: data.get("triaged_by"),
    };
    feedback.textContent = "Saving…";
    try {
      const r = await fetch(`/api/alerts/${alertId}/triage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const detail = await r.text();
        throw new Error(`${r.status}: ${detail}`);
      }
      feedback.textContent = "Saved. Reloading…";
      setTimeout(() => window.location.reload(), 500);
    } catch (err) {
      feedback.textContent = `Error: ${err.message}`;
    }
  });
});

window.runDiscoveryPrompt = async () => {
  const brands = window.__brands || [];
  if (brands.length === 0) {
    alert("No brands onboarded. Run scripts/seed_demo.py first.");
    return;
  }
  const choice = brands.length === 1
    ? brands[0]
    : brands.find(b => b.name === window.prompt(
        "Brand name to sweep:\n\n" + brands.map(b => "• " + b.name).join("\n")
      ));
  if (!choice) return;

  const r = await fetch("/api/discovery/run?wait=true", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ brand_id: choice.id, max_inspect: 15 }),
  });
  const out = await r.json();
  alert(
    `Pipeline complete.\n\n` +
    `Discovered: ${out.stats.suspects_discovered}\n` +
    `Inspected:  ${out.stats.suspects_inspected}\n` +
    `Flagged:    ${out.stats.suspects_above_threshold}\n` +
    `Alerts:     ${out.stats.alerts_created}`
  );
  window.location.reload();
};

// Analyst notes — append-only thread
(function () {
  const form = document.querySelector(".note-form");
  if (!form) return;
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const alertId = form.dataset.alertId;
    const author = form.querySelector("[name=author]").value.trim();
    const body = form.querySelector("[name=body]").value.trim();
    const feedback = form.querySelector(".note-feedback");
    if (!body) return;
    feedback.textContent = "Saving…";
    try {
      const r = await fetch(`/api/alerts/${alertId}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body, author: author || null }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const note = await r.json();
      const thread = document.getElementById("notes-thread");
      const empty = document.getElementById("notes-empty");
      if (empty) empty.remove();
      const div = document.createElement("div");
      div.className = "note";
      div.innerHTML =
        `<div class="note-meta"><span class="note-author"></span> · ` +
        `<span class="note-time"></span></div><div class="note-body"></div>`;
      div.querySelector(".note-author").textContent = note.author;
      div.querySelector(".note-time").textContent = note.created_at;
      div.querySelector(".note-body").textContent = note.body;
      thread.appendChild(div);
      form.querySelector("[name=body]").value = "";
      feedback.textContent = "Saved.";
      setTimeout(() => (feedback.textContent = ""), 2000);
    } catch (err) {
      feedback.textContent = "Error: " + err.message;
    }
  });
})();
