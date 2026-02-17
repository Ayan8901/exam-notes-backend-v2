"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerRoutes = registerRoutes;
const node_http_1 = require("node:http");
const multer_1 = __importDefault(require("multer"));
const sharp_1 = __importDefault(require("sharp"));
const inference_1 = require("@huggingface/inference");
/* ---------------- SETUP ---------------- */
const hfToken = process.env.HF_API_KEY;
const hf = hfToken ? new inference_1.HfInference(hfToken) : null;
// ❌ OCR disabled in Railway (no localhost python service)
const DOCTR_URL = process.env.DOCTR_URL || "http://localhost:8000/ocr";
const upload = (0, multer_1.default)({
    storage: multer_1.default.memoryStorage(),
    limits: { fileSize: 12 * 1024 * 1024 },
});
/* ---------------- IMAGE PREPROCESS ---------------- */
async function preprocessImage(buffer) {
    return await (0, sharp_1.default)(buffer)
        .rotate()
        .resize({ width: 2400 })
        .grayscale()
        .normalize()
        .sharpen({ sigma: 1.4 })
        .toBuffer();
}
/* ---------------- OCR DISABLED ---------------- */
async function runDocTrOCR(buffers) {
    console.log("⚠️ OCR route called but disabled in production");
    throw new Error("OCR disabled in Railway deploy — use Paste Text mode");
}
/* ---------------- TEXT CLEANER ---------------- */
function cleanOCRText(text) {
    return text
        .replace(/[^\x00-\x7F]/g, " ")
        .replace(/\s+/g, " ")
        .replace(/([A-Za-z])\1{3,}/g, "$1$1")
        .replace(/[^a-zA-Z0-9.,:;()%\- \n]/g, " ")
        .trim();
}
/* ---------------- SMART EXAM NOTES BUILDER ---------------- */
function generateNotesFromText(text) {
    const lines = text
        .split(/[\n\.]/)
        .map(l => l.trim())
        .filter(l => l.length > 20);
    let bullets = [];
    for (const line of lines) {
        const lower = line.toLowerCase();
        if (lower.includes(" is ") ||
            lower.includes(" are ") ||
            lower.includes(" defined as") ||
            lower.includes(" refers to")) {
            bullets.push(`• Definition: ${line}`);
        }
        else if (/\d/.test(line)) {
            bullets.push(`• ${line}`);
        }
        else if (line.length < 140) {
            bullets.push(`• ${line}`);
        }
    }
    bullets = bullets.slice(0, 60);
    const title = bullets[0]?.replace(/^•\s*/, "").slice(0, 80) ||
        "Study Notes";
    return {
        title,
        content: `## ${title}\n\n${bullets.join("\n")}`,
    };
}
/* ---------------- ROUTES ---------------- */
async function registerRoutes(app) {
    /* ---------- TEXT → NOTES (PRIMARY MODE) ---------- */
    app.post("/api/generate-notes-from-text", async (req, res) => {
        try {
            const { text } = req.body;
            if (!text || typeof text !== "string") {
                return res.status(400).json({ error: "No text provided" });
            }
            console.log("📝 Text notes request received");
            const cleaned = cleanOCRText(text);
            const notes = generateNotesFromText(cleaned);
            res.json(notes);
        }
        catch (err) {
            console.error("TEXT MODE FAIL:", err);
            res.status(500).json({ error: "Failed to generate notes" });
        }
    });
    /* ---------- IMAGE OCR ROUTE (DISABLED SAFE RESPONSE) ---------- */
    app.post("/api/generate-notes", upload.array("images", 25), async (req, res) => {
        console.log("⚠️ Image OCR endpoint hit — blocked in Railway deploy");
        return res.status(503).json({
            error: "Image OCR temporarily disabled. Use Paste Text mode.",
        });
    });
    return (0, node_http_1.createServer)(app);
}
