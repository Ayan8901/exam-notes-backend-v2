"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.insertMessageSchema = exports.insertConversationSchema = exports.messages = exports.conversations = void 0;
const pg_core_1 = require("drizzle-orm/pg-core");
const drizzle_zod_1 = require("drizzle-zod");
const zod_1 = require("zod");
const drizzle_orm_1 = require("drizzle-orm");
exports.conversations = (0, pg_core_1.pgTable)("conversations", {
    id: (0, pg_core_1.serial)("id").primaryKey(),
    title: (0, pg_core_1.text)("title").notNull(),
    createdAt: (0, pg_core_1.timestamp)("created_at").default((0, drizzle_orm_1.sql) `CURRENT_TIMESTAMP`).notNull(),
});
exports.messages = (0, pg_core_1.pgTable)("messages", {
    id: (0, pg_core_1.serial)("id").primaryKey(),
    conversationId: (0, pg_core_1.integer)("conversation_id").notNull(),
    role: (0, pg_core_1.text)("role").notNull(),
    content: (0, pg_core_1.text)("content").notNull(),
    createdAt: (0, pg_core_1.timestamp)("created_at").default((0, drizzle_orm_1.sql) `CURRENT_TIMESTAMP`).notNull(),
});
// Simplified schemas without the problematic type inference
exports.insertConversationSchema = (0, drizzle_zod_1.createInsertSchema)(exports.conversations, {
    title: zod_1.z.string(),
});
exports.insertMessageSchema = (0, drizzle_zod_1.createInsertSchema)(exports.messages, {
    conversationId: zod_1.z.number(),
    role: zod_1.z.string(),
    content: zod_1.z.string(),
});
