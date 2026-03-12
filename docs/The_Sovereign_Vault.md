# The Sovereign Vault Manifest

## Executive Summary
The Sovereign Vault is an architectural extension of the MCP Forensic Analyzer. It addresses the Data Sovereignty Gap: the inherent risk of exposing high-value proprietary visual artifacts and "Golden Data" to third-party cloud models. This phase transitions the system into a "Zero-Trust" posture regarding external LLM providers.

## The Three Pillars of Sovereignty
- **Pillar 1:** Local Vision (Edge-Based Feature Extraction): High-resolution scans never leave the local environment. We use SLMs (Small Language Models) at the edge to convert pixels into text-based metadata.
- **Pillar 2:** The Redactor (Contextual PII Obfuscation): Automatic detection and scrubbing of sensitive identifiers within proprietary bibliography data before cloud routing.
- **Pillar 3:** The Control Tower (Security Observability): A unified dashboard providing visibility into security posture, cognitive budgeting, and forensic reliability.

## Technical Stack Rationale
- **Vision:** Ollama (Llama 3.2 Vision) for sovereign image reasoning.
- **Preprocessing:** `sharp` (Node.js) to ensure image normalization before inference.
- **Privacy:** Microsoft Presidio & Spacy for enterprise-grade PII detection.
- **Dashboard:** Streamlit for high-velocity executive reporting.