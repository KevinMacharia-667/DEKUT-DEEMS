# DeKUT Event Management System - Backend

FastAPI backend application for the DeKUT Event Management Platform.

## Requirements
- Python 3.11+
- Pip (Python Package Installer)

## Setup & Running (Windows)

1. **Create Virtual Environment**:
   ```cmd
   python -m venv venv
   ```

2. **Activate Virtual Environment**:
   ```cmd
   venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```cmd
   pip install -r requirements.txt
   ```

4. **Environment Variables Setup**:
   Copy the example environment file:
   ```cmd
   copy .env.example .env
   ```

5. **Start Development Server**:
   ```cmd
   uvicorn main:app --reload
   ```

6. **Verify API is running**:
   Open a browser or run the following PowerShell command:
   ```powershell
   Invoke-RestMethod -Uri http://127.0.0.1:8000/health
   ```
   Expected response:
   ```json
   {"status": "ok"}
   ```

## Development Features
- **Auto-reloading**: Uvicorn is set to reload when code changes are detected.
- **Interactive Documentation**: Swagger UI documentation is available at `http://127.0.0.1:8000/docs` once the server is running.

## Recommendation Engine Offline Benchmark

To run the multi-seed evaluation benchmark comparing all 5 recommendation strategies across Overall, Cold-Start, and Warm user cohorts:

```powershell
python evaluate.py
```

### Benchmark Methodology & Limitation Note
- **Ground Truth Generation**: In `seed.py`, `seed_ground_truth.json` was generated synthetically by evaluating whether an event's category matches a user's declared interest tags or shares $\ge 2$ tags with the user's declared tags.
- **Methodological Limitation**: Because relevance in `seed_ground_truth.json` was defined through category and tag overlap, the heuristic **Rule-Based Baseline** has an inherent structural advantage on this synthetic dataset. For production deployment, ground truth must be collected from real user implicit feedback telemetry (such as click-through rate, card dwell time, and RSVP completion).
- **Data Leakage Prevention**: In `evaluate.py`, each user's interactions are partitioned into Train, Validation, and Test sets. Held-out test events are strictly quarantined: they are never present in the user's training profile, never included in the collaborative filtering SVD interaction matrix, and never included in the popularity frequency counts.
- **Metrics Reported**: Precision@5, Precision@10, Recall@5, Recall@10, NDCG@10, and Mean Reciprocal Rank (MRR averaged across users), reported as $\text{Mean} \pm \text{Std}$ over 10 evaluation seeds.
- **Output Artifacts**: Detailed results are exported to `results/evaluation.csv` and `results/evaluation.json`.

