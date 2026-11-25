"""Local Experiment Tracking for LOVE Native AI.

Implements Section 10 (NAI-04):
- Local SQLite database (native_ai/experiments/experiments.db) and JSON export.
- Strictly isolated from main LOVE application database.
- Tracks hyperparameters, system telemetry, loss, perplexity, VRAM, and checkpoint references.
"""
import os
import json
import sqlite3
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

class ExperimentTracker:
    """Manages experiment runs, step telemetry logging, and local metric persistence."""

    def __init__(self, exp_dir: Optional[Path] = None):
        base_dir = Path(__file__).resolve().parent.parent
        self.exp_dir = exp_dir or (base_dir / "experiments")
        self.exp_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.exp_dir / "experiments.db"
        self._init_db()

    def _init_db(self) -> None:
        """Initializes tables for experiments and step telemetry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    experiment_id TEXT PRIMARY KEY,
                    run_name TEXT,
                    created_at_iso TEXT,
                    device TEXT,
                    precision TEXT,
                    batch_size INTEGER,
                    context_length INTEGER,
                    learning_rate REAL,
                    model_params INTEGER,
                    config_json TEXT,
                    status TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS step_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment_id TEXT,
                    step INTEGER,
                    epoch INTEGER,
                    train_loss REAL,
                    val_loss REAL,
                    perplexity REAL,
                    lr REAL,
                    vram_allocated_mb REAL,
                    vram_peak_mb REAL,
                    step_time_ms REAL,
                    timestamp_unix REAL,
                    FOREIGN KEY(experiment_id) REFERENCES runs(experiment_id)
                )
            """)
            conn.commit()

    def start_run(
        self,
        experiment_id: str,
        run_name: str,
        hyperparameters: Dict[str, Any],
        model_params: int = 0,
        device: str = "cpu",
        precision: str = "float32",
    ) -> None:
        """Registers a new experiment run."""
        created_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        config_json = json.dumps(hyperparameters)
        batch_size = hyperparameters.get("batch_size", 1)
        context_len = hyperparameters.get("context_length", 512)
        lr = hyperparameters.get("learning_rate", 1e-4)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO runs (
                    experiment_id, run_name, created_at_iso, device, precision,
                    batch_size, context_length, learning_rate, model_params, config_json, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                experiment_id, run_name, created_iso, device, precision,
                batch_size, context_len, lr, model_params, config_json, "RUNNING"
            ))
            conn.commit()

    def log_step(
        self,
        experiment_id: str,
        step: int,
        epoch: int,
        train_loss: Optional[float] = None,
        val_loss: Optional[float] = None,
        perplexity: Optional[float] = None,
        lr: Optional[float] = None,
        vram_allocated_mb: float = 0.0,
        vram_peak_mb: float = 0.0,
        step_time_ms: float = 0.0,
    ) -> None:
        """Logs step-level telemetry and evaluation metrics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO step_metrics (
                    experiment_id, step, epoch, train_loss, val_loss, perplexity,
                    lr, vram_allocated_mb, vram_peak_mb, step_time_ms, timestamp_unix
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                experiment_id, step, epoch, train_loss, val_loss, perplexity,
                lr, vram_allocated_mb, vram_peak_mb, step_time_ms, time.time()
            ))
            conn.commit()

    def end_run(self, experiment_id: str, final_status: str = "COMPLETED") -> Dict[str, Any]:
        """Marks run completed and exports full experiment report as JSON."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("UPDATE runs SET status = ? WHERE experiment_id = ?", (final_status, experiment_id))
            conn.commit()

            cursor.execute("SELECT * FROM runs WHERE experiment_id = ?", (experiment_id,))
            run_row = dict(cursor.fetchone() or {})

            cursor.execute("SELECT * FROM step_metrics WHERE experiment_id = ? ORDER BY step ASC", (experiment_id,))
            step_rows = [dict(r) for r in cursor.fetchall()]

        report = {
            "run": run_row,
            "metrics_history": step_rows,
            "total_steps_logged": len(step_rows),
        }

        # Export JSON summary
        json_path = self.exp_dir / f"{experiment_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)

        return report
