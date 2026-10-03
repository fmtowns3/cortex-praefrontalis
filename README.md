# cortex-praefrontalis

Working memory for Claude Code.

After compaction, `/clear`, or a new session, Claude forgets what you were just
talking about. This plugin hands the latest **10,000 characters of the conversation**
back to Claude, **verbatim**, through a `SessionStart` hook.

- **No summaries.** Your words and Claude's replies, as they were written.
- **No LLM, no extra files, no MCP server.** One Python file reads the transcript that
  Claude Code already keeps.
- **Conversation only.** Tool calls, tool output, thinking, command logs and
  notifications are left out, so 10,000 characters go a long way.

## Why

Most compaction helpers write a better summary. This one doesn't summarize at all.
It picks by *kind*, not by *importance*: the conversation is kept as is, everything
else is dropped. Nothing has to decide what mattered, so nothing can get it wrong.

What we measured before writing it (Claude Code 2.1.287, Windows 11):

- Claude Code writes every session to `~/.claude/projects/<project>/<session>.jsonl`.
  Compaction only **appends** a boundary and a summary; the earlier messages stay.
- Across compaction, Claude Code itself keeps only the last assistant turn verbatim
  (68 to 1,229 characters of conversation in our sessions).
- Conversation is a tiny share of a transcript: 35,000 characters of conversation in a
  22 MB file, the rest is tool output.
- A hook may add at most **10,000 characters** to the context (`10,001` gets cut to a
  2,000-character preview). That is this plugin's budget.

## Install

```bash
claude plugin marketplace add fmtowns3/cortex-praefrontalis
claude plugin install cortex-praefrontalis@cortex-praefrontalis
```

Or try it without installing:

```bash
claude --plugin-dir /path/to/cortex-praefrontalis
```

Requires Python 3.8 or later on `PATH` as `python3` or `python`. No packages.

## What it does

| How the session started | What Claude gets |
|---|---|
| Compaction (manual or auto) | The end of the same session's conversation |
| `/clear`, or a new session | The end of the previous session in the same project |
| `--resume`, `--continue`, fork | Nothing (the context is already there) |

The text arrives wrapped in `<cortex-praefrontalis>` with `[user MM-DD HH:MM]` and
`[assistant]` labels, newest message last. The oldest message that doesn't fit is cut
from the front and marked with `…`.

Set `CORTEX_PRAEFRONTALIS_CHARS` to send less (1,000 to 10,000; default 10,000).

## Things to know

- **Secrets are not masked.** If you typed a key into the conversation, it is already
  in the transcript in plain text, and this plugin sends it back to the same model.
  Nothing new is written to disk.
- **"Previous session" is the newest other transcript in the project folder.** With
  two sessions open in the same project at once, it may pick the other one.
- The transcript format is not a public API. A Claude Code update can change it.

## 日本語

Claude Code の作業記憶。圧縮や `/clear`、新しいセッションのあとに、**直前の会話の原文を
最大 1 万字**、SessionStart hook で渡します。要約しない・LLM なし・中間ファイルなし・
本体は Python 1 ファイル。会話（ユーザーとアシスタントの文）だけを選び、ツールの出力や
thinking は入れません。

## License

MIT. See [LICENSE](LICENSE).
