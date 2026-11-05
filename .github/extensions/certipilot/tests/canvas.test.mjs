import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, mkdir, writeFile, readFile, rm, symlink } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";
import { createStudyService } from "../study.mjs";
import { startServer } from "../server.mjs";

async function fixture(t) {
    const root = await mkdtemp(join(tmpdir(), "certipilot-canvas-"));
    t.after(() => rm(root, { recursive: true, force: true }));
    async function put(path, content) {
        await mkdir(join(root, path, ".."), { recursive: true });
        await writeFile(join(root, path), content);
    }
    await put("exams/one/exam.md", "# ONE: Synthetic exam");
    await put("exams/two/exam.md", "# TWO: Another exam");
    await put("exams/incomplete/blueprint.json", "{}");
    const sent = [];
    const service = createStudyService(root, {
        send: async (message) => { sent.push(message); return "synthetic-message"; },
        getMode: async () => "interactive",
    });
    return { root, put, sent, service };
}

test("fresh checkout requires selection; missing personal files are unknown, not zero scores", async (t) => {
    const { service, root } = await fixture(t);
    assert.deepEqual(await service.snapshot(), {
        exams: [{ id: "one", title: "ONE: Synthetic exam" }, { id: "two", title: "TWO: Another exam" }],
        selected: null,
    });
    assert.deepEqual((await service.snapshot("one")).selected, {
        id: "one", title: "ONE: Synthetic exam", plans: [], checkpoint: false, progress: false, evidence: false,
    });
    await assert.rejects(readFile(join(root, "exams/one/assets/coverage.json")), { code: "ENOENT" });
    await assert.rejects(service.snapshot("../two"), /Selecciona/);
});

test("real plan preview is confined to selected exam; private solutions never enter snapshots", async (t) => {
    const { put, service } = await fixture(t);
    const planPath = join("exams", "one", "assets", "study-plans", "dated.md");
    await put(planPath, "# My real fixture plan\n\n2026-11-05: Synthetic task");
    await put("exams/one/assets/study-plans/README.md", "# Shared template, not a plan");
    await put("exams/one/assets/session.json", '{"private_key":"SECRET_CANARY"}');
    await put("exams/one/assets/progress.md", "PERSONAL_SCORE_CANARY");
    await put("exams/one/assets/coverage.json", "EVIDENCE_CANARY");
    await put("exams/two/assets/study-plans/other.md", "# Other exam");
    await put("assets/master.md", "# Cross-exam plan");
    const state = await service.snapshot("one");
    assert.equal(state.selected.plans.length, 2);
    assert.equal(state.selected.checkpoint, true);
    assert.equal(state.selected.progress, true);
    assert.equal(state.selected.evidence, true);
    assert.doesNotMatch(JSON.stringify(state), /CANARY|private_key|Other exam/);
    assert.equal((await service.plan("one", planPath)).content, "# My real fixture plan\n\n2026-11-05: Synthetic task");
    await assert.rejects(service.plan("two", planPath), /no está disponible/);
    await assert.rejects(service.plan("one", "exams/one/assets/session.json"), /no está disponible/);
    await assert.rejects(service.plan("one", "../anything"), /no está disponible/);
});

test("all five study actions send exam-scoped instructions, not answers; no private state changes", async (t) => {
    const { put, service, sent, root } = await fixture(t);
    const planPath = join("exams", "one", "assets", "study-plans", "dated.md");
    await put(planPath, "# Existing plan");
    await put("exams/one/assets/session.json", "DO_NOT_PARSE_OR_MUTATE_CHECKPOINT");
    for (const action of ["quiz", "tutor", "planner", "follow", "resume"]) {
        assert.equal((await service.dispatch({ examId: "one", action, topic: "Mechanism", planPath })).messageId, "synthetic-message");
    }
    assert.equal(sent.length, 5);
    for (const message of sent) {
        assert.equal(message.source, "system");
        assert.equal(message.mode, "immediate");
        assert.match(message.prompt, /AGENTS\.md y exams\/one\/exam\.md/);
        assert.match(message.prompt, /progress-tracking\.instructions\.md/);
        assert.match(message.prompt, /NO es una respuesta/);
        assert.match(message.prompt, /checkpoint/);
        assert.doesNotMatch(message.prompt, /exams\/two|DO_NOT_PARSE/);
    }
    assert.match(sent[1].prompt, /Mechanism/);
    assert.match(sent[2].prompt, /build-sprint-plan/);
    assert.match(sent[3].prompt, /follow-plan/);
    assert.equal(await readFile(join(root, "exams/one/assets/session.json"), "utf8"), "DO_NOT_PARSE_OR_MUTATE_CHECKPOINT");
});

test("invalid inputs, missing checkpoint, and missing plan never dispatch", async (t) => {
    const { service, sent } = await fixture(t);
    for (const input of [
        null, [], {}, { examId: "one", action: "wrong" }, { examId: "one", action: "constructor" },
        { examId: "one", action: "tutor", topic: " " },
        { examId: "one", action: "tutor", topic: "a".repeat(2001) },
        { examId: "one", action: "follow", planPath: "../x" },
        { examId: "one", action: "resume" },
    ]) await assert.rejects(service.dispatch(input));
    assert.equal(sent.length, 0);
    await service.dispatch({ examId: "one", action: "quiz" });
    assert.equal(sent.length, 1);
});

test("non-interactive mode and transport failures are explicit and retryable", async (t) => {
    const { root } = await fixture(t);
    let mode = "autopilot";
    let fail = true;
    let calls = 0;
    const service = createStudyService(root, {
        getMode: async () => mode,
        send: async () => { calls++; if (fail) throw new Error("transport unavailable"); return "ok"; },
    });
    await assert.rejects(service.dispatch({ examId: "one", action: "quiz" }), /Interactive/);
    assert.equal(calls, 0);
    mode = "interactive";
    await assert.rejects(service.dispatch({ examId: "one", action: "quiz" }), /transport unavailable/);
    fail = false;
    assert.equal((await service.dispatch({ examId: "one", action: "quiz" })).messageId, "ok");
});

test("simultaneous clicks cannot race during filesystem reads", async (t) => {
    const { root } = await fixture(t);
    const service = createStudyService(root, {
        getMode: async () => "interactive", send: async () => "ok",
    });
    const results = await Promise.allSettled([
        service.dispatch({ examId: "one", action: "quiz" }),
        service.dispatch({ examId: "one", action: "quiz" }),
    ]);
    assert.equal(results.filter((item) => item.status === "fulfilled").length, 1);
    assert.match(results.find((item) => item.status === "rejected").reason.message, /enviando/);
});

test("fresh process reads existing plans without persisting invented active exam", async (t) => {
    const { put, root, service } = await fixture(t);
    await put("exams/one/assets/study-plans/plan.md", "# Persisted synthetic plan");
    const moduleUrl = pathToFileURL(resolve(import.meta.dirname, "../study.mjs")).href;
    const script = `import {createStudyService} from ${JSON.stringify(moduleUrl)};
        const service=createStudyService(${JSON.stringify(root)}, {});
        process.stdout.write(JSON.stringify(await service.snapshot("one")));`;
    const restarted = spawnSync(process.execPath, ["--input-type=module", "-e", script], { encoding: "utf8" });
    assert.equal(restarted.status, 0, restarted.stderr);
    assert.deepEqual(JSON.parse(restarted.stdout), await service.snapshot("one"));
    assert.equal((await service.snapshot()).selected, null);
});

test("symlinked private directory outside the checkout is rejected", async (t) => {
    const { root, service } = await fixture(t);
    const external = await mkdtemp(join(tmpdir(), "certipilot-external-"));
    t.after(() => rm(external, { recursive: true, force: true }));
    await writeFile(join(external, "session.json"), "PRIVATE_CANARY");
    await symlink(external, join(root, "exams/one/assets"), process.platform === "win32" ? "junction" : "dir");
    await assert.rejects(service.snapshot("one"), /fuera de este repositorio/);
});

test("HTTP journey: assets, selection, plan, dispatch, rejection, close and fresh server", async (t) => {
    const { put, service, sent } = await fixture(t);
    const planPath = join("exams", "one", "assets", "study-plans", "plan.md");
    await put(planPath, "# Safe <script>alert('not HTML')</script>");
    await put("exams/one/assets/session.json", '{"private_key":"SECRET_HTTP_CANARY"}');
    const server = await startServer(service);
    t.after(() => server.close());
    const origin = new URL(server.url).origin;
    const request = (path, options) => fetch(new URL(path, server.url), options);
    for (const asset of ["", "client.js", "style.css"]) {
        const response = await request(asset);
        assert.equal(response.status, 200);
        assert.match(response.headers.get("cache-control"), /no-store/);
        assert.match(response.headers.get("content-security-policy"), /script-src 'self'/);
    }
    assert.equal((await (await request("api/state")).json()).selected, null);
    const state = await request("api/state?exam=one");
    assert.doesNotMatch(await state.text(), /SECRET_HTTP_CANARY/);
    const preview = await request(`api/plan?${new URLSearchParams({ exam: "one", path: planPath })}`);
    assert.equal((await preview.json()).content, "# Safe <script>alert('not HTML')</script>");
    const options = {
        method: "POST",
        headers: { Origin: origin, "Content-Type": "application/json", "X-Certipilot-Request": "study" },
        body: JSON.stringify({ examId: "one", action: "quiz" }),
    };
    assert.equal((await request("api/study", options)).status, 202);
    assert.equal(sent.length, 1);
    assert.equal((await request("api/study", { ...options, headers: { ...options.headers, Origin: "https://unrelated.invalid" } })).status, 403);
    assert.equal((await request("api/study", { ...options, body: "{" })).status, 400);
    assert.equal((await request("api/study", { ...options, headers: { ...options.headers, "Content-Type": "text/plain" } })).status, 415);
    assert.equal((await fetch(`${origin}/api/state`)).status, 404);
    assert.equal((await request("api/plan?exam=one&path=../session.json")).status, 404);
    await server.close();
    const restarted = await startServer(service, "one");
    try {
        assert.notEqual(restarted.url, server.url);
        const state = await (await fetch(new URL("api/state", restarted.url))).json();
        assert.equal(state.selected.id, "one");
        assert.equal(state.selected.plans.length, 1);
    } finally {
        await restarted.close();
    }
});
