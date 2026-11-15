# Brand Compliance QA Pipeline

A multimodal video compliance QA pipeline built on Microsoft Azure. It analyzes video content against brand and regulatory guidelines using Azure Video Indexer, Azure OpenAI, and Azure AI Search, orchestrated as an agentic workflow with LangGraph.

## Overview

Manually reviewing video ads and brand content for compliance is slow and inconsistent. This pipeline automates the first pass: it ingests a video, extracts transcript, on-screen text, and visual signals, retrieves the relevant compliance rules, and produces a structured report of violations and passes.

## Features

- **Multimodal analysis**: transcript, OCR, and scene insights from Azure Video Indexer, with reasoning by Azure OpenAI
- **RAG over compliance rules**: guidelines are chunked, embedded, and indexed in Azure AI Search (vector + hybrid search)
- **Agentic workflow**: LangGraph orchestrates the steps as a stateful graph
- **Structured output**: per-rule verdicts with timestamped evidence
- **Secure by default**: secrets in Azure Key Vault, auth via Managed Identity / `DefaultAzureCredential`
- **Observability**: tracing and logs through Azure Application Insights
- **Automatic cleanup**: temporary media files are removed after each run
- **uv workspace**: reproducible, fast dependency management

## Architecture

```
Video input
    │
    ▼
Azure Blob Storage (upload)
    │
    ▼
Azure Video Indexer
(transcript · OCR · labels · scenes)
    │
    ▼
LangGraph orchestrator ◄──── Azure AI Search (compliance rules, vector index)
    │                         ▲
    │                         │ embeddings: Azure OpenAI
    ▼
Compliance evaluation (Azure OpenAI GPT-4o)
    │
    ▼
Structured QA report (JSON → Blob Storage)
```

## Tech Stack

| Layer | Azure Service / Tool |
|---|---|
| Orchestration | LangGraph |
| Video + speech + OCR | Azure Video Indexer |
| LLM reasoning | Azure OpenAI (GPT-4o) |
| Embeddings | Azure OpenAI (`text-embedding-3-large`) |
| Vector search | Azure AI Search |
| Storage | Azure Blob Storage |
| Secrets | Azure Key Vault |
| Monitoring | Azure Application Insights |
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
├── infra/                  # optional Bicep/Terraform for Azure resources
├── .env.example
└── README.md
```

> Update this tree to match your actual folder layout.

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli)
- An Azure subscription with these resources provisioned:
  - Azure OpenAI (a chat deployment and an embeddings deployment)
  - Azure AI Search
  - Azure Video Indexer (connected to an Azure Media Services/Storage account)
  - Azure Blob Storage account
  - (Optional) Key Vault and Application Insights

### Installation

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
uv sync
az login
```

### Configuration

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=your_key            # omit if using Managed Identity
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://<your-search>.search.windows.net
AZURE_SEARCH_API_KEY=your_key
AZURE_SEARCH_INDEX=compliance-rules

# Azure Video Indexer
AZURE_VI_ACCOUNT_ID=your_account_id
AZURE_VI_LOCATION=eastus
AZURE_VI_RESOURCE_ID=/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.VideoIndexer/accounts/<name>

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
AZURE_STORAGE_CONTAINER=videos

# Optional
APPLICATIONINSIGHTS_CONNECTION_STRING=your_connection_string
```

> In production, prefer `DefaultAzureCredential` with Managed Identity and keep secrets in Key Vault instead of `.env`.

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
      "evidence": "Spoken claim at 00:12 with no on-screen disclaimer (OCR found none)",
      "timestamp": "00:00:12",
      "confidence": 0.86
    }
  ]
}
```

## Deployment

The pipeline can run as:

- **Azure Container Apps / Container Instances**: containerize with Docker and deploy
- **Azure Functions**: trigger on new blob uploads for event-driven reviews
- **Azure ML / Batch**: for large-scale batch processing

## Troubleshooting

- **401/403 from Azure services**: confirm `az login` is active, role assignments (e.g. *Cognitive Services OpenAI User*, *Search Index Data Contributor*, *Storage Blob Data Contributor*) are set, and keys are correct.
- **429 rate limits on Azure OpenAI**: increase your deployment's TPM quota or add retry with exponential backoff.
- **Video Indexer stuck in "Processing"**: large videos take time; poll the index status and check the account's region and quota.
- **Dependency resolution issues**: run `uv lock --upgrade` and re-sync.
- **Leftover temp files**: the pipeline cleans up automatically, but you can safely delete the temp directory if a run is interrupted.

## Roadmap

- [ ] Batch processing for multiple videos
- [ ] Web UI for uploading videos and viewing reports
- [ ] Evaluation set to measure precision and recall of violation detection
- [ ] Azure AI Content Safety integration for additional checks
- [ ] Support for custom rule sets per brand

## Contributing

Issues and pull requests are welcome. Please open an issue first to discuss major changes.

## License

Distributed under the MIT License. See `LICENSE` for details.

## Author

**Flacko**: [GitHub](https://github.com/<your-username>) · [LinkedIn](https://linkedin.com/in/<your-handle>)
