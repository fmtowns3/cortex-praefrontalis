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

- **Secrets are not masked.** Claude Code itself stores transcripts in plain text.
  This plugin carries that conversation over as it is, so a key you typed into the
  conversation goes back to the same model unchanged. Nothing new is written to disk.
- **"Previous session" is the newest other transcript in the project folder.** With
  two sessions open in the same project at once, it may pick the other one.
- The transcript format is not a public API. A Claude Code update can change it.

## License

MIT. See [LICENSE](LICENSE).

* * *

# 日本語

Claude Code の作業記憶です。

圧縮や `/clear`、新しいセッションのあと、Claude は直前まで何を話していたかを忘れます。
この plugin は、**直前の会話の最後の 1 万字**を、**原文のまま**、`SessionStart` hook で
Claude に渡します。

- **要約しません。** あなたの言葉と Claude の返事を、書かれたとおりに渡します。
- **LLM なし、中間ファイルなし、MCP サーバーなし。** Claude Code がすでに残している
  transcript を、Python 1 ファイルが読むだけです。
- **会話だけ。** ツールの呼び出しと出力、thinking、コマンドの記録、通知は入れません。
  そのぶん、1 万字で長い時間をさかのぼれます。

## なぜ

圧縮を助ける道具の多くは、より良い要約を書こうとします。これは要約そのものをしません。
*重要さ*ではなく*種類*で選びます。会話はそのまま残し、それ以外は全部落とします。
何が大事だったかを誰も判定しないので、判定を誤ることもありません。

作る前に測ったこと（Claude Code 2.1.287、Windows 11）：

- Claude Code は全セッションを `~/.claude/projects/<project>/<session>.jsonl` に書きます。
  圧縮は境界と要約を**追記する**だけで、それより前のメッセージは残ります。
- 圧縮をまたいで Claude Code 自身が原文で残すのは、直前のアシスタントの 1 ターンだけです
  （手元のセッションでは、会話にして 68〜1,229 字）。
- 会話は transcript のごく一部です。22 MB のファイルのうち会話は 35,000 字で、残りは
  ツールの出力でした。
- hook が文脈に足せるのは**最大 1 万字**です（`10,001` 字になると 2,000 字のプレビューに
  切られます）。これがこの plugin の上限値です。

## インストール

```bash
claude plugin marketplace add fmtowns3/cortex-praefrontalis
claude plugin install cortex-praefrontalis@cortex-praefrontalis
```

インストールせずに試す場合：

```bash
claude --plugin-dir /path/to/cortex-praefrontalis
```

Python 3.8 以降が `python3` または `python` として `PATH` にあること。追加パッケージは
要りません。

## 動作

| セッションの始まり方 | Claude に渡るもの |
|---|---|
| 圧縮（手動・自動） | 同じセッションの会話の末尾 |
| `/clear`、または新しいセッション | 同じプロジェクトの、直前のセッションの末尾 |
| `--resume`、`--continue`、fork | 何も渡さない（文脈がすでにあるため） |

本文は `<cortex-praefrontalis>` で包まれ、`[user MM-DD HH:MM]` と `[assistant]` の見出しが
付きます。新しい発言ほど後ろです。入りきらない一番古い発言は前から切られ、`…` が付きます。

渡す量を減らすには `CORTEX_PRAEFRONTALIS_CHARS` を設定します（1,000〜10,000、既定 10,000）。

## 知っておくこと

- **秘密はマスクされません。** Claude Code の仕様として、transcript は平文で保存されています。
  この plugin はその会話をそのまま引き継ぐので、会話に貼ったキーも同じモデルへそのまま
  戻ります。新しくディスクに書くものはありません。
- **「直前のセッション」とは、プロジェクトのフォルダにある、自分以外で一番新しい transcript
  です。** 同じプロジェクトで 2 つのセッションを同時に開いていると、もう片方を拾うことが
  あります。
- transcript の形式は公開 API ではありません。Claude Code の更新で変わる可能性があります。

## ライセンス

MIT。[LICENSE](LICENSE) を参照してください。
