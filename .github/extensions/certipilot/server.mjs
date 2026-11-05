import { createServer } from "node:http";
import { randomBytes } from "node:crypto";
import { readFile } from "node:fs/promises";
import { StudyError } from "./study.mjs";

const assets = new Map([
    ["", ["index.html", "text/html; charset=utf-8"]],
    ["client.js", ["client.js", "text/javascript; charset=utf-8"]],
    ["style.css", ["style.css", "text/css; charset=utf-8"]],
]);

async function body(request) {
    if (request.headers["content-type"] !== "application/json") {
        throw new StudyError("Se requiere application/json.", 415);
    }
    let size = 0;
    const chunks = [];
    for await (const chunk of request) {
        size += chunk.length;
        if (size > 16_384) throw new StudyError("Solicitud demasiado grande.", 413);
        chunks.push(chunk);
    }
    try {
        return JSON.parse(Buffer.concat(chunks).toString("utf8"));
    } catch {
        throw new StudyError("JSON inválido.");
    }
}

export async function startServer(study, initialExam) {
    const token = randomBytes(24).toString("hex");
    const prefix = `/${token}/`;
    let origin;
    const server = createServer(async (req, res) => {
        res.setHeader("Cache-Control", "no-store");
        res.setHeader("X-Content-Type-Options", "nosniff");
        res.setHeader("Referrer-Policy", "no-referrer");
        res.setHeader("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'");
        function json(status, data) {
            res.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
            res.end(JSON.stringify(data));
        }
        try {
            if (req.headers.host !== new URL(origin).host) throw new StudyError("Host no permitido.", 403);
            const url = new URL(req.url, origin);
            if (!url.pathname.startsWith(prefix)) throw new StudyError("Ruta no disponible.", 404);
            const route = url.pathname.slice(prefix.length);
            if (req.method === "GET" && assets.has(route)) {
                const [file, type] = assets.get(route);
                const content = await readFile(new URL(file, import.meta.url));
                res.writeHead(200, { "Content-Type": type });
                res.end(content);
            } else if (req.method === "GET" && route === "api/state") {
                json(200, await study.snapshot(url.searchParams.get("exam") || initialExam));
            } else if (req.method === "GET" && route === "api/plan") {
                json(200, await study.plan(url.searchParams.get("exam"), url.searchParams.get("path")));
            } else if (req.method === "POST" && route === "api/study") {
                if (req.headers.origin !== origin || req.headers["x-certipilot-request"] !== "study") {
                    throw new StudyError("Origen de solicitud no permitido.", 403);
                }
                json(202, await study.dispatch(await body(req)));
            } else {
                throw new StudyError("Ruta o método no disponible.", 404);
            }
        } catch (error) {
            if (!(error instanceof StudyError)) console.error("[certipilot]", error);
            json(error instanceof StudyError ? error.status : 500, {
                error: error instanceof StudyError ? error.message : "No se pudo completar la operación. Revisa el log de la extensión.",
            });
        }
    });
    await new Promise((resolve, reject) => {
        server.once("error", reject);
        server.listen(0, "127.0.0.1", resolve);
    });
    origin = `http://127.0.0.1:${server.address().port}`;
    let closing;
    return {
        url: `${origin}${prefix}`,
        close: () => closing ??= new Promise((resolve, reject) => {
            server.close((error) => error ? reject(error) : resolve());
            server.closeIdleConnections();
        }),
    };
}
