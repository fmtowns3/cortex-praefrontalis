#!/usr/bin/env python3
"""cortex-praefrontalis: compaction や再起動のあとに、直前の会話を原文のまま渡す。

Claude Code の SessionStart hook から呼ばれる。stdin で受け取った hook 入力から
transcript (JSONL) を探し、ユーザーとアシスタントの「会話の文」だけを新しい側から
最大 CHARS 字ぶん取り出して stdout に書く。stdout はそのまま Claude の文脈に入る。

- 要約しない。LLM も中間ファイルも使わない。
- ツールの呼び出しと結果、thinking、コマンドの記録、通知は入れない。
- hook の出力は 1 本 10,000 字までなので、それを超えないように切る。
- 失敗しても何も出さずに終わる（セッションの起動を邪魔しない）。

環境変数:
  CORTEX_PRAEFRONTALIS_CHARS  渡す量（字）。既定 10000、上限 10000。
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

HOOK_CAP = 10_000          # Claude Code が hook の出力 1 本に許す字数
FIRST_READ = 4 << 20       # 末尾から最初に読むバイト数。足りなければ倍々で広げる

NOISE_PREFIXES = (
    "<local-command-",
    "<command-name>",
    "<command-message>",
    "<command-args>",
    "<task-notification>",
    "<bash-input>",
    "<bash-stdout>",
    "<bash-stderr>",
)
SYSTEM_REMINDER = re.compile(r"<system-reminder>.*?</system-reminder>", re.S)
PASTE_TAG = re.compile(r"</?pasted_content[^>]*>")


def budget() -> int:
    try:
        n = int(os.environ.get("CORTEX_PRAEFRONTALIS_CHARS", HOOK_CAP))
    except ValueError:
        n = HOOK_CAP
    return max(1_000, min(n, HOOK_CAP))


def clean(text: str) -> str:
    text = SYSTEM_REMINDER.sub("", text)
    text = PASTE_TAG.sub("", text)
    return text.strip()


def stamp(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone()
        return t.strftime("%m-%d %H:%M")
    except ValueError:
        return ""


def text_of(content: object) -> str:
    """文字列か content ブロックの配列から、text ブロックだけをつなぐ（画像などは捨てる）。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content
                         if isinstance(b, dict) and b.get("type") == "text")
    return ""


def message_of(row: dict) -> tuple[str, str, str] | None:
    """transcript の 1 行から (話者, 時刻, 本文) を取り出す。会話でなければ None。"""
    if row.get("isSidechain") or row.get("isMeta") or row.get("isCompactSummary"):
        return None
    kind = row.get("type")

    if kind == "attachment":
        # 作業中に割り込んだユーザーの発言
        att = row.get("attachment") or {}
        if att.get("type") == "queued_command" and att.get("humanTurn"):
            text = clean(text_of(att.get("prompt")))
            return ("user", stamp(row.get("timestamp")), text) if text else None
        return None

    if kind not in ("user", "assistant"):
        return None
    msg = row.get("message") or {}
    if kind == "assistant" and msg.get("model") == "<synthetic>":
        return None
    content = msg.get("content")

    if isinstance(content, list) and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
        return None
    text = clean(text_of(content))
    if not text or text.startswith(NOISE_PREFIXES):
        return None
    when = stamp(row.get("timestamp")) if kind == "user" else ""
    return kind, when, text


def tail_messages(path: Path, want: int) -> list[tuple[str, str, str]]:
    """ファイルの末尾から読み、会話が want 字以上たまるまで読む範囲を広げる。"""
    size = path.stat().st_size
    span = FIRST_READ
    while True:
        start = max(0, size - span)
        with path.open("rb") as fh:
            fh.seek(start)
            raw = fh.read()
        lines = raw.split(b"\n")
        if start > 0:
            lines = lines[1:]          # 途中から始まった行は捨てる
        out = []
        for line in lines:
            if not line.strip():
                continue
            try:
                m = message_of(json.loads(line))
            except (ValueError, AttributeError):
                continue
            if m:
                out.append(m)
        if start == 0 or sum(len(t) for _, _, t in out) >= want:
            return out
        span *= 2


def pick_transcript(data: dict) -> Path | None:
    """compact なら今のセッション、新規セッションや /clear なら直前のセッションを読む。"""
    cur = Path(data.get("transcript_path") or "")
    if data.get("source") == "compact":
        return cur if cur.is_file() else None
    folder = cur.parent if str(cur) else None
    if not folder or not folder.is_dir():
        return None
    others = [p for p in folder.glob("*.jsonl") if p.resolve() != cur.resolve()]
    others.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return others[0] if others else None


def render(source: str, path: Path, msgs: list[tuple[str, str, str]], limit: int) -> str:
    head = (f'<cortex-praefrontalis source="{source}" transcript="{path.name}">\n'
            "直前までの会話の原文（要約ではない。新しい側から入る分だけ。"
            "ツールの出力・thinking は含まない）。\n\n")
    foot = "\n</cortex-praefrontalis>"
    room = limit - len(head) - len(foot)

    picked: list[str] = []
    for who, when, text in reversed(msgs):
        label = f"[{who}{' ' + when if when else ''}]\n"
        block = label + text + "\n\n"
        if len(block) <= room:
            picked.append(block)
            room -= len(block)
            continue
        # 入りきらない一番古い発言は、後ろ側だけ残す
        keep = room - len(label) - len("…\n\n")
        if keep > 200:
            picked.append(label + "…" + text[-keep:] + "\n\n")
        break
    if not picked:
        return ""
    return head + "".join(reversed(picked)).rstrip() + "\n" + foot


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    source = data.get("source", "")
    if source in ("resume", "fork"):
        return 0                       # 文脈がそのまま戻るので要らない
    path = pick_transcript(data)
    if path is None:
        return 0
    limit = budget()
    msgs = tail_messages(path, limit)
    text = render(source, path, msgs, limit)
    if text:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # 起動を止めない
        print(f"cortex-praefrontalis: {exc}", file=sys.stderr)
        sys.exit(0)
