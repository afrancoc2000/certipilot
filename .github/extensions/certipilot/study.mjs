import { readdir, readFile, realpath, stat } from "node:fs/promises";
import { isAbsolute, join, relative, sep } from "node:path";

export class StudyError extends Error {
    constructor(message, status = 400) {
        super(message);
        this.status = status;
    }
}

async function optional(operation) {
    try {
        return await operation();
    } catch (error) {
        if (error.code === "ENOENT") return null;
        throw error;
    }
}

function title(text, fallback) {
    return text.match(/^#\s+(.+)$/m)?.[1]?.trim() || fallback;
}

export function createStudyService(root, { send, getMode }) {
    async function local(path) {
        const base = await realpath(root);
        const resolved = await optional(() => realpath(join(base, path)));
        if (!resolved) return null;
        const rel = relative(base, resolved);
        if (rel === ".." || rel.startsWith(`..${sep}`) || isAbsolute(rel)) {
            throw new StudyError("Un archivo local apunta fuera de este repositorio.", 403);
        }
        return resolved;
    }

    async function text(path) {
        const file = await local(path);
        if (!file) return null;
        const info = await stat(file);
        if (!info.isFile() || info.size > 1_000_000) {
            throw new StudyError(`No se puede leer ${path}: archivo inválido o mayor de 1 MB.`);
        }
        return readFile(file, "utf8");
    }

    async function directories(path) {
        const dir = await local(path);
        if (!dir) return [];
        return readdir(dir, { withFileTypes: true });
    }

    async function catalog() {
        const entries = await directories("exams");
        const exams = [];
        for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
            if (!entry.isDirectory() || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(entry.name)) continue;
            const config = await text(join("exams", entry.name, "exam.md"));
            if (config === null) continue;
            exams.push({ id: entry.name, title: title(config, entry.name.toUpperCase()) });
        }
        return exams;
    }

    async function exam(examId) {
        const exams = await catalog();
        const selected = exams.find((item) => item.id === examId);
        if (!selected) throw new StudyError("Selecciona un examen disponible.");
        return selected;
    }

    async function plans(examId) {
        const result = [];
        for (const [directory, scope] of [
            [join("exams", examId, "assets", "study-plans"), "exam"],
            ["assets", "master"],
        ]) {
            for (const entry of await directories(directory)) {
                if (!entry.isFile() || !/\.md$/i.test(entry.name) || /^readme\.md$/i.test(entry.name)) continue;
                const path = join(directory, entry.name);
                const content = await text(path);
                if (content !== null) result.push({
                    path, title: title(content, entry.name), scope,
                });
            }
        }
        return result.sort((a, b) => a.path.localeCompare(b.path));
    }

    async function exists(path) {
        const file = await local(path);
        return file !== null && (await stat(file)).isFile();
    }

    async function snapshot(examId) {
        const exams = await catalog();
        if (!examId) return { exams, selected: null };
        const selected = await exam(examId);
        return {
            exams,
            selected: {
                ...selected,
                plans: await plans(examId),
                checkpoint: await exists(join("exams", examId, "assets", "session.json")),
                progress: await exists(join("exams", examId, "assets", "progress.md")),
                evidence: await exists(join("exams", examId, "assets", "coverage.json")),
            },
        };
    }

    async function plan(examId, path) {
        await exam(examId);
        const item = (await plans(examId)).find((candidate) => candidate.path === path);
        if (!item) throw new StudyError("El plan ya no está disponible. Actualiza la vista.", 404);
        const content = await text(item.path);
        if (content === null) throw new StudyError("El plan ya no está disponible.", 404);
        return { ...item, content };
    }

    let sending = false;
    async function dispatch(input) {
        if (!input || typeof input !== "object" || Array.isArray(input)) {
            throw new StudyError("La acción debe ser un objeto.");
        }
        const { examId, action, topic, planPath } = input;
        if (sending) throw new StudyError("Ya se está enviando una acción.", 409);
        sending = true;
        try {
            await exam(examId);
            const commands = {
                quiz: "Quiero practicar con una pregunta original de quiz.",
                tutor: "Quiero aprender este tema con tutor, mecanismos y un mapa mental:",
                planner: "Quiero crear un plan de estudio. Invoca build-sprint-plan y pregunta por los datos que falten.",
                follow: "Quiero seguir este plan. Invoca follow-plan con esta ruta explícita:",
                resume: "Quiero continuar mi sesión guardada, sin reconstruir respuestas ni cambiar el ítem pendiente.",
            };
            if (!Object.hasOwn(commands, action)) throw new StudyError("Acción de estudio no reconocida.");
            if (action === "tutor" && (typeof topic !== "string" || !topic.trim() || topic.length > 2000)) {
                throw new StudyError("Escribe un tema de hasta 2000 caracteres.");
            }
            if (action === "follow") await plan(examId, planPath);
            if (action === "resume" && !await exists(join("exams", examId, "assets", "session.json"))) {
                throw new StudyError("No hay un checkpoint local para este examen.", 409);
            }
            const mode = await getMode();
            if (mode !== "interactive") {
                throw new StudyError("Cambia esta conversación a modo Interactive con Shift+Tab antes de estudiar.", 409);
            }
            const detail = action === "tutor" ? `\nTema del usuario: ${JSON.stringify(topic.trim())}`
                : action === "follow" ? `\nRuta seleccionada: ${JSON.stringify(planPath)}` : "";
            const prompt = [
                `Acción solicitada desde el canvas de Certipilot. Examen explícito: ${examId.toUpperCase()}.`,
                "Esta acción inicia estudio, NO es una respuesta del alumno ni evidencia evaluable.",
                `Lee primero AGENTS.md y exams/${examId}/exam.md.`,
                "Carga .github/instructions/active-exam.instructions.md, sources-and-citations.instructions.md",
                "y progress-tracking.instructions.md, junto a sus especificaciones compartidas de evidencia y sesión.",
                `Usa solo exams/${examId}/ para material, progreso, cobertura y checkpoint.`,
                "Valida y reconcilia el checkpoint mediante el protocolo existente antes de comenzar otra actividad.",
                "No uses memoria de Copilot como sustituto del estado estructurado ni inventes progreso.",
                "Si faltan datos o los archivos son inválidos, explícalo y sigue el contrato de la skill.",
                "Los planes se comprueban por fecha; no ejecutes un plan vencido o de otro examen sin aclararlo.",
                "No modifiques planes sin confirmación. Usa los agentes quiz-agent, tutor-agent o study-planner-agent según corresponda.",
                "Explica en español; conserva el idioma de preguntas que establezca el contrato.",
                "Guarda lo requerido antes de presentar una sola pregunta; después espera una respuesta genuina.",
                commands[action] + detail,
            ].join("\n");
            const messageId = await send({ prompt, source: "system", mode: "immediate" });
            return { messageId, message: "Solicitud enviada. Continúa en el chat de esta sesión de Certipilot." };
        } finally {
            sending = false;
        }
    }

    return { snapshot, plan, dispatch };
}
