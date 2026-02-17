"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerChatRoutes = registerChatRoutes;
const openai_1 = __importDefault(require("openai"));
const storage_1 = require("./storage");
const openai = new openai_1.default({
    apiKey: process.env.AI_INTEGRATIONS_OPENAI_API_KEY,
    baseURL: process.env.AI_INTEGRATIONS_OPENAI_BASE_URL,
});
function registerChatRoutes(app) {
    // Get all conversations
    app.get("/api/conversations", async (req, res) => {
        try {
            const conversations = await storage_1.chatStorage.getAllConversations();
            res.json(conversations);
        }
        catch (error) {
            console.error("Error fetching conversations:", error);
            res.status(500).json({ error: "Failed to fetch conversations" });
        }
    });
    // Get single conversation with messages
    app.get("/api/conversations/:id", async (req, res) => {
        try {
            // FIXED: Safely extract 'id' from params which can be string | string[]
            const rawId = req.params.id;
            const idString = Array.isArray(rawId) ? rawId[0] : rawId;
            const id = parseInt(idString);
            const conversation = await storage_1.chatStorage.getConversation(id);
            if (!conversation) {
                return res.status(404).json({ error: "Conversation not found" });
            }
            const messages = await storage_1.chatStorage.getMessagesByConversation(id);
            res.json({ ...conversation, messages });
        }
        catch (error) {
            console.error("Error fetching conversation:", error);
            res.status(500).json({ error: "Failed to fetch conversation" });
        }
    });
    // Create new conversation
    app.post("/api/conversations", async (req, res) => {
        try {
            const { title } = req.body;
            const conversation = await storage_1.chatStorage.createConversation(title || "New Chat");
            res.status(201).json(conversation);
        }
        catch (error) {
            console.error("Error creating conversation:", error);
            res.status(500).json({ error: "Failed to create conversation" });
        }
    });
    // Delete conversation
    app.delete("/api/conversations/:id", async (req, res) => {
        try {
            // FIXED: Safely extract 'id' from params which can be string | string[]
            const rawId = req.params.id;
            const idString = Array.isArray(rawId) ? rawId[0] : rawId;
            const id = parseInt(idString);
            await storage_1.chatStorage.deleteConversation(id);
            res.status(204).send();
        }
        catch (error) {
            console.error("Error deleting conversation:", error);
            res.status(500).json({ error: "Failed to delete conversation" });
        }
    });
    // Send message and get AI response (streaming)
    app.post("/api/conversations/:id/messages", async (req, res) => {
        try {
            // FIXED: Safely extract 'id' from params which can be string | string[]
            const rawId = req.params.id;
            const idString = Array.isArray(rawId) ? rawId[0] : rawId;
            const conversationId = parseInt(idString);
            const { content } = req.body;
            // Save user message
            await storage_1.chatStorage.createMessage(conversationId, "user", content);
            // Get conversation history for context
            const messages = await storage_1.chatStorage.getMessagesByConversation(conversationId);
            const chatMessages = messages.map((m) => ({
                role: m.role,
                content: m.content,
            }));
            // Set up SSE
            res.setHeader("Content-Type", "text/event-stream");
            res.setHeader("Cache-Control", "no-cache");
            res.setHeader("Connection", "keep-alive");
            // Stream response from OpenAI
            const stream = await openai.chat.completions.create({
                model: "gpt-5.1",
                messages: chatMessages,
                stream: true,
                max_completion_tokens: 2048,
            });
            let fullResponse = "";
            for await (const chunk of stream) {
                const content = chunk.choices[0]?.delta?.content || "";
                if (content) {
                    fullResponse += content;
                    res.write(`data: ${JSON.stringify({ content })}\n\n`);
                }
            }
            // Save assistant message
            await storage_1.chatStorage.createMessage(conversationId, "assistant", fullResponse);
            res.write(`data: ${JSON.stringify({ done: true })}\n\n`);
            res.end();
        }
        catch (error) {
            console.error("Error sending message:", error);
            // Check if headers already sent (SSE streaming started)
            if (res.headersSent) {
                res.write(`data: ${JSON.stringify({ error: "Failed to send message" })}\n\n`);
                res.end();
            }
            else {
                res.status(500).json({ error: "Failed to send message" });
            }
        }
    });
}
