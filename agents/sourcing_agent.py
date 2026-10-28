import argparse
import asyncio
import string
from dataclasses import dataclass, field
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKError, HookMatcher, ResultMessage, query
from a_Configs.sources_config import SourcesConfig

"""Sourcing agent: checks one manual source for new data and pulls it into z_Data following the source's runbook."""

MODEL = "claude-sonnet-5-5"
EFFORT = "medium"
MAX_TURNS = 50
MAX_BUDGET_USD = 0.10

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = REPO_ROOT / "agents" / "prompts" / "sourcing_agent.md"
RUNBOOK_DIR = REPO_ROOT / "a_Configs" / "runbooks"
READABLE_DIRS = [REPO_ROOT / "a_Configs", REPO_ROOT / "z_Data"]
TOOLS = ["Read", "Glob", "Grep", "WebFetch", "Write", "Edit", "Bash"]

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "source_key": {"type": "string"},
        "status": {"type": "string", "enum": ["new_data", "no_new_data", "escalate", "error"]},
        "files": {"type": "array", "items": {"type": "string"}},
        "periods": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
        "escalation_reason": {"type": ["string", "null"]},
    },
    "required": ["source_key", "status", "files", "periods", "notes", "escalation_reason"],
    "additionalProperties": False,
}


@dataclass
class SourcingResult:
    source_key: str
    status: str
    files: list[str] = field(default_factory=list)
    periods: list[str] = field(default_factory=list)
    notes: str = ""
    escalation_reason: str | None = None
    cost_usd: float | None = None

    @property
    def new_data_found(self):
        return self.status == "new_data"


def get_source(source_key):
    """Look up a manual source and check it has what the agent needs."""
    source = SourcesConfig.SOURCES.get(source_key)
    if source is None:
        raise ValueError(f"Unknown source: {source_key}")
    if not source.get("runbook"):
        raise ValueError(f"{source_key} has no runbook, so it isn't a manual source")
    if not source.get("data_dir"):
        raise ValueError(f"{source_key} has no data_dir, so the agent has nowhere to write")
    return source


def build_prompt(source_key, special_instructions=None):
    """Fill in the sourcing agent prompt template for one source."""
    source = get_source(source_key)
    runbook_path = RUNBOOK_DIR / source["runbook"]
    template = string.Template(PROMPT_PATH.read_text())
    return template.substitute(
        source_key=source_key,
        source_name=source["name"],
        source_url=source["url"],
        last_updated=source["last_updated"],
        repo_root=REPO_ROOT,
        data_dir=REPO_ROOT / source["data_dir"],
        runbook_path=runbook_path.relative_to(REPO_ROOT),
        runbook=runbook_path.read_text(),
        special_instructions=special_instructions or "None",
    )


def _deny(reason):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def _path_guard(allowed_dirs, path_keys, cwd, action):
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


def _build_options(data_dir):
    write_guard = _path_guard([data_dir], ["file_path"], data_dir, "write")
    read_guard = _path_guard(READABLE_DIRS, ["file_path", "path"], data_dir, "read")
    return ClaudeAgentOptions(
        model=MODEL,
        effort=EFFORT,
        cwd=data_dir,
        tools=TOOLS,
        allowed_tools=TOOLS,
        permission_mode="dontAsk",
        setting_sources=[],
        # Keep the claude.ai account's connectors (Slack, Trello, ...) out of the agent; their tool definitions were ~85% of the input tokens
        env={"ENABLE_CLAUDEAI_MCP_SERVERS": "false"},
        max_turns=MAX_TURNS,
        max_budget_usd=MAX_BUDGET_USD,
        output_format={"type": "json_schema", "schema": RESULT_SCHEMA},
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Write|Edit", hooks=[write_guard]),
                HookMatcher(matcher="Read|Glob|Grep", hooks=[read_guard]),
            ]
        },
        # Bash runs sandboxed: it can only write in cwd (data_dir) and can only read a_Configs and z_Data in the repo
        sandbox={
            "enabled": True,
            "autoAllowBashIfSandboxed": True,
            "allowUnsandboxedCommands": False,
            "failIfUnavailable": True,
            "filesystem": {
                "denyRead": [str(REPO_ROOT)],
                "allowRead": [str(d) for d in READABLE_DIRS],
            },
        },
    )


def _to_result(source_key, message):
    """Map the agent's final ResultMessage to a SourcingResult."""
    if message is None:
        return SourcingResult(source_key, "error", notes="Agent ended without a result")
    cost = message.total_cost_usd
    if message.subtype != "success" or message.is_error:
        reason = message.stop_reason if message.stop_reason == "refusal" else message.subtype
        notes = f"Agent run failed ({reason}): {'; '.join(message.errors or []) or message.result or ''}"
        return SourcingResult(source_key, "error", notes=notes, cost_usd=cost)
    output = message.structured_output
    if not output:
        return SourcingResult(source_key, "error", notes=f"No structured output. Final text: {message.result}", cost_usd=cost)
    return SourcingResult(**output, cost_usd=cost)


async def run_sourcing_agent(source_key, special_instructions=None):
    """Run the sourcing agent for one source and return a SourcingResult.

    special_instructions carries feedback from the Configuration/Testing agent on a retry."""
    data_dir = REPO_ROOT / get_source(source_key)["data_dir"]
    prompt = build_prompt(source_key, special_instructions)
    final = None
    try:
        async for message in query(prompt=prompt, options=_build_options(data_dir)):
            if isinstance(message, ResultMessage):
                final = message
    except ClaudeSDKError as e:
        # query() raises after yielding an error result, so prefer that result if we got one
        if final is None:
            return SourcingResult(source_key, "error", notes=f"Agent SDK error: {e}")
    return _to_result(source_key, final)


def run_sourcing_agent_sync(source_key, special_instructions=None):
    return asyncio.run(run_sourcing_agent(source_key, special_instructions))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check one manual source for new data and pull it.")
    parser.add_argument("source", help="Source key from SourcesConfig.SOURCES, e.g. maine_legislature")
    parser.add_argument("--instructions", help="Feedback from the Configuration/Testing agent for a retry")
    args = parser.parse_args()

    result = run_sourcing_agent_sync(args.source, args.instructions)
    print(f"Source:   {result.source_key}")
    print(f"Status:   {result.status}")
    print(f"Files:    {', '.join(result.files) or '-'}")
    print(f"Periods:  {', '.join(result.periods) or '-'}")
    print(f"Cost:     ${result.cost_usd or 0:.4f}")
    print(f"Notes:    {result.notes}")
    if result.status == "escalate":
        print("\n*** ESCALATION: the source has changed and needs a human ***")
        print(result.escalation_reason)
