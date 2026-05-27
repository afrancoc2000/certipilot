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
opencode
# Then ask: "list the files you can see under data/savill"
```
