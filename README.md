# Certification Study Agent

One workspace for studying multiple Microsoft and GitHub certifications with
GitHub Copilot. Each exam is isolated under `exams/<exam-id>/`; shared agent
instructions resolve the active exam before reading material or tracking
progress.

## Exams

| Exam | Status |
| --- | --- |
| [GH-300: GitHub Copilot](exams/gh-300/exam.md) | Active; official syllabus and starter plan ready |
| [AZ-104: Microsoft Azure Administrator](exams/az-104/exam.md) | Scaffolded; partial material |
| [AZ-305: Azure Infrastructure Solutions](exams/az-305/exam.md) | Existing study material |
| [GH-600: Developing in Agentic AI Systems](exams/gh-600/exam.md) | Scaffolded; official syllabus, no material yet |
| [AI-500: Designing and Implementing Multi-Agent AI Solutions](exams/ai-500/exam.md) | Scaffolded; official syllabus (beta exam), no material yet |

## Start studying

Open Copilot Chat in this workspace and name the exam:

```text
Study GH-300 now
Quiz me on GH-300 prompt engineering
Run today's GH-300 plan
Build an AZ-104 sprint plan for October 10 with 90 minutes per day
```

The agent reads `exams/<active-exam>/exam.md` first, then uses that exam's
material, progress, and study plan. It falls back to authoritative first-party
documentation when local material is missing.

## Add another certification

Follow [exams/README.md](exams/README.md). The minimum exam package is:

```text
exams/<exam-id>/
├── exam.md
├── assets/
│   ├── progress.md
│   └── study-plans/README.md
└── material/README.md
```

Personal progress, plans, and graded results remain local through `.gitignore`;
study material and exam configuration can be shared.
