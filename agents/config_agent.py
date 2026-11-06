import argparse
import asyncio
import json
import string
from dataclasses import asdict, dataclass, field

from claude_agent_sdk import ClaudeAgentOptions, HookMatcher
from agents.checks import format_command, pipeline_commands
from agents.common import AGENT_ENV, PROMPT_DIR, REPO_ROOT, RUNBOOK_DIR, get_source, path_guard, run_agent

"""Configuration/Testing agent: when the automated checks on a pull fail (or a source has none), checks the pull and fixes failures through config."""

MODEL = "claude-opus-5-5"
EFFORT = "medium"
MAX_TURNS = 60
MAX_BUDGET_USD = 1.00

PROMPT_PATH = PROMPT_DIR / "config_agent.md"
WRITABLE_DIRS = [REPO_ROOT / "a_Configs", REPO_ROOT / "z_Data"]
# Preprocessing scripts write their output here, so sandboxed Bash needs these too. The Write/Edit tools don't get them.
SCRIPT_OUTPUT_DIRS = [REPO_ROOT / "preprocessed_data", REPO_ROOT / "logs"]
TOOLS = ["Read", "Write", "Edit", "Bash"]

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "source_key": {"type": "string"},
        "status": {"type": "string", "enum": ["passed", "sourcing_retry", "escalate", "error"]},
        "added": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "period": {"type": "string"},
                    "kind": {"type": "string", "enum": ["new", "revised"]},
                    "files": {"type": "array", "items": {"type": "string"}},
                    "description": {"type": "string"},
                },
                "required": ["period", "kind", "files", "description"],
                "additionalProperties": False,
            },
        },
        "config_changes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"file": {"type": "string"}, "change": {"type": "string"}},
                "required": ["file", "change"],
                "additionalProperties": False,
            },
        },
        "checks": {"type": "string"},
        "sourcing_feedback": {"type": ["string", "null"]},
        "escalation_reason": {"type": ["string", "null"]},
        "notes": {"type": "string"},
    },
    "required": ["source_key", "status", "added", "config_changes", "checks", "sourcing_feedback", "escalation_reason", "notes"],
    "additionalProperties": False,
}


@dataclass
class ConfigResult:
    source_key: str
    status: str
    added: list[dict] = field(default_factory=list)
    config_changes: list[dict] = field(default_factory=list)
    checks: str = ""
    sourcing_feedback: str | None = None
    escalation_reason: str | None = None
    notes: str = ""
    cost_usd: float | None = None


def build_prompt(source_key, sourcing_result, check_report):
    """Fill in the Configuration/Testing agent prompt template for one source, the sourcing agent's result and the failed checks."""
    source = get_source(source_key)
    runbook_path = RUNBOOK_DIR / source["runbook"]
    pulled = {k: v for k, v in asdict(sourcing_result).items() if k != "cost_usd"}
    commands = pipeline_commands(source, sourcing_result.periods)
    command_text = "\n".join(f"- {name}: `{format_command(c)}`" for name, c in commands.items()) or "None: this source has no automated checks."
    template = string.Template(PROMPT_PATH.read_text())
    return template.substitute(
        source_key=source_key,
        source_name=source["name"],
        source_url=source["url"],
        repo_root=REPO_ROOT,
        sourcing_result=json.dumps(pulled, indent=2),
        check_report=check_report.summary(),
        commands=command_text,
        runbook_path=runbook_path.relative_to(REPO_ROOT),
        runbook=runbook_path.read_text(),
    )


def _build_options():
    # cwd is a_Configs, not the repo root, because sandboxed Bash can always write to its working directory.
    # The agent cd's to the repo root to run scripts.
    cwd = REPO_ROOT / "a_Configs"
    write_guard = path_guard(WRITABLE_DIRS, ["file_path"], cwd, "write")
    read_guard = path_guard([REPO_ROOT], ["file_path", "path"], cwd, "read")
    return ClaudeAgentOptions(
        model=MODEL,
        effort=EFFORT,
        cwd=cwd,
        tools=TOOLS,
        allowed_tools=TOOLS,
        permission_mode="dontAsk",
        setting_sources=[],
        env={**AGENT_ENV, "PYTHONDONTWRITEBYTECODE": "1"},
        max_turns=MAX_TURNS,
        max_budget_usd=MAX_BUDGET_USD,
        output_format={"type": "json_schema", "schema": RESULT_SCHEMA},
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Write|Edit", hooks=[write_guard]),
                HookMatcher(matcher="Read|Glob|Grep", hooks=[read_guard]),
            ]
        },
        # Bash runs sandboxed with no network: it can write in cwd (a_Configs), z_Data and the preprocessing output
        # directories, and nowhere else, so it can't commit to git either
        sandbox={
            "enabled": True,
            "autoAllowBashIfSandboxed": True,
            "allowUnsandboxedCommands": False,
            "failIfUnavailable": True,
            "filesystem": {"allowWrite": [str(d) for d in WRITABLE_DIRS + SCRIPT_OUTPUT_DIRS]},
        },
    )


async def run_config_agent(source_key, sourcing_result, check_report):
    """Run the Configuration/Testing agent on a pull whose automated checks failed, and return a ConfigResult."""
    run = await run_agent(build_prompt(source_key, sourcing_result, check_report), _build_options())
    if run.error:
        return ConfigResult(source_key, "error", notes=run.error, cost_usd=run.cost_usd)
    return ConfigResult(**run.output, cost_usd=run.cost_usd)


def run_config_agent_sync(source_key, sourcing_result, check_report):
    return asyncio.run(run_config_agent(source_key, sourcing_result, check_report))


def print_config_result(result):
    print(f"Source:   {result.source_key}")
    print(f"Status:   {result.status}")
    print(f"Checks:   {result.checks or '-'}")
    print(f"Cost:     ${result.cost_usd or 0:.4f}")
    for item in result.added:
        print(f"Added:    {item['period']} ({item['kind']}): {item['description']} [{', '.join(item['files'])}]")
    for change in result.config_changes:
        print(f"Changed:  {change['file']}: {change['change']}")
    print(f"Notes:    {result.notes}")
    if result.status == "sourcing_retry":
        print(f"\nFeedback for the sourcing agent:\n{result.sourcing_feedback}")
    if result.status == "escalate":
        print("\n*** ESCALATION: needs a human ***")
        print(result.escalation_reason)


if __name__ == "__main__":
    from agents.checks import run_checks
    from agents.sourcing_agent import SourcingResult

    parser = argparse.ArgumentParser(description="Check and integrate a pull from the sourcing agent.")
    parser.add_argument("source", help="Source key from SourcesConfig.SOURCES, e.g. maine_legislature")
    parser.add_argument("--status", default="new_data", choices=["new_data", "revised"], help="What the sourcing agent reported")
    parser.add_argument("--file", action="append", default=[], help="A file the sourcing agent saved (repo path). Repeatable")
    parser.add_argument("--period", action="append", default=[], help="A period the pull covers. Repeatable")
    parser.add_argument("--notes", default="", help="The sourcing agent's notes")
    args = parser.parse_args()

    pulled = SourcingResult(args.source, args.status, args.file, args.period, args.notes)
    report = run_checks(get_source(args.source), pulled)
    print(report.summary())
    if report.passed and report.has_validation:
        print("Automated checks passed, so the Configuration/Testing agent isn't needed.")
    else:
        print_config_result(run_config_agent_sync(args.source, pulled, report))
