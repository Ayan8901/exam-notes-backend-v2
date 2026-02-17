"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerRoutes = registerRoutes;
const node_http_1 = require("node:http");
const multer_1 = __importDefault(require("multer"));
const client_1 = require("./replit_integrations/image/client");
const chat_1 = require("./replit_integrations/chat");
const image_1 = require("./replit_integrations/image");
const audio_1 = require("./replit_integrations/audio");
const upload = (0, multer_1.default)({
    storage: multer_1.default.memoryStorage(),
    limits: { fileSize: 10 * 1024 * 1024 },
});
const NOTE_GENERATION_PROMPT = `You are an expert exam revision specialist. Create ULTRA-CONCISE, high-yield revision notes.

STRICT FORMAT (Use ## for headers, - for bullets):
## [Main Topic]
- Definition: [1-sentence max]
- Key Formula: [Equation + Units]
- Step: [Actionable step]
- Fact: [Key keyword/date/value]

HIERARCHY RULES:
- Main Topic (##)
  - Sub-topic (### if needed, else bullet)
    - Key fact (bullet)

STRICT CONTENT RULES:
- MAX 1 LINE per bullet point.
- MAX 8-10 words per bullet point.
- BULLETS ONLY. No paragraphs.
- NO filler words (e.g., "The," "Additionally," "In conclusion").
- FOCUS on: Definitions, Formulas, Steps, Keywords.
- EXAM-ORIENTED: Only include what is likely to be tested.
- TITLE: Concise title (max 4 words).`;
async function registerRoutes(app) {
    // Register integration routes
    (0, chat_1.registerChatRoutes)(app);
    (0, image_1.registerImageRoutes)(app);
    (0, audio_1.registerAudioRoutes)(app);
    app.post("/api/generate-notes", upload.array("images", 25), async (req, res) => {
        try {
            const files = req.files;
            if (!files || files.length === 0) {
                return res.status(400).json({ error: "No images provided" });
            }
            const imageContents = files.map((file) => ({
                type: "image_url",
                image_url: {
                    url: `data:${file.mimetype};base64,${file.buffer.toString("base64")}`,
                },
            }));
            const response = await client_1.openai.chat.completions.create({
                model: "gpt-4o",
                messages: [
                    {
                        role: "system",
                        content: NOTE_GENERATION_PROMPT,
                    },
                    {
                        role: "user",
                        content: [
                            {
                                type: "text",
                                text: "Extract text from these textbook/study material images and convert into exam-focused revision notes:",
                            },
                            ...imageContents,
                        ],
                    },
                ],
                max_tokens: 4000,
            });
            const content = response.choices[0]?.message?.content || "";
            const titleMatch = content.match(/^#\s+(.+)$/m) || content.match(/^##\s+(.+)$/m);
            let title = "Study Notes";
            let noteContent = content;
            if (titleMatch) {
                title = titleMatch[1].trim();
                noteContent = content.replace(titleMatch[0], "").trim();
            }
            else {
                const firstLine = content.split("\n")[0];
                if (firstLine && !firstLine.startsWith("-") && !firstLine.startsWith("#")) {
                    title = firstLine.substring(0, 60);
                    noteContent = content.substring(firstLine.length).trim();
                }
            }
            res.json({
                title,
                content: noteContent,
            });
        }
        catch (error) {
            console.error("Error generating notes from images:", error);
            res.status(500).json({ error: "Failed to generate notes" });
        }
    });
    app.post("/api/generate-notes-from-text", async (req, res) => {
        try {
            const { text } = req.body;
            if (!text || typeof text !== "string") {
                return res.status(400).json({ error: "No text provided" });
            }
            const response = await client_1.openai.chat.completions.create({
                model: "gpt-4o",
                messages: [
                    {
                        role: "system",
                        content: NOTE_GENERATION_PROMPT,
                    },
                    {
                        role: "user",
                        content: `Convert the following study material into exam-focused revision notes:\n\n${text}`,
                    },
                ],
                max_tokens: 4000,
            });
            const content = response.choices[0]?.message?.content || "";
            const titleMatch = content.match(/^#\s+(.+)$/m) || content.match(/^##\s+(.+)$/m);
            let title = "Study Notes";
            let noteContent = content;
            if (titleMatch) {
                title = titleMatch[1].trim();
                noteContent = content.replace(titleMatch[0], "").trim();
            }
            else {
                const firstLine = content.split("\n")[0];
                if (firstLine && !firstLine.startsWith("-") && !firstLine.startsWith("#")) {
                    title = firstLine.substring(0, 60);
                    noteContent = content.substring(firstLine.length).trim();
                }
            }
            res.json({
                title,
                content: noteContent,
            });
        }
        catch (error) {
            console.error("Error generating notes from text:", error);
            res.status(500).json({ error: "Failed to generate notes" });
        }
    });
    const httpServer = (0, node_http_1.createServer)(app);
    return httpServer;
}
