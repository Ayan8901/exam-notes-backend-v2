import type { Express, Request, Response } from "express";
import { createServer, type Server } from "node:http";
import multer from "multer";

/* ---------------- UPLOAD CONFIG ---------------- */

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 12 * 1024 * 1024 },
});

/* ---------------- TEXT CLEANER ---------------- */

function cleanOCRText(text: string) {
  return text
    .replace(/[^\x00-\x7F]/g, " ")
    .replace(/\s+/g, " ")
    .replace(/([A-Za-z])\1{3,}/g, "$1$1")
    .replace(/[^a-zA-Z0-9.,:;()%\- \n]/g, " ")
    .trim();
}

/* ---------------- SMART EXAM NOTES BUILDER ---------------- */

function generateNotesFromText(text: string) {
  const lines = text
    .split(/[\n\.]/)
    .map(l => l.trim())
    .filter(l => l.length > 20);

  let bullets: string[] = [];

  for (const line of lines) {
    const lower = line.toLowerCase();

    if (
      lower.includes(" is ") ||
      lower.includes(" are ") ||
      lower.includes(" defined as") ||
      lower.includes(" refers to")
    ) {
      bullets.push(`• Definition: ${line}`);
    } else if (/\d/.test(line)) {
      bullets.push(`• ${line}`);
    } else if (line.length < 140) {
      bullets.push(`• ${line}`);
    }
  }

  bullets = bullets.slice(0, 60);

  const title =
    bullets[0]?.replace(/^•\s*/, "").slice(0, 80) ||
    "Study Notes";

  return {
    title,
    content: `## ${title}\n\n${bullets.join("\n")}`,
  };
}

/* ---------------- ROUTES ---------------- */

export async function registerRoutes(app: Express): Promise<Server> {

  /* ---------- TEXT → NOTES (MAIN WORKING MODE) ---------- */

  app.post("/api/generate-notes-from-text", async (req: Request, res: Response) => {
    try {
      const { text } = req.body;

      if (!text || typeof text !== "string" || text.trim().length < 10) {
        return res.status(400).json({ error: "Valid text required" });
      }

      console.log("📝 Text notes request received");

      const cleaned = cleanOCRText(text);
      const notes = generateNotesFromText(cleaned);

      res.json(notes);

    } catch (err) {
      console.error("TEXT MODE FAIL:", err);
      res.status(500).json({ error: "Failed to generate notes" });
    }
  });

  /* ---------- IMAGE ROUTE — SAFE DISABLED RESPONSE ---------- */

  app.post("/api/generate-notes", upload.array("images", 25), async (_req, res) => {
    console.log("⚠️ Image route called — not supported on Railway");

    return res.status(503).json({
      error: "Image OCR not available on cloud deploy. Use Paste Text mode.",
    });
  });

  return createServer(app);
}
