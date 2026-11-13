# Which tool to use

| Job | Preferred | Fallback |
|---|---|---|
| Find where to edit, read many files | agent `Explore` | Grep/Glob, then Read each part |
| One known file | Read just the relevant part | — |
| Library docs | WebFetch the official docs, exact version | The installed library's source |
| Check the UI (`ui: False`) | Playwright MCP if installed | Manual description + ask the human for screenshots |
| Run tests | `cd ../.. && bench --site miyano run-tests --module "$(echo {file} | sed 's#/#.#g; s#\.py$##')"` via Bash | `cd ../.. && bench --site miyano run-tests --app erp_ai` |
| PRs, issues | `gh` via Bash | Print the content for the human to do it |
| Diagrams | Mermaid in Markdown | Table |
| Team status | `/team:status` | Read `docs/team/features/<ID>/` |

Preferred tool unavailable → use the fallback and write one line in the journal.
