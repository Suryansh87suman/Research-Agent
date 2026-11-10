"""
app.py — Flask web application for the IBM Research Agent.

Routes
------
GET  /                  → Home page (search form)
POST /search            → Trigger pipeline, returns job_id (JSON)
GET  /stream/<job_id>   → Server-Sent Events: live pipeline progress
GET  /results/<job_id>  → Results page (papers, summaries, hypotheses)
GET  /report/<job_id>   → Full rendered Markdown report
GET  /download/<job_id>/<fmt>  → Download BibTeX / APA / JSON / Markdown
GET  /history           → Past jobs stored in session
"""

import json
import os
import queue
import threading
import time
import uuid
from pathlib import Path

from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    send_file,
    session,
)

app = Flask(__name__, template_folder="templates", static_folder="static")
# Use a stable SECRET_KEY env var in production (Code Engine secret) so
# sessions survive container restarts. Falls back to a random key in dev.
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(32)

# ── In-memory job store ───────────────────────────────────────────────────────
# job_id → {"status", "progress", "result", "error", "queue"}
_jobs: dict = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _emit(q: queue.Queue, event: str, data: dict) -> None:
    """Push an SSE-formatted message onto the queue."""
    q.put(f"event: {event}\ndata: {json.dumps(data)}\n\n")


def _run_pipeline(job_id: str, query: str, sources: list, num_hypotheses: int) -> None:
    """Background thread: runs the research pipeline and streams progress."""
    q = _jobs[job_id]["queue"]
    try:
        from research_agent.agent import ResearchAgent
        from research_agent import config

        _emit(q, "progress", {"step": 1, "total": 5, "message": "Initialising IBM Granite model…"})

        agent = ResearchAgent(verbose=False)

        # Step 1 — Search
        _emit(q, "progress", {"step": 1, "total": 5, "message": f"Searching literature across {', '.join(sources)}…"})
        papers = agent.search(query, sources=sources)
        if not papers:
            _emit(q, "error", {"message": "No papers found for this query. Try a broader search."})
            _jobs[job_id]["status"] = "error"
            return

        paper_data = [
            {
                "title": p.title,
                "authors": p.authors[:4],
                "year": p.year,
                "abstract": p.abstract or "",
                "source": p.source,
                "url": p.url,
                "doi": p.doi,
                "venue": p.venue,
                "citation_count": p.citation_count,
            }
            for p in papers
        ]
        _emit(q, "papers_found", {"count": len(papers), "papers": paper_data})

        # Step 2 — Summarise (sequential with inter-request delay to avoid 429)
        _emit(q, "progress", {"step": 2, "total": 5, "message": f"Summarising {len(papers)} papers with IBM Llama-3…"})
        summaries = {}
        for i, paper in enumerate(papers):
            _emit(q, "progress", {
                "step": 2, "total": 5,
                "message": f"Summarising paper {i+1}/{len(papers)}: {paper.title[:55]}…"
            })
            summaries[paper.title] = agent.summarize_paper(paper)
            # Pause between requests — IBM Cloud Lite allows ~10 concurrent;
            # a 3 s gap keeps us well clear of the burst limit.
            if i < len(papers) - 1:
                time.sleep(3)
        _emit(q, "summaries_done", {"summaries": summaries})

        # Step 3 — Hypotheses
        _emit(q, "progress", {"step": 3, "total": 5, "message": f"Generating {num_hypotheses} research hypotheses…"})
        hypotheses = agent.generate_hypotheses(query, papers, count=num_hypotheses)
        _emit(q, "hypotheses_done", {"hypotheses": hypotheses})

        # Step 4 — Report
        _emit(q, "progress", {"step": 4, "total": 5, "message": "Writing full research report…"})
        agent.add_citations(papers)
        report_filename = f"report_{job_id}.md"
        report_path = agent.write_report(query, papers, filename=report_filename)

        # Step 5 — Export citations
        _emit(q, "progress", {"step": 5, "total": 5, "message": "Exporting citations (BibTeX, APA, JSON)…"})
        bib_path = agent.export_citations("bibtex")
        apa_path = agent.export_citations("apa")
        json_path = agent.export_citations("json")

        # Rename outputs to include job_id for isolation
        def _rename(src: Path, suffix: str) -> Path:
            dest = src.parent / f"{suffix}_{job_id}{src.suffix}"
            src.rename(dest)
            return dest

        bib_path = _rename(bib_path, "references")
        apa_path = _rename(apa_path, "references_apa")
        json_path = _rename(json_path, "references")

        result = {
            "query": query,
            "papers": paper_data,
            "summaries": summaries,
            "hypotheses": hypotheses,
            "report_path": str(report_path),
            "bib_path": str(bib_path),
            "apa_path": str(apa_path),
            "json_path": str(json_path),
        }
        _jobs[job_id]["result"] = result
        _jobs[job_id]["status"] = "done"
        _emit(q, "done", {"job_id": job_id})

    except Exception as exc:  # noqa: BLE001
        _jobs[job_id]["status"] = "error"
        _emit(q, "error", {"message": str(exc)})
    finally:
        q.put(None)  # sentinel — close the SSE stream


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    data = request.get_json(force=True)
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"error": "Query is required."}), 400

    sources = data.get("sources") or ["arxiv", "semantic_scholar", "crossref"]
    num_hypotheses = int(data.get("hypotheses", 3))

    job_id = uuid.uuid4().hex
    _jobs[job_id] = {
        "status": "running",
        "query": query,
        "result": None,
        "error": None,
        "queue": queue.Queue(),
    }

    # Store job history in session
    history = session.get("history", [])
    history.insert(0, {"job_id": job_id, "query": query})
    session["history"] = history[:10]

    thread = threading.Thread(
        target=_run_pipeline,
        args=(job_id, query, sources, num_hypotheses),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/stream/<job_id>")
def stream(job_id: str):
    if job_id not in _jobs:
        return Response("data: {\"error\": \"Job not found\"}\n\n", mimetype="text/event-stream")

    q = _jobs[job_id]["queue"]

    def generate():
        while True:
            msg = q.get()
            if msg is None:
                break
            yield msg

    return Response(generate(), mimetype="text/event-stream",
                    headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"})


@app.route("/results/<job_id>")
def results(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        return render_template("error.html", message="Job not found."), 404
    if job["status"] == "running":
        return render_template("loading.html", job_id=job_id, query=job.get("query", ""))
    if job["status"] == "error":
        return render_template("error.html", message="Pipeline encountered an error."), 500
    return render_template("results.html", job_id=job_id, result=job["result"])


@app.route("/report/<job_id>")
def report(job_id: str):
    job = _jobs.get(job_id)
    if not job or not job.get("result"):
        return render_template("error.html", message="Report not found."), 404
    report_path = Path(job["result"]["report_path"])
    if not report_path.exists():
        return render_template("error.html", message="Report file missing."), 404
    report_md = report_path.read_text(encoding="utf-8")
    return render_template("report.html", report_md=report_md,
                           query=job["result"]["query"], job_id=job_id)


@app.route("/download/<job_id>/<fmt>")
def download(job_id: str, fmt: str):
    job = _jobs.get(job_id)
    if not job or not job.get("result"):
        return "Not found", 404
    result = job["result"]
    paths = {
        "bibtex": result.get("bib_path"),
        "apa":    result.get("apa_path"),
        "json":   result.get("json_path"),
        "report": result.get("report_path"),
    }
    path_str = paths.get(fmt)
    if not path_str or not Path(path_str).exists():
        return "File not found", 404
    return send_file(path_str, as_attachment=True)


@app.route("/history")
def history():
    hist = session.get("history", [])
    return render_template("history.html", history=hist, jobs=_jobs)


@app.route("/api/job/<job_id>")
def job_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"status": job["status"], "result": job.get("result")})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000, threaded=True)
