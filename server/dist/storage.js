"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.storage = exports.MemStorage = void 0;
const crypto_1 = require("crypto");
class MemStorage {
    users;
    constructor() {
        this.users = new Map();
    }
    async getUser(id) {
        return this.users.get(id);
    }
    async getUserByUsername(username) {
        return Array.from(this.users.values()).find((user) => user.username === username);
    }
    async createUser(insertUser) {
        const id = (0, crypto_1.randomUUID)();
        // FIXED: Create the user object with all required fields
        const user = {
            id,
            username: insertUser.username,
            password: insertUser.password,
        };
        this.users.set(id, user);
        return user;
    }
}
exports.MemStorage = MemStorage;
exports.storage = new MemStorage();
