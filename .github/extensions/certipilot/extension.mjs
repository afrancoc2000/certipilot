import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createCanvas, joinSession } from "@github/copilot-sdk/extension";
import { createStudyService } from "./study.mjs";
import { startServer } from "./server.mjs";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const servers = new Map();
let session;
const study = createStudyService(root, {
    send: (options) => session.send(options),
    getMode: () => session.rpc.mode.get(),
});
const selectionSchema = {
    type: "object",
    properties: { examId: { type: "string", pattern: "^[a-z0-9]+(?:-[a-z0-9]+)*$" } },
    additionalProperties: false,
};

session = await joinSession({
    canvases: [
        createCanvas({
            id: "certipilot",
            displayName: "Certipilot",
            description: "Seleccionar examen, consultar planes locales y estudiar con el agente de esta sesión.",
            inputSchema: selectionSchema,
            actions: [
                {
                    name: "refresh",
                    description: "Consultar exámenes y disponibilidad local sin exponer soluciones ni calificaciones.",
                    inputSchema: selectionSchema,
                    handler: (ctx) => study.snapshot(ctx.input?.examId),
                },
            ],
            open: async (ctx) => {
                if (ctx.input?.examId) await study.snapshot(ctx.input.examId);
                let entry = servers.get(ctx.instanceId);
                if (!entry) {
                    entry = await startServer(study, ctx.input?.examId);
                    servers.set(ctx.instanceId, entry);
                }
                return { title: "Certipilot · Tu espacio de estudio", url: entry.url };
            },
            onClose: async (ctx) => {
                const entry = servers.get(ctx.instanceId);
                if (entry) {
                    servers.delete(ctx.instanceId);
                    await entry.close();
                }
            },
        }),
    ],
});
