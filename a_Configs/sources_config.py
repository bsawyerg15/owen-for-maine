"""
Configuration sources for this project.
"""

class SourcesConfig:
    """Configuration class for sources and footnotes."""

    # Sources for footnotes
    SOURCES = {
        'maine_legislature': {
            'name': 'Maine State Legislature',
            'url': 'https://legislature.maine.gov/ofpr/total-state-budget-information/9304'
        },
        'maine_dept_financial': {
            'name': 'Maine Dept. of Administrative and Financial Services',
            'url': 'https://www.maine.gov/osc/financial-reporting/revenue-reports/reports-archive'
        },
        'transparent_nh_revenue': {
            'name': 'Transparent NH (Revenue Sources)',
            'url': 'https://www.nh.gov/transparentnh/where-the-money-comes-from/'
        },
        'transparent_nh_expenditure': {
            'name': "Transparent NH (Governor's Expenditure Reports)",
            'url': 'https://www.nh.gov/transparentnh/where-the-money-goes/governors-expenditure-reports/index.htm'
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
        'FRED_nh_gdp': {
            'name': "FRED: New Hampshire GDP",
            'url': 'https://fred.stlouisfed.org/series/NHNQGSP'
        },
        'mainecare_enrollment':{
            'name': "MaineCare Enrollment",
            'url': ''
        },
        'me_public_school_enrollment': {
            'name': "Maine DOE: Maine Public School Enrollment",
            'url': 'https://www.maine.gov/doe/data-warehouse/reporting/enrollment'
        },
        'nh_medicaid_enrollment':{
            'name': "NH DHHS: Medicaid Enrollment",
            'url': 'https://www.dhhs.nh.gov/sites/g/files/ehbemt476/files/documents2/bpq-da-medicaid-enrollment.pdf?'
        },
        'nh_public_school_enrollment':
            'name': 'New Hampshire Public School Enrollment',
            'url': ''
        {

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


