import argparse
import asyncio
import string
from dataclasses import dataclass, field
from urllib.parse import urlparse

from claude_agent_sdk import ClaudeAgentOptions, HookMatcher
from agents.common import AGENT_ENV, PROMPT_DIR, REPO_ROOT, RUNBOOK_DIR, get_source, path_guard, run_agent, runbook_section

"""Sourcing agent: checks one manual source for new data and pulls it into z_Data following the source's runbook."""

MODEL = "claude-sonnet-5-5"
EFFORT = "medium"
MAX_TURNS = 50
MAX_BUDGET_USD = 0.10

PROMPT_PATH = PROMPT_DIR / "sourcing_agent.md"
READABLE_DIRS = [REPO_ROOT / "a_Configs", REPO_ROOT / "z_Data"]
TOOLS = ["Read", "Glob", "Grep", "WebFetch", "Write", "Edit", "Bash"]

RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "source_key": {"type": "string"},
        "status": {"type": "string", "enum": ["new_data", "revised", "no_new_data", "escalate", "error"]},
        "files": {"type": "array", "items": {"type": "string"}},
        "periods": {"type": "array", "items": {"type": "string"}},
        "as_of": {"type": ["string", "null"]},
        "notes": {"type": "string"},
        "escalation_reason": {"type": ["string", "null"]},
    },
    "required": ["source_key", "status", "files", "periods", "as_of", "notes", "escalation_reason"],
    "additionalProperties": False,
}


@dataclass
class SourcingResult:
    source_key: str
    status: str
    files: list[str] = field(default_factory=list)
    periods: list[str] = field(default_factory=list)
    notes: str = ""
    as_of: str | None = None  # YYYY-MM-DD the pulled data is current to, as the runbook defines it
    escalation_reason: str | None = None
    cost_usd: float | None = None

    @property
    def new_data_found(self):
        # Revised data also needs to go through Configuration/Testing, so it counts as new
        return self.status in ("new_data", "revised")


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
        runbook=runbook_section(source, "Sourcing"),
        special_instructions=special_instructions or "None",
    )


def _build_options(data_dir, source_url):
    write_guard = path_guard([data_dir], ["file_path"], data_dir, "write")
    read_guard = path_guard(READABLE_DIRS, ["file_path", "path"], data_dir, "read")
    return ClaudeAgentOptions(
        model=MODEL,
        effort=EFFORT,
        cwd=data_dir,
        tools=TOOLS,
        allowed_tools=TOOLS,
        permission_mode="dontAsk",
        setting_sources=[],
        env=AGENT_ENV,
        max_turns=MAX_TURNS,
        max_budget_usd=MAX_BUDGET_USD,
        output_format={"type": "json_schema", "schema": RESULT_SCHEMA},
        hooks={
            "PreToolUse": [
                HookMatcher(matcher="Write|Edit", hooks=[write_guard]),
                HookMatcher(matcher="Read|Glob|Grep", hooks=[read_guard]),
            ]
        },
        # Bash runs sandboxed: it can only write in cwd (data_dir), can only read a_Configs and z_Data in the repo,
        # and can only reach the source's own domain (for curl downloads)
        sandbox={
            "enabled": True,
            "autoAllowBashIfSandboxed": True,
            "allowUnsandboxedCommands": False,
            "failIfUnavailable": True,
            "filesystem": {
                "denyRead": [str(REPO_ROOT)],
                "allowRead": [str(d) for d in READABLE_DIRS],
            },
            "network": {"allowedDomains": [urlparse(source_url).hostname]},
        },
    )


async def run_sourcing_agent(source_key, special_instructions=None):
    """Run the sourcing agent for one source and return a SourcingResult.

    special_instructions carries feedback from the Configuration/Testing agent on a retry."""
    source = get_source(source_key)
    data_dir = REPO_ROOT / source["data_dir"]
    run = await run_agent(build_prompt(source_key, special_instructions), _build_options(data_dir, source["url"]))
    if run.error:
        return SourcingResult(source_key, "error", notes=run.error, cost_usd=run.cost_usd)
    return SourcingResult(**run.output, cost_usd=run.cost_usd)


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
    print(f"As of:    {result.as_of or '-'}")
    print(f"Cost:     ${result.cost_usd or 0:.4f}")
    print(f"Notes:    {result.notes}")
    if result.status == "escalate":
        print("\n*** ESCALATION: the source has changed and needs a human ***")
        print(result.escalation_reason)
