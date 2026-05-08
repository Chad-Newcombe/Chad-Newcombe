"""Flask web dashboard for the personal finance analyzer."""

from __future__ import annotations
import json
import shutil
import tempfile
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, url_for

PROJECT_ROOT = Path(__file__).parent.parent

# In-memory job registry: run_id → {status, output_dir, error, steps}
JOBS: dict[str, dict] = {}


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB

    # ── Routes ────────────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/analyze", methods=["POST"])
    def analyze():
        run_id = uuid.uuid4().hex[:10]

        uploaded = request.files.getlist("statements")
        if not uploaded or all(f.filename == "" for f in uploaded):
            return redirect(url_for("index"))

        # Save uploaded CSVs to a temp directory
        temp_dir = Path(tempfile.mkdtemp(prefix="finance_"))
        saved_paths: list[str] = []
        for f in uploaded:
            if f.filename:
                dest = temp_dir / Path(f.filename).name
                f.save(str(dest))
                saved_paths.append(str(dest))

        # Parse credit card config rows
        cc_names = request.form.getlist("cc_name")
        cc_aprs = request.form.getlist("cc_apr")
        cc_mins = request.form.getlist("cc_min")
        cc_balances = request.form.getlist("cc_balance")
        cc_limits = request.form.getlist("cc_limit")

        cc_configs: list[dict] = []
        for i in range(len(cc_names)):
            name = cc_names[i].strip()
            if not name:
                continue
            cfg: dict = {
                "name": name,
                "apr": float(cc_aprs[i] or 0),
                "min_payment": float(cc_mins[i] or 0),
            }
            if i < len(cc_balances) and cc_balances[i].strip():
                cfg["balance"] = float(cc_balances[i])
            if i < len(cc_limits) and cc_limits[i].strip():
                cfg["credit_limit"] = float(cc_limits[i])
            cc_configs.append(cfg)

        income_str = request.form.get("income", "").strip()
        budget_str = request.form.get("budget", "").strip()
        api_key = request.form.get("api_key", "").strip() or None

        projected_income = float(income_str) if income_str else None
        monthly_budget = float(budget_str) if budget_str else None

        JOBS[run_id] = {
            "status": "running",
            "steps": ["Uploading files…", "Starting analysis pipeline…"],
            "output_dir": None,
            "error": None,
        }

        thread = threading.Thread(
            target=_run_analysis,
            args=(run_id, saved_paths, cc_configs, projected_income, monthly_budget, api_key, temp_dir),
            daemon=True,
        )
        thread.start()

        return redirect(url_for("loading", run_id=run_id))

    @app.route("/loading/<run_id>")
    def loading(run_id):
        if run_id not in JOBS:
            return redirect(url_for("index"))
        return render_template("loading.html", run_id=run_id)

    @app.route("/api/status/<run_id>")
    def api_status(run_id):
        job = JOBS.get(run_id)
        if not job:
            return jsonify({"status": "not_found"}), 404
        return jsonify(job)

    @app.route("/dashboard/<run_id>")
    def dashboard(run_id):
        job = JOBS.get(run_id)
        if not job:
            return redirect(url_for("index"))
        if job["status"] == "error":
            return render_template("error.html", error=job["error"], run_id=run_id)
        if job["status"] != "done":
            return redirect(url_for("loading", run_id=run_id))

        report = json.loads((Path(job["output_dir"]) / "report.json").read_text())
        return render_template("dashboard.html", report=report, run_id=run_id,
                               output_dir=job["output_dir"])

    @app.route("/transactions/<run_id>")
    def transactions(run_id):
        job = JOBS.get(run_id)
        if not job or job["status"] != "done":
            return redirect(url_for("index"))
        txns = json.loads((Path(job["output_dir"]) / "transactions.json").read_text())
        return render_template("transactions.html", transactions=txns, run_id=run_id)

    return app


# ── Background worker ─────────────────────────────────────────────────────────

def _run_analysis(
    run_id: str,
    statement_files: list[str],
    cc_configs: list[dict],
    projected_income: float | None,
    monthly_budget: float | None,
    api_key: str | None,
    temp_dir: Path,
) -> None:
    """Run the finance orchestrator in a background thread."""
    try:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))
        from src.finance_orchestrator import FinanceOrchestrator

        _step(run_id, "Parsing CSV statements…")
        orchestrator = FinanceOrchestrator(api_key=api_key)

        _step(run_id, "Categorizing transactions with AI…")
        report = orchestrator.analyze(
            statement_files=statement_files,
            credit_card_configs=cc_configs,
            monthly_payment_budget=monthly_budget,
            projected_income=projected_income,
        )

        JOBS[run_id]["status"] = "done"
        JOBS[run_id]["output_dir"] = report.output_dir
        _step(run_id, "Analysis complete!")

    except Exception as exc:
        JOBS[run_id]["status"] = "error"
        JOBS[run_id]["error"] = str(exc)
    finally:
        shutil.rmtree(str(temp_dir), ignore_errors=True)


def _step(run_id: str, message: str) -> None:
    if run_id in JOBS:
        JOBS[run_id]["steps"].append(message)
