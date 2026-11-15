# Brand Compliance QA Pipeline

A multimodal video compliance QA pipeline that analyzes video content against brand and regulatory guidelines. It combines speech transcription, visual understanding, and retrieval-augmented reasoning, orchestrated as an agentic workflow with LangGraph.

## Overview

Manually reviewing video ads and brand content for compliance is slow and inconsistent. This pipeline automates the first pass: it ingests a video, extracts audio and visual signals, retrieves the relevant compliance rules, and produces a structured report of violations and passes.

## Features

- **Multimodal analysis**: audio transcription (Groq) plus visual and contextual understanding (Gemini)
- **RAG over compliance rules**: guidelines are embedded and indexed in FAISS for fast retrieval
- **Agentic workflow**: LangGraph orchestrates the steps as a stateful graph
- **Structured output**: per-rule verdicts with supporting evidence
- **Automatic cleanup**: temporary media files are removed after each run
- **uv workspace**: reproducible, fast dependency management

## Architecture

```
Video input
    │
    ▼
Preprocessing (extract audio / frames)
    │
    ├──► Transcription (Groq) ─────────┐
    │                                  ▼
    └──► Visual analysis (Gemini) ──► LangGraph orchestrator
                                       │
                         FAISS retrieval of relevant rules
                                       │
                                       ▼
                         Compliance evaluation (LLM)
                                       │
                                       ▼
                             Structured QA report
```

## Tech Stack

| Layer | Tool |
|---|---|
| Orchestration | LangGraph |
| Speech-to-text | Groq |
| Vision / reasoning | Google Gemini |
| Vector search | FAISS |
| Package management | uv (workspace) |
| Language | Python 3.11+ |

## Project Structure

```
.
├── pyproject.toml          # uv workspace root
├── packages/
│   ├── ...                 # workspace members (update to match your layout)
├── data/
│   └── guidelines/         # compliance rule documents
├── .env.example
└── README.md
```

> Update this tree to match your actual folder layout.

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- ffmpeg (for audio/frame extraction)
- API keys for Groq and Google Gemini

### Installation

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
uv sync
```

### Configuration

Copy the example env file and add your keys:

```bash
cp .env.example .env
```

```env
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
```

### Build the guideline index

```bash
uv run python -m <package>.index_guidelines --source data/guidelines
```

### Run the pipeline

```bash
uv run python -m <package>.main --video path/to/video.mp4
```

## Example Output

```json
{
  "video": "sample_ad.mp4",
  "overall_status": "FAIL",
  "findings": [
    {
      "rule": "Claims must include a disclaimer",
      "status": "FAIL",
      "evidence": "Spoken claim at 00:12 with no on-screen disclaimer",
      "confidence": 0.86
    }
  ]
}
```

## Troubleshooting

- **Gemini API errors**: check that your key is valid and that you are within quota; retry transient 429/5xx errors with backoff.
- **Dependency resolution issues**: run `uv lock --upgrade` and re-sync.
- **Leftover temp files**: the pipeline cleans up automatically, but you can safely delete the temp directory if a run is interrupted.

## Roadmap

- [ ] Batch processing for multiple videos
- [ ] Web UI for uploading videos and viewing reports
- [ ] Evaluation set to measure precision and recall of violation detection
- [ ] Support for custom rule sets per brand

## Contributing

Issues and pull requests are welcome. Please open an issue first to discuss major changes.

## License

Distributed under the MIT License. See `LICENSE` for details.

## Author

**Flacko**: [GitHub](https://github.com/<your-username>) · [LinkedIn](https://linkedin.com/in/<your-handle>)
