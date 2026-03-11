To test The Local Eye properly, you need your local environment to handle both the "processing" (Node.js) and the "seeing" (Ollama).

Since you are running this on your own machine, this is where the "Sovereignty" actually happens—no data leaves your local network during this phase.

🛠️ The Installation Checklist

## The Vision Step

1. Ollama & The Vision Model
[Ollama](https://ollama.com/) needs the specific weights for the multimodal model to handle images.

Install Ollama with:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Then run this in your terminal:

```bash
ollama pull llama3.2-vision
```
Note: If you have limited VRAM (under 8GB), you can also try `ollama pull moondream` which is a much smaller but very capable vision model.

2. Node.js Dependencies (The Processor)
Your MCP server needs the sharp library to handle the image "airlock" (resizing/formatting).

Action: In your `mcp-forensic-analyzer` root (or wherever your `package.json` lives):

```bash
npm install sharp
```

3. Python Dependencies (The Agent)
The orchestrator needs to pass file paths and handle the vision results. All image processing uses sharp in the MCP server; no Python image libs required.

For `--provider ollama` (LLM synthesis and Sovereign Vault vision):
```bash
pip install ollama
```

🖼️ What image should you use for testing?
For a "Forensic" demo, you want an image that has text, texture, and metadata for the model to "chew" on.

Recommendation: Don't just use a random cat photo. Use a high-res photo or scan of a book's title page or a copyright page.

The "Golden Sample": Take a photo of a physical book you have nearby.

Why? It allows you to test if the Vision Agent can:

Read the Year (OCR).

Identify the Publisher Logo (Pattern recognition).

Spot "Foxing" or Water damage (Visual forensics).

## The Redactor Step

1. The Brains (NLP Models)
We need spaCy—the industry standard for industrial-strength Natural Language Processing.

Action: Run these in your terminal:

```bash
pip install spacy presidio-analyzer presidio-anonymizer
python -m spacy download en_core_web_lg
```

> Note: We use the lg (large) model instead of sm (small) because in forensics, missing a name due to a smaller vector space is a compliance failure.