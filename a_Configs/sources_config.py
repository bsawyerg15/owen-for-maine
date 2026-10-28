"""
Configuration sources for this project.
"""

import re
from pathlib import Path


class SourcesConfig:
    """Configuration class for sources and footnotes.

    Manual sources also have the keys the ingest agents use: runbook, data_dir, last_updated,
    and the preprocess/validate flags that agents/ingest.py runs after a new pull."""

    # Sources for footnotes
    SOURCES = {
        'maine_legislature': {
            'name': 'Maine State Budget: Maine Legislature',
            'url': 'https://legislature.maine.gov/ofpr/total-state-budget-information/9304',
            'runbook': 'maine_legislature.md',
            'data_dir': 'z_Data/ME/',
            'preprocess': ['--budget-pdfs', '--positions-pdfs'],  # flags for scripts/preprocess_pdfs.py
            'validate': ['--budget', '--positions'],  # flags for scripts/validate_data.py
            'last_updated': '2026-05-08'
        },
        'FRED_me_gdp': {
            'name': "FRED: Maine GDP",
            'url': 'https://fred.stlouisfed.org/series/MENQGSP'
        },
        'FRED_cpi': {
            'name': "FRED: CPI",
            'url': 'https://fred.stlouisfed.org/series/CPIAUCSL'
        },
        'FRED_me_pop': {
            'name': "FRED: Maine Population",
            'url': 'https://fred.stlouisfed.org/series/MEPOP'
        },
        'maine_dept_financial': {
            'name': 'General Fund Revenue Sources: Maine Dept. of Administrative and Financial Services',
            'url': 'https://www.maine.gov/osc/financial-reporting/revenue-reports/reports-archive',
            'runbook': 'maine_dept_financial.md',
            'data_dir': 'z_Data/ME General Fund Sources/',
            'preprocess': ['--revenue-pdfs'],  # flags for scripts/preprocess_pdfs.py
            'validate': ['--revenue'],  # flags for scripts/validate_data.py
            'last_updated': '2025-12-04'
        },
        'mainecare_enrollment':{
            'name': "MaineCare Enrollment: Maine DHHS",
            'url': 'https://www.dhhs.nh.gov/sites/g/files/ehbemt476/files/documents2/bpq-da-medicaid-enrollment.pdf',
            'runbook': 'mainecare_enrollment.md',
            'data_dir': 'z_Data/Department Statistics/HHS/',
            'preprocess': [],  # flags for scripts/preprocess_pdfs.py
            'validate': [],  # flags for scripts/validate_data.py
            'last_updated': '2025-12-11'
        },
        'me_public_school_enrollment': {
            'name': "Maine Public School Enrollment: Maine DOE",
            'url': 'https://www.maine.gov/doe/data-warehouse/reporting/enrollment',
            'runbook': 'me_public_school_enrollment.md',
            'data_dir': 'z_Data/Department Statistics/Education/',
            'preprocess': [],  # flags for scripts/preprocess_pdfs.py
            'validate': [],  # flags for scripts/validate_data.py
            'last_updated': '2025-12-11'
        },
        'transparent_nh_expenditure': {
            'name': "NH Expenditure Reports: Transparent NH",
            'url': 'https://www.nh.gov/transparentnh/where-the-money-goes/governors-expenditure-reports/index.htm',
            'runbook': 'transparent_nh_expenditure.md',
            'data_dir': 'z_Data/NH/',
            'preprocess': [],  # flags for scripts/preprocess_pdfs.py
            'validate': [],  # flags for scripts/validate_data.py
            'last_updated': '2025-12-16'
        },
        'FRED_nh_gdp': {
            'name': "FRED: New Hampshire GDP",
            'url': 'https://fred.stlouisfed.org/series/NHNQGSP'
        },
        'transparent_nh_revenue': {
            'name': 'NH Revenue Sources: Transparent NH',
            'url': 'https://www.nh.gov/transparentnh/where-the-money-comes-from/',
            'runbook': 'transparent_nh_revenue.md',
            'data_dir': 'z_Data/NH General Fund Sources/',
            'preprocess': [],  # flags for scripts/preprocess_pdfs.py
            'validate': [],  # flags for scripts/validate_data.py
            'last_updated': '2025-12-15'
        },
        'nh_medicaid_enrollment':  {
            'name': "NH Medicaid Enrollment: NH DHHS",
            'url': 'https://www.dhhs.nh.gov/sites/g/files/ehbemt476/files/documents2/bpq-da-medicaid-enrollment.pdf?',
            'runbook': 'nh_medicaid_enrollment.md',
            'data_dir': None,
            'preprocess': [],  # flags for scripts/preprocess_pdfs.py
            'validate': [],  # flags for scripts/validate_data.py
            'last_updated': None
        },
        'nh_public_school_enrollment': {
            'name': 'New Hampshire Public School Enrollment: NH DOE',
            'url': 'https://my.doe.nh.gov/iPlatform/Report/Report?path=%2FBDMQ%2FiPlatform%20Reports%2FEnrollment%20Data%2FState%20Totals%2FState%20Totals%20Ten%20Years%20Public%20and%20Private%20Fall%20Enrollments&name=State%20Totals%20Ten%20Years%20Public%20and%20Private%20Fall%20Enrollments&categoryName=State%20Totals&categoryId=12',
            'runbook': 'nh_public_school_enrollment.md',
            'data_dir': None,
            'preprocess': [],  # flags for scripts/preprocess_pdfs.py
            'validate': [],  # flags for scripts/validate_data.py
            'last_updated': None
        }
    }

    @staticmethod
    def get_footnotes_superscripts(source_keys):
        """Generate superscript footnote numbers with links for given source keys."""
        if not isinstance(source_keys, list):
            source_keys = [source_keys]

        links = []
        for key in source_keys:
            if key in SourcesConfig.SOURCES:
                # Get the position (1-based index) in the sources dict
                index = list(SourcesConfig.SOURCES.keys()).index(key) + 1
                url = SourcesConfig.SOURCES[key]['url']
                links.append(f'<a href="{url}">{index}</a>')

        if links:
            # Sort by index to ensure consistent ordering
            links.sort(key=lambda x: int(x.split('>')[1].split('<')[0]))
            return f"<sup>{' '.join(links)}</sup>"
        return ""


def set_last_updated(source_key, date):
    """Rewrite this file so source_key's last_updated is date (YYYY-MM-DD), and update SOURCES to match."""
    path = Path(__file__)
    text = path.read_text()
    block = re.search(rf"        '{re.escape(source_key)}':\s*\{{\n.*?\n        \}}", text, re.S)
    if block is None:
        raise ValueError(f"No block for {source_key} in {path}")
    new_block, count = re.subn(r"('last_updated': )(?:'[^']*'|None)", rf"\g<1>'{date}'", block.group(0))
    if count != 1:
        raise ValueError(f"Expected one last_updated line for {source_key}, found {count}")
    path.write_text(text[:block.start()] + new_block + text[block.end():])
    SourcesConfig.SOURCES[source_key]['last_updated'] = date
