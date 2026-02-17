"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const routes_1 = require("./routes");
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
const app = (0, express_1.default)();
const log = console.log;
/* ---------------- CORS ---------------- */
function setupCors(app) {
    app.use((req, res, next) => {
        const origins = new Set();
        if (process.env.REPLIT_DEV_DOMAIN) {
            origins.add(`https://${process.env.REPLIT_DEV_DOMAIN}`);
        }
        if (process.env.REPLIT_DOMAINS) {
            process.env.REPLIT_DOMAINS.split(",").forEach((d) => {
                origins.add(`https://${d.trim()}`);
            });
        }
        const origin = req.header("origin");
        const isLocalhost = origin?.startsWith("http://localhost:") ||
            origin?.startsWith("http://127.0.0.1:");
        if (origin && (origins.has(origin) || isLocalhost)) {
            res.header("Access-Control-Allow-Origin", origin);
            res.header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
            res.header("Access-Control-Allow-Headers", "Content-Type");
            res.header("Access-Control-Allow-Credentials", "true");
        }
        if (req.method === "OPTIONS") {
            return res.sendStatus(200);
        }
        next();
    });
}
/* ---------------- BODY PARSING ---------------- */
function setupBodyParsing(app) {
    app.use(express_1.default.json({
        limit: "20mb",
        verify: (req, _res, buf) => {
            req.rawBody = buf;
        },
    }));
    app.use(express_1.default.urlencoded({ extended: false, limit: "20mb" }));
}
/* ---------------- LOGGING ---------------- */
function setupRequestLogging(app) {
    app.use((req, res, next) => {
        const start = Date.now();
        const pathName = req.path;
        let capturedJsonResponse;
        const originalResJson = res.json;
        res.json = function (bodyJson, ...args) {
            capturedJsonResponse = bodyJson;
            return originalResJson.apply(res, [bodyJson, ...args]);
        };
        res.on("finish", () => {
            if (!pathName.startsWith("/api"))
                return;
            const duration = Date.now() - start;
            let logLine = `${req.method} ${pathName} ${res.statusCode} in ${duration}ms`;
            if (capturedJsonResponse) {
                logLine += ` :: ${JSON.stringify(capturedJsonResponse)}`;
            }
            if (logLine.length > 120) {
                logLine = logLine.slice(0, 119) + "…";
            }
            log(logLine);
        });
        next();
    });
}
/* ---------------- EXPO LANDING (FIXED PATH) ---------------- */
function getAppName() {
    try {
        const appJsonPath = path.resolve(process.cwd(), "app.json");
        const appJsonContent = fs.readFileSync(appJsonPath, "utf-8");
        const appJson = JSON.parse(appJsonContent);
        return appJson.expo?.name || "App Landing Page";
    }
    catch {
        return "App Landing Page";
    }
}
function serveExpoManifest(platform, res) {
    const manifestPath = path.resolve(process.cwd(), "static-build", platform, "manifest.json");
    if (!fs.existsSync(manifestPath)) {
        return res
            .status(404)
            .json({ error: `Manifest not found for platform: ${platform}` });
    }
    res.setHeader("expo-protocol-version", "1");
    res.setHeader("expo-sfv-version", "0");
    res.setHeader("content-type", "application/json");
    res.send(fs.readFileSync(manifestPath, "utf-8"));
}
function serveLandingPage(req, res, landingTemplate, appName) {
    const protocol = req.header("x-forwarded-proto") || req.protocol || "https";
    const host = req.header("x-forwarded-host") || req.get("host");
    const baseUrl = `${protocol}://${host}`;
    const expsUrl = host || "";
    const html = landingTemplate
        .replace(/BASE_URL_PLACEHOLDER/g, baseUrl)
        .replace(/EXPS_URL_PLACEHOLDER/g, expsUrl)
        .replace(/APP_NAME_PLACEHOLDER/g, appName);
    res.setHeader("Content-Type", "text/html; charset=utf-8");
    res.status(200).send(html);
}
function configureExpoAndLanding(app) {
    // ✅ FIXED — no double "server"
    const templatePath = path.join(__dirname, "../templates/landing-page.html");
    let landingTemplate = "<h1>API Running</h1>";
    if (fs.existsSync(templatePath)) {
        landingTemplate = fs.readFileSync(templatePath, "utf-8");
    }
    else {
        log("⚠️ landing-page.html not found — using fallback page");
    }
    const appName = getAppName();
    app.use((req, res, next) => {
        if (req.path.startsWith("/api"))
            return next();
        if (req.path === "/" || req.path === "/manifest") {
            const platform = req.header("expo-platform");
            if (platform === "ios" || platform === "android") {
                return serveExpoManifest(platform, res);
            }
            if (req.path === "/") {
                return serveLandingPage(req, res, landingTemplate, appName);
            }
        }
        next();
    });
    app.use("/assets", express_1.default.static(path.resolve(process.cwd(), "assets")));
    app.use(express_1.default.static(path.resolve(process.cwd(), "static-build")));
    log("Serving static Expo files with dynamic manifest routing");
}
/* ---------------- ERROR HANDLER ---------------- */
function setupErrorHandler(app) {
    app.use((err, _req, res, next) => {
        const error = err;
        const status = error.status || error.statusCode || 500;
        console.error("Internal Server Error:", err);
        if (res.headersSent)
            return next(err);
        res.status(status).json({ message: error.message || "Internal Server Error" });
    });
}
/* ---------------- BOOT ---------------- */
(async () => {
    setupCors(app);
    setupBodyParsing(app);
    setupRequestLogging(app);
    configureExpoAndLanding(app);
    const server = await (0, routes_1.registerRoutes)(app);
    setupErrorHandler(app);
    const PORT = process.env.PORT ? parseInt(process.env.PORT, 10) : 5000;
    server.listen(PORT, "0.0.0.0", () => {
        console.log(`✅ Server is live on port ${PORT}`);
    });
})();
