"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.chatStorage = void 0;
const db_1 = require("../../db");
const chat_1 = require("../../shared/models/chat"); // <-- FIXED: Changed from "../../shared/schema"
const drizzle_orm_1 = require("drizzle-orm");
exports.chatStorage = {
    async getConversation(id) {
        const [conversation] = await db_1.db.select().from(chat_1.conversations).where((0, drizzle_orm_1.eq)(chat_1.conversations.id, id));
        return conversation;
    },
    async getAllConversations() {
        return db_1.db.select().from(chat_1.conversations).orderBy((0, drizzle_orm_1.desc)(chat_1.conversations.createdAt));
    },
    async createConversation(title) {
        const [conversation] = await db_1.db.insert(chat_1.conversations).values({ title }).returning();
        return conversation;
    },
    async deleteConversation(id) {
        await db_1.db.delete(chat_1.messages).where((0, drizzle_orm_1.eq)(chat_1.messages.conversationId, id));
        await db_1.db.delete(chat_1.conversations).where((0, drizzle_orm_1.eq)(chat_1.conversations.id, id));
    },
    async getMessagesByConversation(conversationId) {
        return db_1.db.select().from(chat_1.messages).where((0, drizzle_orm_1.eq)(chat_1.messages.conversationId, conversationId)).orderBy(chat_1.messages.createdAt);
    },
    async createMessage(conversationId, role, content) {
        const [message] = await db_1.db.insert(chat_1.messages).values({ conversationId, role, content }).returning();
        return message;
    },
};
