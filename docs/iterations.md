# Tukio Recommender: How the System Evolved

> Sources: `git log` of this repository, the code of each version, and the current benchmark in [`evaluation.md`](evaluation.md).
> All three versions are still in the codebase and can be selected in the live API with `GET /recommendations?strategy=baseline|ml|hybrid` (`backend/app/routers/recommendations.py`).

## Summary

| # | Version | File | First commit | Date | Live default? |
| :---: | :--- | :--- | :--- | :--- | :---: |
| 0 | No recommender (event CRUD, auth, RSVP) | – | `dd3ccec` | 16 Jul 2026 | – |
| 1 | Rule-based baseline | `backend/app/ml/baseline.py` | `559609a` | 17 Jul 2026 | No |
| 2 | TF-IDF content-based filtering | `backend/app/ml/engine.py` | `559609a` | 17 Jul 2026 | Yes, until 13 Oct |
| 3 | Unified multi-factor hybrid | `backend/app/ml/hybrid_engine.py` | `3e7afff` | 13 Oct 2026 | Yes, from 13 Oct |

Versions 1 and 2 arrived in the same commit. The baseline was built as the comparison point for the TF-IDF engine, as its own docstring says. It was never meant to be shipped on its own. The hybrid replaced TF-IDF as the API default; the older two stay available for comparison and the demo.

## Timeline from git

| Commit | Date | What changed in the recommender |
| :--- | :--- | :--- |
| `dd3ccec` | 16 Jul 2026 | Stages 1–4: auth, event CRUD, RSVP, frontend. No recommendations. |
| `559609a` | 17 Jul 2026 | **Versions 1 and 2.** `baseline.py` and `engine.py` added, plus `/recommendations?strategy=ml\|baseline` (default `ml`), user interests, `seed.py` with `seed_ground_truth.json`, and a first `evaluate.py` measuring Precision@5/10 only. |
| `b742907`, `ed3eca3` | 9 Aug, 5 Sep 2026 | UI and branding work. No recommender changes. |
| `3e7afff` | 13 Oct 2026 | **Version 3.** `hybrid_engine.py` added (355 lines). The API gains `strategy=hybrid` and makes it the default. `evaluate.py` now compares all three and adds MRR. |
| `41bbf76` | 17 Oct 2026 | Hybrid gains the feedback loop: "Interested" signals feed the SVD matrix and the content profile, and "Not for me" applies a small category penalty. Negative RSVP weights are removed from SVD. Feedback, interaction and time-aware models, routers and tests are added. |
| `bc4cac4` | 21 Oct 2026 | All three engines accept a fixed `reference_date` so evaluation is repeatable. The hybrid accepts `custom_weights` for validation-split tuning. `evaluate.py` becomes the multi-seed benchmark: 10 seeds, cold-start and warm cohorts, Recall, NDCG@10, and Random and Popularity floors. |
| `7edb785` | 23 Oct 2026 | Benchmark adds a behaviour-based ground truth (simulated students with hidden preferences), catalog coverage and a sensitivity check. See [`evaluation.md`](evaluation.md). |
| *current work* | 23 Oct 2026 | Hybrid: ended events get urgency 0 instead of maximum, and an optional MMR diversity re-rank is added. MMR was tested and left off because it lowered coverage. The benchmark reference date moves to the catalog's first day. See [`evaluation.md`](evaluation.md) §4.4–4.5. |

## Version 1: Rule-based baseline

**How it works.** Each event gets points for the user's declared interest tags: +3 if the event's category is one of them, +2 per shared tag, and +1 if it starts within 14 days. Events scoring 0 are never shown, and ties go to the sooner event.

**What it does well.** It is simple, instant and fully explainable ("category match: Tech; shared tags: ai").

**Limits visible in the code**
- **Exact string matches only.** "machine learning" and "ai" never match.
- **No learning.** RSVP history and other students' behaviour are ignored, so the ranking never improves with use.
- **Blank for some users.** It returns nothing for a user with no declared interests.

## Version 2: TF-IDF content-based filtering

**How it works.** Each event becomes a text document (title, description, category and tags, with the curated fields repeated for weight). Each user becomes a document too: declared interests plus the titles of events they RSVP'd to. Events are ranked by TF-IDF cosine similarity, and the "why" text lists the top shared terms. The docstring links this to Chapter 2 of the proposal: content-based filtering works from day one, with no cold-start problem from missing interaction data.

**What changed from version 1**
- **RSVP history counts.** Events a student RSVPs to now shape their profile.
- **Wider matching.** Scoring uses descriptions and titles, not only exact tags.
- **Gradual scores.** Scores are continuous instead of a few fixed point values.

**Limits visible in the code**
- **Only one student's signals.** What similar students attend is never used.
- **No campus context.** Department, timing and popularity are ignored.
- **Too-similar results.** Students tend to see more of what they already declared.

## Version 3: Unified multi-factor hybrid

**How it works.** Five scores are blended. The table shows the weights for a student with activity:

| Component | Weight | Source |
| :--- | :---: | :--- |
| Content (TF-IDF, unigrams + bigrams, adds department and RSVP'd categories to the profile) | 0.42 | `compute_content_scores` |
| Collaborative (TruncatedSVD on the user × event RSVP/"interested" matrix) | 0.28 | `compute_collaborative_scores` |
| Department match | 0.12 | `compute_context_scores` |
| Urgency (exponential decay, 12-day scale) | 0.10 | `compute_context_scores` |
| Popularity (confirmed RSVPs / capacity) | 0.08 | `compute_context_scores` |

**Cold-start handling.** The weights adapt to how much the system knows about a student:
- **Interests but no activity:** the collaborative weight is 0 and content rises to 0.62.
- **Nothing at all:** only department, urgency and popularity are used.

**Explainability.** Each card gets a badge ("For You", "Trending on Campus", "Happening Soon", "Faculty Pick") and reason chips.

**What changed from version 2**
- **Learns from similar students.** The collaborative term recommends what students with similar RSVP patterns attend.
- **Campus context.** Department, urgency and popularity are now part of the score.
- **Feedback loop** (added in `41bbf76`). The Interested and Not-for-me buttons change future rankings.

## How the versions compare today

Numbers below are NDCG@10 and Catalog Coverage@10 from the current benchmark (mean ± std over 10 seeds, all users). Full tables and method are in [`evaluation.md`](evaluation.md).

| Version | NDCG@10 (behaviour-based) | NDCG@10 (tag-overlap, biased toward v1) | Coverage@10 (behaviour-based) |
| :--- | :---: | :---: | :---: |
| 1. Rule-based | 0.119 ± 0.018 | **0.825 ± 0.029** | 0.826 ± 0.027 |
| 2. TF-IDF | 0.138 ± 0.021 | 0.736 ± 0.025 | **0.901 ± 0.035** |
| 3. Hybrid | **0.187 ± 0.026** | 0.722 ± 0.018 | 0.737 ± 0.034 |

**What each step bought**
- **v1 → v2:** a small accuracy gain on behaviour data (+0.019 NDCG@10, about one seed standard deviation) and the widest coverage of the three. On cold-start students, TF-IDF is slightly *behind* the rule-based version (0.127 vs 0.131).
- **v2 → v3:** a clear accuracy gain on behaviour data (+0.049 NDCG@10, +36%) in both cold-start and warm cohorts. The cost is lower coverage, because popularity and collaborative signals pull many students toward the same events. The sensitivity check in [`evaluation.md`](evaluation.md) §4.3 shows that this gain **disappears** (a tie on NDCG@10, a loss on MRR) when the simulator's department and popularity signals are removed.
- **On the tag-overlap set,** each step *loses* accuracy against v1. That set uses v1's own rule as its answer key, so it shows how much the later versions move away from exact tag matching. It is not evidence that they are worse for students.

## Gaps in the historical record

- **No benchmark numbers were saved when each version was built.** The July `evaluate.py` printed Precision@5/10 to the terminal, and nothing was committed to `results/` until the multi-seed benchmark. Every number above comes from today's benchmark, run on the current version of all three engines. Version 1 and 2 have only had small changes since July: a `reference_date` parameter and a null-weight guard in `bc4cac4`.
- **One earlier result was saved.** The committed tag-overlap results from `bc4cac4` matched the first run of the rewritten benchmark to within 0.002 (hybrid NDCG@10 0.730 both times), so the old and new benchmark code agreed on that set. The numbers above are lower for the hybrid (0.722) because of the later reference-date correction ([`evaluation.md`](evaluation.md) §4.5).
- **Some commit messages don't describe their changes.** `41bbf76` ("checkpoint before Tukio step 7") and `bc4cac4` ("wip: checkpoint before venues update") contain the feedback loop and the multi-seed benchmark respectively. The timeline above records what they actually changed.
- **The earlier versions can be inspected directly.** For example, `git show 559609a:backend/app/ml/engine.py` shows TF-IDF as it was in July, and `git show 3e7afff:backend/app/ml/hybrid_engine.py` shows the first hybrid.
