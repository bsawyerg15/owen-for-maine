import subprocess
import sys
from dataclasses import dataclass, field

import pandas as pd

from agents.common import REPO_ROOT

"""Deterministic checks that run on a pull before (and instead of) the Configuration/Testing agent.

Each source declares its own preprocess and validate flags in SourcesConfig.SOURCES, so the same checks work for any manual source."""

COMMAND_TIMEOUT_SECONDS = 1800


@dataclass
class CheckStep:
    name: str
    passed: bool
    output: str = ""


@dataclass
class CheckReport:
    steps: list[CheckStep] = field(default_factory=list)
    has_validation: bool = False  # False means code can't vouch for this source's data, so the agent has to

    @property
    def passed(self):
        return all(step.passed for step in self.steps)

    def summary(self):
        """Short text for logs and the Configuration/Testing agent's prompt."""
        lines = []
        for step in self.steps:
            lines.append(f"{'✓' if step.passed else '✗'} {step.name}")
            lines += [f"    {line}" for line in step.output.strip().splitlines()]
        if not self.has_validation:
            lines.append("This source has no validation checks in code, so they couldn't confirm the data.")
        return "\n".join(lines)


def pipeline_commands(source, periods):
    """The preprocessing and validation commands for a source's pull, limited to the pulled periods."""
    year_flags = [arg for period in periods for arg in ('--year', period)]
    commands = {}
    if source.get('preprocess'):
        commands['preprocess'] = ['python', 'scripts/preprocess_pdfs.py', *source['preprocess'], *year_flags, '--quiet']
    if source.get('validate'):
        commands['validate'] = ['python', 'scripts/validate_data.py', *source['validate'], *year_flags, '--failures-only']
    return commands


def format_command(command):
    return ' '.join(f'"{arg}"' if ' ' in arg else arg for arg in command)


def check_files(files):
    """Every pulled file exists, isn't empty, and is the type its extension says."""
    problems = []
    for name in files:
        path = REPO_ROOT / name
        if not path.is_file():
            problems.append(f"{name}: doesn't exist")
        elif path.stat().st_size == 0:
            problems.append(f"{name}: is empty")
        elif path.suffix.lower() == '.pdf' and not path.read_bytes()[:5].startswith(b'%PDF'):
            problems.append(f"{name}: isn't a PDF (doesn't start with %PDF)")
        elif path.suffix.lower() == '.csv':
            try:
                pd.read_csv(path)
            except Exception as e:
                problems.append(f"{name}: doesn't load as a CSV ({e})")
    return CheckStep('pulled files', not problems, "\n".join(problems))


def _run(name, command, fail_on=()):
    """Run a command from the repo root. It fails on a non-zero exit or an output line containing any of fail_on."""
    command = [sys.executable if command[0] == 'python' else command[0], *command[1:]]
    try:
        completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, timeout=COMMAND_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return CheckStep(name, False, f"Timed out after {COMMAND_TIMEOUT_SECONDS}s")
    output = (completed.stdout + completed.stderr).strip()
    flagged = any(marker in line for line in output.splitlines() for marker in fail_on)
    return CheckStep(name, completed.returncode == 0 and not flagged, output)


def run_checks(source, sourcing_result):
    """Check a pull: the files, then the source's preprocessing, then its validation. Stops at the first failure."""
    commands = pipeline_commands(source, sourcing_result.periods)
    report = CheckReport(has_validation='validate' in commands)

    report.steps.append(check_files(sourcing_result.files))
    if not report.passed:
        return report
    if 'preprocess' in commands:
        # preprocess_pdfs.py logs a failed file and carries on, so treat any warning or error as a failure
        report.steps.append(_run('preprocessing', commands['preprocess'], fail_on=('WARNING', 'ERROR')))
        if not report.passed:
            return report
    if 'validate' in commands:
        report.steps.append(_run('validation', commands['validate']))
    return report
