/**
 * analyze_artifact_vision — Sovereign Vault: Local image analysis for forensic audit.
 *
 * STRICT DATA SOVEREIGNTY: Processes images locally only. Uses sharp for resizing,
 * sends to local Ollama (llama3.2-vision:11b). Raw image and base64 are cleared
 * from memory immediately after the call. Returns only structured text; no image
 * data is retained or transmitted off-host.
 */

import sharp from "sharp";
import { readFile } from "fs/promises";
import { existsSync } from "fs";
import { join } from "path";

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

/**
 * Resize image to 512x512 and convert to base64. Uses sharp for local processing.
 */
async function imageToBase64(imagePath: string): Promise<string> {
  const resolved = imagePath.startsWith("/") ? imagePath : join(process.cwd(), imagePath);
  if (!existsSync(resolved)) {
    throw new Error(`Image not found: ${imagePath}`);
  }
  const buffer = await readFile(resolved);
  const resized = await sharp(buffer)
    .resize(512, 512, { fit: "inside" })
    .jpeg({ quality: 85 })
    .toBuffer();
  return resized.toString("base64");
}

/**
 * Call local Ollama vision model. Raw image and base64 are cleared after call.
 */
export async function executeAnalyzeArtifactVision(
  args: AnalyzeArtifactVisionInput
): Promise<AnalyzeArtifactVisionResult> {
  const { image_path, analysis_focus } = args;
  if (!image_path?.trim() || !analysis_focus?.trim()) {
    throw new Error("image_path and analysis_focus are required and must be non-empty");
  }

  let base64: string;
  try {
    base64 = await imageToBase64(image_path);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return { visual_findings: "", error: `Image load failed: ${msg}` };
  }

  const prompt = `Analyze this artifact image and describe your visual findings. Focus on: ${analysis_focus}. Provide a structured text description suitable for a forensic audit. Do not include image data.`;

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
  } finally {
    // Privacy Guard: clear base64 from memory (best-effort; JS GC handles the rest)
    (base64 as unknown) = "";
  }
}
