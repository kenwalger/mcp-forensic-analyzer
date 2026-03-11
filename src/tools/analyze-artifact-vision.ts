/**
 * analyze_artifact_vision — Sovereign Vault: Local image analysis for forensic audit.
 *
 * STRICT DATA SOVEREIGNTY: Processes images locally only. Uses sharp for resizing,
 * sends to local Ollama (llama3.2-vision:11b). Resized image buffer is zeroed
 * after the API call (Buffer.fill(0)); JavaScript strings cannot be cleared.
 * Returns only structured text; no image data retained or transmitted off-host.
 */

import sharp from "sharp";
import { readFile } from "fs/promises";
import { existsSync } from "fs";
import { resolve, relative, isAbsolute } from "path";

export interface AnalyzeArtifactVisionInput {
  image_path: string;
  analysis_focus: string;
}

export interface AnalyzeArtifactVisionResult {
  visual_findings: string;
  error?: string;
}

const OLLAMA_HOST = process.env.OLLAMA_HOST ?? "http://localhost:11434";
const VISION_MODEL = process.env.OLLAMA_VISION_MODEL ?? "llama3.2-vision:11b";
const OLLAMA_TIMEOUT_MS = parseInt(
  process.env.OLLAMA_VISION_TIMEOUT_MS ?? "120000",
  10
);
const IMAGE_BASE = process.env.SOVEREIGN_VAULT_IMAGE_BASE ?? process.cwd();

/**
 * Resize image to 512x512. Returns buffer; caller must zero it after use.
 * Rejects path traversal (e.g. ../../etc/passwd).
 */
async function loadAndResizeImage(imagePath: string): Promise<Buffer> {
  const base = resolve(IMAGE_BASE);
  const resolved = resolve(base, imagePath);
  const rel = relative(base, resolved);
  if (rel.startsWith("..") || isAbsolute(rel)) {
    throw new Error(`Path traversal not allowed: ${imagePath}`);
  }
  if (!existsSync(resolved)) {
    throw new Error(`Image not found: ${imagePath}`);
  }
  const buffer = await readFile(resolved);
  return sharp(buffer)
    .resize(512, 512, { fit: "inside" })
    .jpeg({ quality: 85 })
    .toBuffer();
}

/**
 * Call local Ollama vision model. Resized buffer is zeroed after call (Buffer.fill(0)).
 */
export async function executeAnalyzeArtifactVision(
  args: AnalyzeArtifactVisionInput
): Promise<AnalyzeArtifactVisionResult> {
  const { image_path, analysis_focus } = args;
  if (!image_path?.trim() || !analysis_focus?.trim()) {
    throw new Error("image_path and analysis_focus are required and must be non-empty");
  }

  let buffer: Buffer;
  try {
    buffer = await loadAndResizeImage(image_path);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return { visual_findings: "", error: `Image load failed: ${msg}` };
  }

  const base64 = buffer.toString("base64");
  const prompt = `Analyze this artifact image and describe your visual findings. Focus on: ${analysis_focus}. Provide a structured text description suitable for a forensic audit. Do not include image data.`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), OLLAMA_TIMEOUT_MS);

  try {
    const res = await fetch(`${OLLAMA_HOST}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model: VISION_MODEL,
        messages: [
          {
            role: "user",
            content: prompt,
            images: [base64],
          },
        ],
        stream: false,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      const text = await res.text();
      return {
        visual_findings: "",
        error: `Ollama vision call failed (${res.status}): ${text.slice(0, 200)}`,
      };
    }

    const data = (await res.json()) as { message?: { content?: string } };
    const text = data?.message?.content?.trim() ?? "";
    return { visual_findings: text };
  } catch (e) {
    clearTimeout(timeoutId);
    if (e instanceof Error && e.name === "AbortError") {
      return {
        visual_findings: "",
        error: `Ollama vision call timed out after ${OLLAMA_TIMEOUT_MS}ms`,
      };
    }
    throw e;
  } finally {
    // Privacy Guard: zero the resized image buffer (JS strings cannot be cleared)
    buffer.fill(0);
  }
}
