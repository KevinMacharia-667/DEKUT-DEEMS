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

To run the multi-seed evaluation benchmark (about 8 minutes) comparing all 5 recommendation strategies on two ground-truth sets, across Overall, Cold-Start, and Warm user cohorts:

```powershell
$env:APP_ENV = "development"
python evaluate.py
```

Full method, results, and limitations: [`docs/evaluation.md`](../docs/evaluation.md).

### Benchmark Methodology Summary
- **Behaviour-based ground truth (primary)**: 60 simulated students per seed with hidden latent preferences (category taste, taste cluster, department, event appeal) plus noise. Their RSVPs come from that hidden utility, not from the tag-overlap rule. Models only see noisy declared interests and training-split RSVPs.
- **Tag-overlap ground truth (secondary, biased toward the baseline)**: `seed_ground_truth.json` from `seed.py`, built with the same category/tag overlap rule the Rule-Based baseline scores with. Kept for comparison.
- **Data Leakage Prevention**: Each user's interactions are partitioned into Train, Validation, and Test sets. Held-out test events never appear in the user's training profile, the SVD interaction matrix, or the popularity counts.
- **Metrics Reported**: Precision@5, Precision@10, Recall@5, Recall@10, NDCG@10, MRR, and Catalog Coverage@10, as mean ± std over 10 seeds.
- **Output Artifacts**: `results/evaluation.csv`, `results/evaluation.json`, `docs/evaluation_results.md` (tables), and `docs/evaluation_chart.png`.

## Real-Student Survey (Google Form)

The survey in `docs/tukio_survey_form_template.pdf` collects real DeKUT student preferences. Once responses are in:

1. In Google Forms: **Responses → Link to Sheets**, then in Sheets **File → Download → CSV**.
2. Save the file as `backend/data/survey/responses.csv` (this folder is git-ignored; keep raw responses out of the repo).
3. Run:

```powershell
$env:APP_ENV = "development"
python survey_import.py data/survey/responses.csv
```

It drops rows without consent, maps answers to the app's vocabulary, matches the 16 surveyed events to the seeded catalog, prints the assumption checks (popularity, department, timing), and ranks each respondent's held-out events with every model (P@3, NDCG@5, MRR over 10 random splits). Results are saved to `results/survey_evaluation.json`. Keep the event row titles in the form exactly as in the template, so they match the catalog. Report these results as *stated intention*, not observed attendance.
