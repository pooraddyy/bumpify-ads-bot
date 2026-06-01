import http from "http";
import express, { type Express, type Request, type Response } from "express";
import cors from "cors";
import pinoHttp from "pino-http";
import router from "./routes";
import { logger } from "./lib/logger";

const app: Express = express();

app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return { id: req.id, method: req.method, url: req.url?.split("?")[0] };
      },
      res(res) {
        return { statusCode: res.statusCode };
      },
    },
  }),
);
app.use(cors());

app.use("/api", express.json(), express.urlencoded({ extended: true }), router);

function makeProxy(prefix: string) {
  return (req: Request, res: Response) => {
    const fullPath = prefix + req.url;
    const options = {
      hostname: "localhost",
      port: 3000,
      path: fullPath,
      method: req.method,
      headers: { ...req.headers, host: "localhost:3000" },
    };
    const proxyReq = http.request(options, (proxyRes) => {
      res.writeHead(proxyRes.statusCode ?? 502, proxyRes.headers);
      proxyRes.pipe(res, { end: true });
    });
    proxyReq.on("error", () => {
      if (!res.headersSent) res.status(502).json({ error: "Bot service unavailable" });
    });
    req.pipe(proxyReq, { end: true });
  };
}

app.use("/webhook", makeProxy("/webhook"));
app.use("/panel", makeProxy("/panel"));
app.use("/static", makeProxy("/static"));

export default app;
