/**
 * analyze_artifact_vision — Sovereign Vault: Local image analysis for forensic audit.
 *
 * STRICT DATA SOVEREIGNTY: Processes images locally only. Uses sharp for resizing,
 * sends to local Ollama (llama3.2-vision:11b). Resized image buffer is zeroed
 * after the API call (Buffer.fill(0)); JavaScript strings cannot be cleared.
 * Returns only structured text; no image data retained or transmitted off-host.
 */

import sharp from "sharp";
import { readFile, realpath } from "fs/promises";
import { resolve, relative, isAbsolute, sep } from "path";

export interface AnalyzeArtifactVisionInput {
  image_path: string;
  analysis_focus: string;
}

export interface AnalyzeArtifactVisionResult {
  visual_findings: string;
  error?: string;
}

function assertLocalOllamaHost(url: string): string {
  try {
    const u = new URL(url);
    const host = u.hostname.toLowerCase();
    if (host === "localhost" || host === "127.0.0.1" || host === "::1") return url;
    // IPv6: fc00::/7 (unique local), fe80::/10 (link-local)
    if (host.startsWith("fc") || host.startsWith("fd") || /^fe[89ab]/.test(host)) {
      return url;
    }
    const octets = host.split(".").map(Number);
    if (
      octets.length === 4 &&
      octets.every((n) => !Number.isNaN(n) && n >= 0 && n <= 255)
    ) {
      if (octets[0] === 10) return url;
      if (octets[0] === 172 && octets[1] >= 16 && octets[1] <= 31) return url;
      if (octets[0] === 192 && octets[1] === 168) return url;
    }
  } catch {
    /* invalid URL */
  }
  throw new Error(
    `OLLAMA_HOST must resolve to a local endpoint (localhost, 127.0.0.1, or private IP). Got: ${url}`
  );
}
const OLLAMA_HOST = assertLocalOllamaHost(
  process.env.OLLAMA_HOST ?? "http://localhost:11434"
);
const VISION_MODEL = process.env.OLLAMA_VISION_MODEL ?? "llama3.2-vision:11b";
const OLLAMA_TIMEOUT_MS = (() => {
  const raw = process.env.OLLAMA_VISION_TIMEOUT_MS?.trim() || "120000";
  const n = parseInt(raw, 10);
  return n > 0 && !Number.isNaN(n) ? n : 120000;
})();
const IMAGE_BASE = process.env.SOVEREIGN_VAULT_IMAGE_BASE ?? process.cwd();

/**
 * Sanitize analysis_focus for safe prompt embedding: strip control chars, newlines, limit length.
 */
function sanitizeAnalysisFocus(input: string): string {
  return input
    .replace(/[\0-\x1f\x7f]/g, "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 200);
}

/**
 * Resize image to 512x512. Returns buffer; caller must zero it after use.
 * Rejects path traversal and symlink escapes (uses realpath to dereference).
 */
async function loadAndResizeImage(imagePath: string): Promise<Buffer> {
  const base = resolve(IMAGE_BASE);
  const resolved = resolve(base, imagePath);
  const rel = relative(base, resolved);
  if (rel.startsWith("..") || isAbsolute(rel)) {
    throw new Error(
      `Path traversal not allowed: ${imagePath}. Paths are resolved relative to SOVEREIGN_VAULT_IMAGE_BASE (default: cwd).`
    );
  }
  const realBase = await realpath(base);
  let realResolved: string;
  try {
    realResolved = await realpath(resolved);
  } catch {
    throw new Error(`Image not found: ${imagePath}`);
  }
  if (
    realResolved !== realBase &&
    !realResolved.startsWith(realBase + sep)
  ) {
    throw new Error(
      `Path traversal not allowed: ${imagePath} resolves outside SOVEREIGN_VAULT_IMAGE_BASE (symlink escape).`
    );
  }
  // Read from realResolved (verified canonical path) to prevent TOCTOU symlink swap
  const buffer = await readFile(realResolved);
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
  const safeFocus = sanitizeAnalysisFocus(analysis_focus);
  const prompt = `Analyze this artifact image and describe your visual findings. Focus on: ${safeFocus}. Provide a structured text description suitable for a forensic audit. Do not include image data.`;

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
    if (e instanceof Error && e.name === "AbortError") {
      return {
        visual_findings: "",
        error: `Ollama vision call timed out after ${OLLAMA_TIMEOUT_MS}ms`,
      };
    }
    throw e;
  } finally {
    clearTimeout(timeoutId);
    // Privacy Guard: zero the resized image buffer (JS strings cannot be cleared)
    buffer.fill(0);
  }
}
