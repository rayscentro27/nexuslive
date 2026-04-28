#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import Counter, defaultdict

ROOT = Path.home() / '.hermes' / 'agents'


def parse_ts(value: str):
    if not value:
        return None
    try:
        if value.endswith('Z'):
            value = value[:-1] + '+00:00'
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except Exception:
        return None


def short(text: str, limit: int = 160):
    text = ' '.join((text or '').split())
    if len(text) <= limit:
        return text
    return text[: limit - 1] + '…'


def extract_text_parts(content):
    out = []
    if not isinstance(content, list):
        return out
    for item in content:
        if isinstance(item, dict) and item.get('type') == 'text':
            txt = item.get('text')
            if txt:
                out.append(txt)
    return out


def extract_tool_calls(content):
    names = []
    if not isinstance(content, list):
        return names
    for item in content:
        if isinstance(item, dict) and item.get('type') == 'toolCall':
            name = item.get('name')
            if name:
                names.append(name)
    return names


def session_summary(path: Path, since: datetime):
    session_id = path.stem
    agent_id = path.parts[-3] if len(path.parts) >= 3 else 'unknown'
    session_ts = None
    first_event = None
    last_event = None
    user_msgs = []
    assistant_msgs = []
    tool_calls = Counter()
    total_events = 0
    active_events = 0

    try:
        with path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                total_events += 1
                ts = parse_ts(obj.get('timestamp'))
                if obj.get('type') == 'session' and ts and session_ts is None:
                    session_ts = ts
                if not ts or ts < since:
                    continue
                active_events += 1
                if first_event is None or ts < first_event:
                    first_event = ts
                if last_event is None or ts > last_event:
                    last_event = ts

                if obj.get('type') != 'message':
                    continue
                msg = obj.get('message') or {}
                role = msg.get('role')
                content = msg.get('content') or []
                texts = extract_text_parts(content)
                if role == 'user':
                    user_msgs.extend(texts)
                elif role == 'assistant':
                    assistant_msgs.extend(texts)
                for name in extract_tool_calls(content):
                    tool_calls[name] += 1
    except FileNotFoundError:
        return None

    if active_events == 0:
        return None

    return {
        'agent_id': agent_id,
        'session_id': session_id,
        'path': str(path),
        'session_ts': session_ts,
        'first_event': first_event,
        'last_event': last_event,
        'active_events': active_events,
        'total_events': total_events,
        'user_count': len(user_msgs),
        'assistant_count': len(assistant_msgs),
        'tool_calls': tool_calls,
        'first_user': short(user_msgs[0]) if user_msgs else '',
        'last_assistant': short(assistant_msgs[-1]) if assistant_msgs else '',
    }


def collect(hours: int):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    summaries = []
    if not ROOT.exists():
        return since, summaries
    for path in ROOT.glob('*/sessions/*.jsonl'):
        summary = session_summary(path, since)
        if summary:
            summaries.append(summary)
    summaries.sort(key=lambda x: x['last_event'] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return since, summaries


def render(hours: int, since: datetime, summaries):
    total_sessions = len(summaries)
    per_agent = Counter(s['agent_id'] for s in summaries)
    tool_totals = Counter()
    for s in summaries:
        tool_totals.update(s['tool_calls'])

    lines = []
    lines.append(f'AI activity report — last {hours} hours')
    lines.append(f'Window start (UTC): {since.isoformat()}')
    lines.append(f'Active sessions: {total_sessions}')
    if per_agent:
        lines.append('Agents seen: ' + ', '.join(f'{k} ({v})' for k, v in per_agent.most_common()))
    if tool_totals:
        lines.append('Top tools: ' + ', '.join(f'{k} x{v}' for k, v in tool_totals.most_common(10)))
    lines.append('')

    if not summaries:
        lines.append('No session activity found in this window.')
        lines.append('')
        lines.append('Note: this report reads Hermes session logs. Background shell processes are not fully audited unless we add explicit logging for them.')
        return '\n'.join(lines)

    for i, s in enumerate(summaries, 1):
        start = s['first_event'].astimezone().strftime('%Y-%m-%d %H:%M:%S %Z') if s['first_event'] else 'unknown'
        end = s['last_event'].astimezone().strftime('%Y-%m-%d %H:%M:%S %Z') if s['last_event'] else 'unknown'
        lines.append(f'{i}. Agent: {s["agent_id"]} | Session: {s["session_id"]}')
        lines.append(f'   Active: {start} → {end}')
        lines.append(f'   Message text count: user {s["user_count"]}, assistant {s["assistant_count"]}; events in window: {s["active_events"]}')
        if s['tool_calls']:
            lines.append('   Tools: ' + ', '.join(f'{k} x{v}' for k, v in s['tool_calls'].most_common(8)))
        if s['first_user']:
            lines.append(f'   Started with: {s["first_user"]}')
        if s['last_assistant']:
            lines.append(f'   Ended with: {s["last_assistant"]}')
        lines.append('')

    lines.append('Limitations:')
    lines.append('- This summarizes Hermes conversation/session logs.')
    lines.append('- It does not automatically know the intent or business outcome of every background shell process.')
    lines.append('- If you want true employee/process accountability, the next step is adding a small audit log for spawned jobs and periodic report generation.')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Summarize Hermes AI activity from session logs.')
    parser.add_argument('--hours', type=int, default=24)
    parser.add_argument('--output', type=str, default='')
    args = parser.parse_args()

    since, summaries = collect(args.hours)
    report = render(args.hours, since, summaries)
    print(report)
    if args.output:
        out = Path(args.output).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(report + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
