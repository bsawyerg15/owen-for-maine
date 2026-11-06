import re
from dataclasses import dataclass
from pathlib import Path

from claude_agent_sdk import ClaudeSDKError, ResultMessage, query
from a_Configs.sources_config import SourcesConfig

"""Helpers shared by the ingest agents."""

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_DIR = REPO_ROOT / "agents" / "prompts"
RUNBOOK_DIR = REPO_ROOT / "a_Configs" / "runbooks"

# Keep the claude.ai account's connectors (Slack, Trello, ...) out of the agents; their tool definitions were ~85% of the input tokens
AGENT_ENV = {"ENABLE_CLAUDEAI_MCP_SERVERS": "false"}


def get_source(source_key):
    """Look up a manual source and check it has what the agents need."""
    source = SourcesConfig.SOURCES.get(source_key)
    if source is None:
        raise ValueError(f"Unknown source: {source_key}")
    if not source.get("runbook"):
        raise ValueError(f"{source_key} has no runbook, so it isn't a manual source")
    if not source.get("data_dir"):
        raise ValueError(f"{source_key} has no data_dir, so the agent has nowhere to write")
    return source


def runbook_section(source, heading):
    """Return the runbook's title plus one '## ' section, e.g. 'Sourcing' or 'Configuration/Testing'."""
    text = (RUNBOOK_DIR / source["runbook"]).read_text()
    title, *sections = re.split(r'^(?=## )', text, flags=re.M)
    for section in sections:
        if section.splitlines()[0].strip() == f"## {heading}":
            return (title + section).strip() + "\n"
    raise ValueError(f"Runbook {source['runbook']} has no '## {heading}' section")


def _deny(reason):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def path_guard(allowed_dirs, path_keys, cwd, action):
    """Build a PreToolUse hook that denies tool calls whose path is outside allowed_dirs.

    A missing path means the tool runs in cwd. Relative paths resolve against cwd."""
    async def hook(input_data, tool_use_id, context):
        tool_input = input_data["tool_input"]
        raw = next((tool_input[k] for k in path_keys if tool_input.get(k)), None)
        path = (cwd / raw).resolve() if raw else cwd.resolve()
        if any(path.is_relative_to(d.resolve()) for d in allowed_dirs):
            return {}
        allowed = ", ".join(str(d) for d in allowed_dirs)
        return _deny(f"Can't {action} {path}: only allowed in {allowed}")
    return hook


@dataclass
class AgentRun:
    output: dict | None  # the structured output, when the run succeeded
    error: str | None  # why the run failed, when it didn't
    cost_usd: float | None


async def run_agent(prompt, options):
    """Run an agent to completion and return its structured output or the reason it failed."""
    final = None
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                final = message
    except ClaudeSDKError as e:
        # query() raises after yielding an error result, so prefer that result if we got one
        if final is None:
            return AgentRun(None, f"Agent SDK error: {e}", None)

    if final is None:
        return AgentRun(None, "Agent ended without a result", None)
    cost = final.total_cost_usd
    if final.subtype != "success" or final.is_error:
        reason = final.stop_reason if final.stop_reason == "refusal" else final.subtype
        return AgentRun(None, f"Agent run failed ({reason}): {'; '.join(final.errors or []) or final.result or ''}", cost)
    if not final.structured_output:
        return AgentRun(None, f"No structured output. Final text: {final.result}", cost)
    return AgentRun(final.structured_output, None, cost)
