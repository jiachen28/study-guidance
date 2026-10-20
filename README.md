# Study Guidance

Study Guidance is a local web application for choosing an appropriate type of assistance for university tasks. Users describe a task and receive a category, a tool-type recommendation, relevant restrictions, a verification checklist, and supporting reference links. The system accepts new task descriptions; the evaluation scenarios do not limit its possible inputs.

## How it works

The application combines a local Qwen2.5 3B language model (served through Ollama), TF–IDF retrieval over a small attributed reference collection, and a deterministic policy layer for explicitly restricted uses. Categories are `Coding`, `Research`, `Workflow`, and `None`. A keyword classifier provides a baseline for comparison and an explicitly marked fallback when the model is unavailable. Recommendations are advisory and do not override unit rules or establish that a particular assessment permits outside help.

## Installation and use

Requirements: Python 3.10 or later, Ollama, and the `qwen2.5:3b-instruct` model. The Python application uses only the standard library.

```sh
ollama pull qwen2.5:3b-instruct
python -m app.server
```

Open <http://127.0.0.1:8765> in a browser. Ollama must be running locally. The application binds to localhost and does not send the entered task to a hosted AI API. Do not enter confidential information without appropriate authorisation.

## Study method

`data/scenarios.csv` contains 60 authored scenarios: 40 for development and 20 held out for evaluation. They represent a small controlled exercise rather than a representative sample of all student queries. The dataset has no answer column.

Each group member independently labels **all 60 scenarios**, using one of the four category names. The matching files are:

- `data/annotations_Jiachen_Lu.csv`
- `data/annotations_Siyuan_Chen.csv`
- `data/annotations_Xin_Chen.csv`

Keep IDs and task descriptions unchanged. The `reason` column records the rationale when appropriate. Initial labels should be completed independently, without consulting model predictions.

After all three files are complete, run:

```sh
python run_study.py
```

If there are disagreements, the program writes `results/adjudication.csv` and stops. The group reviews the disputed items and fills in **both** `consensus_label` and `resolution_reason` in that file. Run the **same command** again. If every item already has unanimous agreement, no extra discussion file is needed.

The command then runs the local model on the 20 held-out scenarios using the packaged code and creates `results/consensus.csv`, `evaluation_raw.csv`, `metrics.json`, `case_analysis.csv`, `summary.txt`, and four `.svg` figures. Evaluation results are stored with a fingerprint of the executable pipeline, dataset and model identifier. Interrupted inference resumes from completed results with the same fingerprint; it does not silently reuse results from incompatible code or data.

The report should use the measured results, identify notable errors, compare the keyword baseline, model, and policy-guarded system, and discuss uncertainty arising from the small authored sample. No human labels or experimental scores are supplied in advance for the other two members.

## Testing

```sh
python -m unittest discover -s tests -v
python verify.py
```

Automated tests cover classification, policy checks, data integrity, CSV workflows, metrics and HTTP endpoints. The verification command also checks the live local model. Unit tests use isolated test fixtures and do not modify the independent annotation files or official evaluation results.

## Project files

- `app/` — recommendation logic, local model interface, retrieval, policy checks, web server, and evaluation utilities
- `app/static/` — web interface
- `data/` — scenarios, independent annotations, and attributed reference notes
- `run_study.py` — group consensus, evaluation, and report-figure entry point
- `tests/`, `verify.py` — regression and local integration checks
- `figures/` — system architecture and study workflow diagrams
- `results/` — real outputs produced by the study workflow

## Scope

The reference index contains concise project-authored notes linked to external sources; these notes are summaries rather than policy determinations. The safety rules only recognise selected types of restricted requests. The tool suggestions identify suitable **types** of software and workflows, not verified rankings of commercial products. Classification quality, advice quality and suitability for real-world deployment must be assessed separately.

Supporting sources are recorded in `data/knowledge.json`, including guidance from the University of Sydney, UNESCO, NIST and OWASP. Cite the original publications directly in the report.
