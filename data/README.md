# Study dataset (external)

Drop external study materials here. The agent (`AGENTS.md`) is configured to
look in `data/savill/` for John Savill's AZ-305 video transcripts.

## When Valentina shares her 2.3 GB OneDrive dataset

1. Download it locally (do **not** commit — see `.gitignore`).
2. Unzip into `data/savill/` so the structure looks like:

   ```text
   data/
     savill/
       <transcripts, notes, PDFs, etc>
   ```

3. No agent reconfiguration needed — `AGENTS.md` already references the path.

## Verifying the agent can see it

```bash
copilot
# Then ask: "list the files you can see under data/savill"
```

## Study plans

Store study plans in `data/study-plans/`.

Recommended naming pattern:

- `study-plan-YYYY-MM-DD-to-YYYY-MM-DD.md` for sprint plans
- `study-plan-YYYY-MM-DD.md` for single-day plans

Versioning convention:

1. Keep plans in Git.
2. Treat dated files as immutable snapshots; do not overwrite old plans.
3. Create a new dated file for major revisions (new exam date, post-mock reprioritization).
4. Add a short change note near the top of the new plan (what changed and why).
