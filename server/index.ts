import express from "express";
import type { Request, Response, NextFunction } from "express";
import { registerRoutes } from "./routes";
import * as fs from "fs";
import * as path from "path";

const app = express();
const log = console.log;

declare module "http" {
  interface IncomingMessage {
    rawBody: unknown;
  }
}

/* ---------------- CORS ---------------- */

function setupCors(app: express.Application) {
  app.use((req, res, next) => {
    const allowedOrigins = new Set<string>();

    if (process.env.REPLIT_DEV_DOMAIN) {
      allowedOrigins.add(`https://${process.env.REPLIT_DEV_DOMAIN}`);
    }

    if (process.env.REPLIT_DOMAINS) {
      process.env.REPLIT_DOMAINS.split(",").forEach((d) => {
        allowedOrigins.add(`https://${d.trim()}`);
      });
    }

    const origin = req.header("origin");

    const isLocalhost =
      origin?.startsWith("http://localhost:") ||
      origin?.startsWith("http://127.0.0.1:");

    if (origin && (allowedOrigins.has(origin) || isLocalhost)) {
      res.header("Access-Control-Allow-Origin", origin);
      res.header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS");
      res.header("Access-Control-Allow-Headers", "Content-Type, Authorization");
      res.header("Access-Control-Allow-Credentials", "true");
    }

    if (req.method === "OPTIONS") {
      return res.sendStatus(200);
    }

    next();
  });
}

/* ---------------- BODY PARSING ---------------- */

function setupBodyParsing(app: express.Application) {
  app.use(
    express.json({
      limit: "25mb",
      verify: (req, _res, buf) => {
        (req as any).rawBody = buf;
      },
    }),
  );

  app.use(express.urlencoded({ extended: false, limit: "25mb" }));
}

/* ---------------- LOGGING ---------------- */

function setupRequestLogging(app: express.Application) {
  app.use((req, res, next) => {
    const start = Date.now();
    const pathName = req.path;
    let capturedJsonResponse: unknown;

    const originalJson = res.json;
    res.json = function (body, ...args) {
      capturedJsonResponse = body;
      return originalJson.apply(res, [body, ...args]);
    };

    res.on("finish", () => {
      if (!pathName.startsWith("/api")) return;

      const duration = Date.now() - start;

      let line = `${req.method} ${pathName} ${res.statusCode} in ${duration}ms`;

      if (capturedJsonResponse) {
        line += ` :: ${JSON.stringify(capturedJsonResponse)}`;
      }

      if (line.length > 140) {
        line = line.slice(0, 139) + "…";
      }

      log(line);
    });

    next();
  });
}

/* ---------------- EXPO STATIC + LANDING ---------------- */

function getAppName(): string {
  try {
    const appJson = JSON.parse(
      fs.readFileSync(path.resolve(process.cwd(), "app.json"), "utf-8"),
    );
    return appJson.expo?.name || "App Landing Page";
  } catch {
    return "App Landing Page";
  }
}

function serveExpoManifest(platform: string, res: Response) {
  const manifestPath = path.resolve(
    process.cwd(),
    "static-build",
    platform,
    "manifest.json",
  );

  if (!fs.existsSync(manifestPath)) {
    return res.status(404).json({
      error: `Manifest not found for platform: ${platform}`,
    });
  }

  res.setHeader("expo-protocol-version", "1");
  res.setHeader("expo-sfv-version", "0");
  res.setHeader("content-type", "application/json");
  res.send(fs.readFileSync(manifestPath, "utf-8"));
}

function serveLandingPage(
  req: Request,
  res: Response,
  template: string,
  appName: string,
) {
  const protocol = req.header("x-forwarded-proto") || req.protocol;
  const host = req.header("x-forwarded-host") || req.get("host");

  const baseUrl = `${protocol}://${host}`;

  const html = template
    .replace(/BASE_URL_PLACEHOLDER/g, baseUrl)
    .replace(/EXPS_URL_PLACEHOLDER/g, host || "")
    .replace(/APP_NAME_PLACEHOLDER/g, appName);

  res.setHeader("Content-Type", "text/html; charset=utf-8");
  res.status(200).send(html);
}

function configureExpoAndLanding(app: express.Application) {
  const templatePath = path.join(
    __dirname,
    "../templates/landing-page.html",
  );

  let template = "<h1>API Running</h1>";

  if (fs.existsSync(templatePath)) {
    template = fs.readFileSync(templatePath, "utf-8");
  } else {
    log("⚠️ landing-page.html missing — using fallback");
  }

  const appName = getAppName();

  app.use((req, res, next) => {
    if (req.path.startsWith("/api")) return next();

    if (req.path === "/" || req.path === "/manifest") {
      const platform = req.header("expo-platform");

      if (platform === "ios" || platform === "android") {
        return serveExpoManifest(platform, res);
      }

      if (req.path === "/") {
        return serveLandingPage(req, res, template, appName);
      }
    }

    next();
  });

  app.use("/assets", express.static(path.resolve(process.cwd(), "assets")));
  app.use(express.static(path.resolve(process.cwd(), "static-build")));

  log("Serving static Expo files with dynamic manifest routing");
}

/* ---------------- ERROR HANDLER ---------------- */

function setupErrorHandler(app: express.Application) {
  app.use((err: any, _req: Request, res: Response, next: NextFunction) => {
    const status = err.status || err.statusCode || 500;

    console.error("❌ Internal Error:", err);

    if (res.headersSent) return next(err);

    res.status(status).json({
      message: err.message || "Internal Server Error",
    });
  });
}

/* ---------------- BOOT ---------------- */

(async () => {
  setupCors(app);
  setupBodyParsing(app);
  setupRequestLogging(app);
  configureExpoAndLanding(app);

  const server = await registerRoutes(app);

  setupErrorHandler(app);

  const PORT = parseInt(process.env.PORT || "8080", 10);

  server.listen(PORT, "0.0.0.0", () => {
    console.log(`✅ Server is live on port ${PORT}`);
  });
})();
