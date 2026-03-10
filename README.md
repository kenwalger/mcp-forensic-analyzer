# MCP Forensic Analyser
### A Reference Implementation for Protocol-Driven AI Auditing

The **MCP Forensic Analyser** is a Model Context Protocol (MCP) server designed to facilitate deep-dive archival audits and metadata reconciliation. Built as the cornerstone of the [End of Glue Code series](LINK_TO_YOUR_BLOG), it demonstrates how to move from brittle API integrations to a standardized, discovery-based AI architecture.

## 🏛️ Architecture: The "Zero-Glue" Stack
Unlike traditional integrations, this server allows any MCP-compatible agent (Claude, Oracle 26ai, local SLMs) to dynamically discover forensic tools without custom code.

The project follows an Enterprise AI Mesh pattern, decoupling intelligence (Agents) from capability (MCP Servers). It is designed to scale from a local 'Forensic Clean-Room' to an enterprise-grade governed environment using Oracle 26ai for immutable audit trails and row-level security.

## ⚖️ Reliability & Observability
We move beyond 'vibe-checking' agents by implementing an **LLM-as-a-Judge** framework.
- **Golden Dataset:** A ground-truth set of forensic cases used to benchmark agent performance.
- **Automated Evaluation:** Every architectural change is audited by a high-reasoning 'Judge Agent' to ensure zero regression in forensic accuracy.
- **Structured Logging:** All provider errors and reasoning chains are captured for post-mortem analysis, moving away from silent failures.

## 💰 Cognitive Budgeting (The Accountant)
To manage enterprise scale, we implement **Semantic Routing**:
- **Tiered Intelligence:** Requests are classified by complexity. Simple tasks are routed to local SLMs (Phi-4/Llama 3.2), while complex forensic tasks are escalated to Claude 3.5.
- **Cost Optimization:** This approach reduces inference costs by up to 80% without sacrificing high-end reasoning where it matters.

> **Architect’s Summary:** This implementation solves the three "Last Mile" problems of enterprise AI: Standardization (via MCP), Reliability (via automated LLM-as-a-Judge), and Sustainability (via Tiered Intelligence Routing). It transitions AI from brittle, high-cost experiments to governed, cost-optimized infrastructure.

## 🛠️ Features
- **Discovery-First:** Implements the full MCP Lifecycle (Handshake -> Manifest -> Execution).
- **Archival Tools:** Specialized functions for metadata cross-referencing and watermark verification.
- **Polyglot Ready:** Built in TypeScript, designed to be orchestrated by Python-based agentic frameworks.

## ⚙️ Configuration & Prompts
Agent logic is decoupled from the execution engine. System instructions are managed in `config/prompts.yaml`, allowing for A/B testing of prompt versions and model-specific tuning without redeploying code.

## 🚀 Quick Start

### Installation
```bash
npm install
npm run build
```

## 🏠 Edge AI: Running Locally with SLMs
This branch demonstrates the "Forensic Clean-Room" setup, moving inference from the cloud to your local machine.

### Prerequisites
1. **Ollama:** [Download and install Ollama](https://ollama.com/).
2. **Model:** Pull the default model (or another of your choice):
   ```bash
   ollama pull llama3.2
   ```
   The orchestrator defaults to `llama3.2`; for other models (e.g. phi4), set `LLM_MODEL` (see below).

### Running the Local Orchestrator
To run the multi-agent team using the local SLM:

```bash
python examples/orchestrator.py --provider ollama
```

To use a different model or Ollama host, set the environment variables:
```bash
LLM_MODEL=phi4 python examples/orchestrator.py --provider ollama
OLLAMA_HOST=http://192.168.1.10:11434 python examples/orchestrator.py --provider ollama
```

> Note: SLMs require explicit instruction tuning. The orchestrator includes an optimized system prompt to help small models handle MCP JSON schemas effectively.

### Running The Judge
```bash
python examples/evaluator.py
```

### Running with The Accountant (Semantic Router)
Route requests by complexity to save budget—simple queries use local SLMs, complex forensic tasks use cloud models:

```bash
python examples/router.py --query "Look up The Hobbit" --title "The Hobbit" --author "Tolkien"
python examples/orchestrator.py --use-accountant --query "Compare points of issue and binding across editions" --title "The Great Gatsby"
```

Configure routing via `ACCOUNTANT_MODEL` (classification model), `ACCOUNTANT_CLASSIFICATION_PROVIDER` (default: ollama; use `lm_studio` if only LM Studio available), `ACCOUNTANT_LEVEL_1_PROVIDER`, `ACCOUNTANT_LEVEL_2_PROVIDER`.
