/**
 * search.js — handles the search form on the home page,
 * fires a POST /search, then opens SSE /stream/<job_id>
 * to show live progress inline before redirecting.
 */

document.addEventListener("DOMContentLoaded", () => {
  const form        = document.getElementById("searchForm");
  const submitBtn   = document.getElementById("submitBtn");
  const progressPanel = document.getElementById("progressPanel");
  const progressBar   = document.getElementById("progressBar");
  const progressMsg   = document.getElementById("progressMessage");
  const stepLabel     = document.getElementById("progressStepLabel");
  const papersFeed    = document.getElementById("papersFeed");
  const papersTable   = document.getElementById("papersTable");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const query = document.getElementById("queryInput").value.trim();
    if (!query) return;

    const sources = [...document.querySelectorAll("input[name='sources']:checked")]
      .map(el => el.value);
    if (!sources.length) {
      alert("Please select at least one literature source.");
      return;
    }

    const hypotheses = parseInt(document.getElementById("hypothesesCount").value, 10);

    // Disable form
    submitBtn.disabled = true;
    submitBtn.textContent = "⏳ Starting…";
    progressPanel.style.display = "block";
    progressPanel.scrollIntoView({ behavior: "smooth", block: "start" });

    // POST /search
    let jobId;
    try {
      const resp = await fetch("/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, sources, hypotheses }),
      });
      const data = await resp.json();
      if (data.error) throw new Error(data.error);
      jobId = data.job_id;
    } catch (err) {
      progressMsg.textContent = "❌ " + err.message;
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<span class="btn-icon">🔬</span> Start Research';
      return;
    }

    // Open SSE stream
    const es = new EventSource("/stream/" + jobId);

    function setBar(step, total) {
      const pct = Math.round((step / total) * 100);
      progressBar.style.width = pct + "%";
      stepLabel.textContent = `Step ${step} of ${total}`;
    }

    es.addEventListener("progress", ev => {
      const d = JSON.parse(ev.data);
      progressMsg.textContent = d.message;
      setBar(d.step, d.total);
    });

    es.addEventListener("papers_found", ev => {
      const d = JSON.parse(ev.data);
      papersFeed.style.display = "block";
      papersTable.innerHTML = d.papers.map((p, i) => `
        <div class="mini-paper-row">
          <span class="mini-num">${i + 1}</span>
          <span class="mini-title">${escHtml(p.title)}</span>
          <span class="mini-year">${p.year || "–"}</span>
          <span class="mini-source badge-source badge-${escHtml(p.source)}">${escHtml(p.source)}</span>
        </div>`).join("");
    });

    es.addEventListener("done", () => {
      es.close();
      progressBar.style.width = "100%";
      progressMsg.textContent = "✅ Complete! Loading results…";
      setTimeout(() => { window.location.href = "/results/" + jobId; }, 600);
    });

    es.addEventListener("error", ev => {
      es.close();
      let msg = "An error occurred.";
      try { msg = JSON.parse(ev.data).message; } catch (_) {}
      progressMsg.textContent = "❌ " + msg;
      progressBar.style.background = "var(--danger)";
      submitBtn.disabled = false;
      submitBtn.innerHTML = '<span class="btn-icon">🔬</span> Start Research';
    });
  });

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
});
