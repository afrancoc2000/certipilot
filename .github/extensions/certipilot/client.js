const $ = (id) => document.getElementById(id);
let selectedExam = "";
let selectedPlan = "";
let snapshot;
let sending = false;
let loading = false;
let revision = 0;

function notice(message, error = false) {
    $("notice").textContent = message;
    $("notice").dataset.error = String(error);
}

async function api(path, options) {
    const response = await fetch(path, options);
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "No se pudo completar la solicitud.");
    return data;
}

function controls() {
    document.querySelectorAll("[data-study]").forEach((button) => {
        button.disabled = sending || loading || !snapshot?.selected;
    });
    $("resume").disabled ||= !snapshot?.selected?.checkpoint;
    $("follow").disabled ||= !selectedPlan;
    $("tutor").disabled ||= !$("topic").value.trim();
    document.querySelectorAll(".plan-item").forEach((button) => {
        button.disabled = sending || loading;
    });
    $("exam").disabled = sending || loading;
    $("refresh").disabled = sending || loading;
}

async function preview(plan) {
    if (loading || sending) return;
    const currentRevision = revision;
    loading = true;
    controls();
    try {
        const data = await api(`api/plan?${new URLSearchParams({ exam: selectedExam, path: plan.path })}`);
        if (revision !== currentRevision) return;
        selectedPlan = data.path;
        $("plan-content").textContent = data.content;
        $("plan-path").textContent = `${data.scope === "master" ? "Plan transversal · " : ""}${data.path}`;
        $("plan-preview").hidden = false;
        document.querySelectorAll(".plan-item").forEach((button) => {
            button.setAttribute("aria-pressed", String(button.dataset.path === selectedPlan));
        });
    } catch (error) {
        notice(error.message, true);
    } finally {
        loading = false;
        controls();
    }
}

async function refresh() {
    revision++;
    loading = true;
    controls();
    try {
        snapshot = await api(`api/state?${new URLSearchParams({ exam: selectedExam })}`);
        $("exam").replaceChildren(new Option("Selecciona un examen…", ""));
        for (const exam of snapshot.exams) {
            const label = exam.title.toLowerCase().startsWith(exam.id)
                ? exam.title : `${exam.id.toUpperCase()} · ${exam.title}`;
            $("exam").add(new Option(label, exam.id));
        }
        selectedExam = snapshot.selected?.id || "";
        $("exam").value = selectedExam;
        $("workspace").hidden = !snapshot.selected;
        selectedPlan = "";
        $("plan-preview").hidden = true;
        $("topic").value = "";
        $("plans").replaceChildren();
        if (!snapshot.selected) {
            $("exam-note").textContent = snapshot.exams.length
                ? "No inferimos un examen activo a partir de archivos sin validar. Elige cuál estudiar."
                : "No hay exámenes con exam.md en este repositorio.";
            return;
        }
        const exam = snapshot.selected;
        $("exam-note").textContent = `${exam.id.toUpperCase()} seleccionado para este canvas. Al estudiar, se enviará como elección explícita al agente.`;
        $("checkpoint-note").textContent = exam.checkpoint
            ? "Hay un checkpoint local. El agente lo validará antes de retomar el hilo."
            : "No hay una sesión guardada en este checkout. Puedes empezar con una pregunta o un concepto.";
        $("evidence-note").textContent = exam.progress || exam.evidence
            ? "Hay archivos personales de seguimiento. Su existencia no acredita puntuación ni cobertura; aquí no se muestran respuestas."
            : "Sin progreso ni evidencia local disponibles. No significa 0 %: todavía no hay datos que mostrar.";
        if (!exam.plans.length) {
            const empty = document.createElement("p");
            empty.className = "muted";
            empty.textContent = "No hay planes locales en este checkout. Los planes personales ignorados no viajan con un clon o un worktree nuevo.";
            $("plans").append(empty);
        }
        for (const plan of exam.plans) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "plan-item";
            button.dataset.path = plan.path;
            button.setAttribute("aria-pressed", "false");
            const name = document.createElement("span");
            name.textContent = plan.title;
            const meta = document.createElement("small");
            meta.textContent = plan.scope === "master" ? "Transversal · relación con el examen sin validar" : "Plan del examen · fechas sin validar";
            button.append(name, meta);
            button.addEventListener("click", () => preview(plan));
            $("plans").append(button);
        }
    } catch (error) {
        snapshot = null;
        $("workspace").hidden = true;
        notice(error.message, true);
    } finally {
        loading = false;
        controls();
    }
}

async function study(action) {
    if (sending || loading) return;
    sending = true;
    controls();
    notice("Enviando la solicitud al agente de esta sesión…");
    try {
        const result = await api("api/study", {
            method: "POST",
            headers: { "Content-Type": "application/json", "X-Certipilot-Request": "study" },
            body: JSON.stringify({ examId: selectedExam, action, planPath: selectedPlan, topic: $("topic").value }),
        });
        notice(result.message);
    } catch (error) {
        notice(error.message, true);
    } finally {
        sending = false;
        controls();
    }
}

$("exam").addEventListener("change", () => {
    selectedExam = $("exam").value;
    notice("");
    refresh();
});
$("refresh").addEventListener("click", () => { notice(""); refresh(); });
$("topic").addEventListener("input", controls);
for (const action of ["resume", "planner", "follow", "quiz", "tutor"]) {
    $(action).addEventListener("click", () => study(action));
}
await refresh();
