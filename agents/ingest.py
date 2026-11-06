import argparse
import asyncio
from dataclasses import dataclass, field

from a_Configs.sources_config import SourcesConfig, set_last_updated
from agents.checks import CheckReport, run_checks
from agents.common import RUNBOOK_DIR, get_source
from agents.config_agent import ConfigResult, print_config_result, run_config_agent
from agents.sourcing_agent import SourcingResult, run_sourcing_agent

"""Ingest one manual source: the sourcing agent pulls new data, then the source's automated checks run on it.
The Configuration/Testing agent only runs when those checks fail (or the source has none), and pulls it rejects
go back to the sourcing agent with its feedback. Works for any source in SourcesConfig.SOURCES with a runbook."""

MAX_SOURCING_RETRIES = 2


@dataclass
class IngestResult:
    source_key: str
    status: str  # no_new_data | passed | escalate | error
    sourcing: list[SourcingResult] = field(default_factory=list)
    checks: list[CheckReport] = field(default_factory=list)
    config: list[ConfigResult] = field(default_factory=list)
    added: list[dict] = field(default_factory=list)
    escalation_reason: str | None = None

    @property
    def cost_usd(self):
        return sum(r.cost_usd or 0 for r in self.sourcing + self.config)


def _added_from_pull(sourced):
    """What was added, described from the sourcing agent's result (used when no Configuration/Testing agent ran)."""
    kind = "revised" if sourced.status == "revised" else "new"
    return [{"period": period, "kind": kind, "files": sourced.files, "description": sourced.notes} for period in sourced.periods]


def _finish_passed(result, source_key, sourced, added):
    result.status = "passed"
    result.added = added
    if sourced.as_of:
        set_last_updated(source_key, sourced.as_of)
    return result


async def run_ingest(source_key, max_sourcing_retries=MAX_SOURCING_RETRIES):
    """Pull, check and integrate new data for one source until it passes, needs a human, or fails."""
    source = get_source(source_key)
    result = IngestResult(source_key, "error")
    feedback = None
    for _ in range(max_sourcing_retries + 1):
        sourced = await run_sourcing_agent(source_key, feedback)
        result.sourcing.append(sourced)
        if not sourced.new_data_found:
            # no_new_data on a retry means the sourcing agent couldn't act on the feedback
            if sourced.status == "no_new_data" and feedback is None:
                result.status = "no_new_data"
            elif sourced.status == "no_new_data":
                result.status = "escalate"
                result.escalation_reason = f"The sourcing agent found nothing to re-pull after this feedback:\n{feedback}\n\nIts notes: {sourced.notes}"
            else:
                result.status = sourced.status
                result.escalation_reason = sourced.escalation_reason or sourced.notes
            return result

        report = run_checks(source, sourced)
        result.checks.append(report)
        if report.passed and report.has_validation:
            return _finish_passed(result, source_key, sourced, _added_from_pull(sourced))

        checked = await run_config_agent(source_key, sourced, report)
        result.config.append(checked)
        if checked.status == "passed":
            return _finish_passed(result, source_key, sourced, checked.added)
        if checked.status != "sourcing_retry":
            result.status = checked.status
            result.escalation_reason = checked.escalation_reason if checked.status == "escalate" else checked.notes
            return result
        feedback = checked.sourcing_feedback

    result.status = "escalate"
    result.escalation_reason = f"The Configuration/Testing agent rejected {max_sourcing_retries + 1} pulls. Last feedback:\n{feedback}"
    return result


def run_ingest_sync(source_key, max_sourcing_retries=MAX_SOURCING_RETRIES):
    return asyncio.run(run_ingest(source_key, max_sourcing_retries))


def ingestable_sources():
    """Manual sources that have a runbook written and somewhere to write data."""
    return [key for key, source in SourcesConfig.SOURCES.items()
            if source.get("runbook") and source.get("data_dir") and (RUNBOOK_DIR / source["runbook"]).exists()]


def print_ingest_result(result):
    for i, sourced in enumerate(result.sourcing, 1):
        print(f"--- Sourcing attempt {i}: {sourced.status} {', '.join(sourced.files)} (${sourced.cost_usd or 0:.4f})")
        print(sourced.notes)
        if i <= len(result.checks):
            print(f"--- Automated checks {i}:")
            print(result.checks[i - 1].summary())
        if i <= len(result.config):
            print(f"\n--- Configuration/Testing attempt {i}")
            print_config_result(result.config[i - 1])
    print(f"\n=== {result.source_key}: {result.status} (total ${result.cost_usd:.4f}) ===")
    for item in result.added:
        print(f"Added: {item['period']} ({item['kind']}) [{', '.join(item['files'])}]")
    if result.escalation_reason and result.status in ("escalate", "error"):
        print(result.escalation_reason)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pull, check and integrate new data for manual sources.")
    parser.add_argument("source", nargs="?", help="Source key from SourcesConfig.SOURCES, e.g. maine_legislature")
    parser.add_argument("--all", action="store_true", help="Run every manual source that has a runbook")
    parser.add_argument("--max-retries", type=int, default=MAX_SOURCING_RETRIES, help="How many times to send a rejected pull back to the sourcing agent")
    args = parser.parse_args()
    if bool(args.source) == args.all:
        parser.error("Give one source key or --all")

    if args.all:
        keys = ingestable_sources()
        skipped = [k for k, s in SourcesConfig.SOURCES.items() if s.get("runbook") and k not in keys]
        if skipped:
            print(f"Skipping sources without a runbook file or data_dir: {', '.join(skipped)}")
    else:
        keys = [args.source]

    for key in keys:
        print_ingest_result(run_ingest_sync(key, args.max_retries))
    print("Changes are left uncommitted for review.")
