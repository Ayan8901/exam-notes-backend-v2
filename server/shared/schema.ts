import { pgTable, text, varchar } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: varchar("id", { length: 191 }).primaryKey(),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
});

// Simplified schema with explicit Zod types
export const insertUserSchema = createInsertSchema(users, {
  username: z.string(),
  password: z.string(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = z.infer<typeof insertUserSchema>;