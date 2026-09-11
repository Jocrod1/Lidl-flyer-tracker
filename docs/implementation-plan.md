# Repository Restructuring Plan — lidl-flyer-tracker

## Current state (confirmed by inspection)

```
lidl-flyer-tracker/
├── .github/workflows/{ingest,watch,watch-test}.yml
├── compose.yaml
├── pyproject.toml                  # dist name "lidl-flyer-tracker", package "lidl_tracker", where=["src"]
├── README.md
├── .env.example, .env.local
├── data/{cache,config,out,raw,recon,state}/
├── .local/{cache,raw}/
├── docs/{acquisition,pdf-structure,scheduling}.md
├── migrations/*.sql                # NOT executed by code — documentary only
├── src/lidl_tracker/…              # the actual package
├── tests/*.py                      # imports `lidl_tracker...` + one file imports `tools.image_ranking`
└── tools/{*.py, image_ranking/, run_watch.bat}
```

No Dockerfile, Makefile, conftest.py, or alembic — schema is applied by inline SQL in `storage/database.py`, not by reading `migrations/*.sql`.

---

## Key findings that drive the plan

1. **`migrations/*.sql` are pure documentation.** `apply_migrations()` embeds the schema as a Python string; nothing reads the files. This means moving `migrations/` is *safe for runtime behavior* — it only affects `psql -f migrations/...` comments and human workflow.
2. **`tools/` is currently a de-facto test dependency of the main suite.** `tests/test_image_ranking.py` does `from tools.image_ranking.ranker import ...`, which only works because `python -m pytest` is invoked from the repo root (cwd on `sys.path`), and is not declared anywhere in `pyproject.toml`. This is fragile and will break the moment `tests/` and `tools/` are no longer siblings of a common root that's `pytest`'s cwd.
3. **`tools/image_ranking` has an internal import inconsistency** (`evaluate.py` uses bare `from ranker import ...`, requiring `PYTHONPATH=tools/image_ranking`, while tests use the fully-qualified path). This predates the restructuring but should be cleaned up while touching this code.
4. **~40+ `patch("lidl_tracker...")` string literals** in tests — a package rename would require careful find/replace across all of them. There's no functional reason to rename `lidl_tracker` for this restructuring.
5. **`docs/scheduling.md` hardcodes an absolute Windows path** to `tools/run_watch.bat` for a live Scheduled Task on this machine — this is outside git and needs manual re-registration if the file moves, independent of anything else.
6. **`watch.yml` hardcodes `data/state/watch_state.json`** in a `git add` step, tightly coupled with a `.gitignore` negation pattern for the same path.
7. `compose.yaml` only orchestrates third-party images (no COPY/build context) — zero coupling to any path restructuring.

---

## Recommendations for your explicit questions

**Should the Python package remain named `lidl_tracker`?**
Yes — keep it. Renaming has real cost (40+ patch-string literals, imports, egg-info, CLI module paths in workflows: `python -m lidl_tracker.cli_ingest`) and zero benefit tied to this restructuring. The pre-existing `lidl-flyer-tracker` (dist name) vs `lidl_tracker` (import name) mismatch is unrelated and not worth fixing now.

**Where should shared configuration live?**
- `pyproject.toml` moves to **`ingestion/pyproject.toml`** (not root). It's Python-specific and only governs the ingestion app; a future `apps/web` will have its own `package.json`, and a future `apps/api` its own manifest. Root should stay language-agnostic.
- Root keeps: `.github/`, `compose.yaml` (shared dev infra: Postgres/MinIO/Mailpit, used by both ingestion and future api), `.gitignore`, top-level `README.md` (becomes a short index linking into `ingestion/README` and `apps/web/README`).
- `.env.example` stays at root for now (only one app consumes env vars today); split per-app later if `apps/web` needs its own env file.

**Should `migrations/` remain at repo root?**
Yes — keep at root. It's shared infrastructure conceptually owned by "the database," not by any one app. A future `apps/api` would apply the same migrations. This matches your target tree.

**Should `tools/image_ranking` remain at root under `tools/`?**
Keep `tools/` at root per your target tree, but **decouple `test_image_ranking.py` from the ingestion test suite**: move it to `tools/image_ranking/tests/test_image_ranking.py` and give it its own pytest invocation (or its own tiny `pyproject.toml`/`pytest.ini` under `tools/`). Rationale: `tools/` is explicitly "offline research/development," and it should not be an implicit, undeclared dependency of `ingestion/tests` that only works by accident of cwd. Also fix `evaluate.py`'s inconsistent bare import (`from ranker import ...` → `from tools.image_ranking.ranker import ...`) while touching this.

---

## Proposed final tree

```
lidl-flyer-tracker/
├── .github/
│   └── workflows/
│       ├── ingest.yml           # updated: pip install -e ./ingestion, cwd stays root for data/ steps
│       ├── watch.yml            # updated: same, git add data/state/... unchanged (data/ stays root)
│       └── watch-test.yml       # updated: pytest run scoped to ingestion/
├── apps/
│   └── web/                     # empty placeholder for now, not created yet
├── ingestion/
│   ├── pyproject.toml           # moved from root, unchanged content (where=["src"], testpaths=["tests"])
│   ├── src/
│   │   └── lidl_tracker/…       # unchanged, verbatim
│   └── tests/
│       ├── test_cards.py
│       ├── test_cli_ingest.py
│       ├── test_ingestion.py
│       ├── test_parsers.py
│       ├── test_r2.py
│       ├── test_search.py
│       └── test_watch_state.py  # test_image_ranking.py REMOVED from here
├── migrations/                  # unchanged, stays at root
│   ├── 001_create_flyers.sql
│   ├── 002_create_product_cards.sql
│   └── 003_add_product_card_image.sql
├── tools/
│   ├── __init__.py
│   ├── capture_network.py
│   ├── dump_flyer_links.py
│   ├── inspect_api.py
│   ├── inspect_results.py
│   ├── probe_page.py
│   ├── run_watch.bat            # ROOT logic (%~dp0..) still correct, one level below repo root
│   └── image_ranking/
│       ├── __init__.py
│       ├── evaluate.py          # import fixed to package-qualified
│       ├── ranker.py
│       ├── review.py
│       ├── README.md
│       └── tests/
│           └── test_image_ranking.py   # MOVED here, own test entrypoint
├── data/                        # stays at root (see note below)
├── .local/                      # stays at root
├── docs/                        # stays at root (see note below)
├── compose.yaml
├── .env.example
├── .gitignore
└── README.md                    # trimmed "Layout" section rewritten for new tree, links to ingestion/README
```

### Open decision flagged (not in your original skeleton): `data/`, `.local/`, `docs/`

These weren't mentioned in your target tree. I recommend **leaving them at the repo root** rather than moving them into `ingestion/`, because:
- CLI commands resolve `data/...` and `.local/...` as relative paths from the invocation cwd, not from package location — moving them would require touching `.env.example`, `cli_watch.py`/`cli_ingest.py` defaults, `docs/scheduling.md`'s absolute path, `tools/run_watch.bat`, and the `watch.yml` `git add data/state/watch_state.json` step, and the `.gitignore` negation pattern — a lot of moving parts for a directory that (a) isn't code, and (b) will plausibly be shared by a future `apps/api` too (same DB/state).
- `docs/` currently documents only the ingestion pipeline, but keeping it at root lets it grow into a multi-app docs home later (e.g. `docs/web.md`) without another move.

If you'd rather have `ingestion/` be fully self-contained (including its own data/docs), say so and I'll fold that into the plan — it's a bigger diff (touches CI, `.gitignore`, `run_watch.bat`, `scheduling.md`) but is mechanical.

---

## Step-by-step migration plan

1. **Move Python source tree**
   - `git mv pyproject.toml ingestion/pyproject.toml`
   - `git mv src ingestion/src`
   - `git mv tests ingestion/tests` (all files except `test_image_ranking.py`)
   - No changes needed inside `ingestion/pyproject.toml` (`where=["src"]`, `testpaths=["tests"]` remain correct relative to their new location).

2. **Decouple `tools/image_ranking`**
   - `git mv tests/test_image_ranking.py tools/image_ranking/tests/test_image_ranking.py`
   - Fix `tools/image_ranking/evaluate.py` import to `from tools.image_ranking.ranker import rank_cards`.
   - Add a minimal `tools/image_ranking/tests/__init__.py` or a small `pytest.ini`/`conftest.py` at repo root scope so `tools.image_ranking` resolves when running `pytest tools/image_ranking/tests` from repo root (cwd already on `sys.path` when invoked that way — verify with a dry run).
   - Update `tools/image_ranking/README.md` to drop the `PYTHONPATH=tools/image_ranking` instruction now that imports are package-qualified; document `python -m pytest tools/image_ranking/tests` instead.

3. **Update CI workflows**
   - `ingest.yml`, `watch.yml`: change `pip install -e .` → `pip install -e ./ingestion` (run from repo root, no `working-directory` needed — package installs into the venv regardless of cwd). Runtime steps (`python -m lidl_tracker.cli_ingest`, `cli_watch`) keep default working directory = repo root so `data/...` relative paths keep resolving.
   - `watch-test.yml`: 
     - `pip install -e "./ingestion[dev]"`
     - `python -m pytest ingestion/tests` (main suite)
     - optionally add a second step `python -m pytest tools/image_ranking/tests` if you want the R&D tool's tests to still run in CI (recommended, since it's cheap and currently already runs).

4. **Update docs**
   - `README.md`: rewrite "Layout" section to reflect `apps/`, `ingestion/`, `migrations/`, `tools/`, `.github/`; update install instructions (`pip install -e "./ingestion[dev]"`).
   - `docs/acquisition.md`: no change needed (`tools/capture_network.py` path unchanged).
   - `docs/scheduling.md`: no path changes needed for `run_watch.bat` (stays under `tools/`), but flag that the live Windows Scheduled Task registration is unaffected only because `tools/` doesn't move.
   - `src/lidl_tracker/acquisition.py` docstring reference to `tools/capture_network.py` — unaffected (still correct, both stay at root-relative distance... actually `tools/` is now a repo-root sibling of `ingestion/`, so the relative docstring mention is still accurate since it's prose, not a path resolved at runtime).

5. **No changes required for:**
   - `migrations/*.sql` (root-relative comments already correct; nothing executes them).
   - `compose.yaml` (no path coupling).
   - `.gitignore` (no `src/`, `tests/`, `tools/`, `migrations/` patterns exist; `data/state/*` negation untouched since `data/` doesn't move).
   - `data/`, `.local/`, `.env.example` (per decision above).

6. **Verification checklist after the move**
   - `pip install -e "./ingestion[dev]"` succeeds from repo root.
   - `python -m pytest ingestion/tests` passes (7 files, unchanged imports since `lidl_tracker` package name/layout didn't change).
   - `python -m pytest tools/image_ranking/tests` passes with the fixed import.
   - `python -m lidl_tracker.cli_ingest --help` and `cli_watch --help` work from repo root.
   - CI workflows dry-run (or at least a `act`/manual read-through) confirm `git add data/state/watch_state.json` step still finds the file (data/ didn't move).
   - Windows Scheduled Task still points at the same absolute `tools/run_watch.bat` path (unaffected).

This plan preserves all runtime/database behavior, doesn't touch any Python logic, and gets you to your requested `apps/ / ingestion/{src,tests} / migrations/ / tools/ / .github/` shape with a clearly identified, small set of side files (CI YAML, two docs, one import fix) that must change in lockstep. Let me know if you want `data/`/`docs/` moved into `ingestion/` as well, or if you'd like me to proceed executing this plan.
