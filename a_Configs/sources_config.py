"""
Configuration sources for this project.
"""

class SourcesConfig:
    """Configuration class for sources and footnotes."""

    # Sources for footnotes
    SOURCES = {
        'maine_legislature': {
            'name': 'Maine State Budget: Maine Legislature',
            'url': 'https://legislature.maine.gov/ofpr/total-state-budget-information/9304'
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
            'url': 'https://www.maine.gov/osc/financial-reporting/revenue-reports/reports-archive'
        },
        'mainecare_enrollment':{
            'name': "MaineCare Enrollment: Maine DHHS",
            'url': 'https://www.dhhs.nh.gov/sites/g/files/ehbemt476/files/documents2/bpq-da-medicaid-enrollment.pdf'
        },
        'me_public_school_enrollment': {
            'name': "Maine Public School Enrollment: Maine DOE",
            'url': 'https://www.maine.gov/doe/data-warehouse/reporting/enrollment'
        },
        'transparent_nh_expenditure': {
            'name': "NH Expenditure Reports: Transparent NH",
            'url': 'https://www.nh.gov/transparentnh/where-the-money-goes/governors-expenditure-reports/index.htm'
        },
        'FRED_nh_gdp': {
            'name': "FRED: New Hampshire GDP",
            'url': 'https://fred.stlouisfed.org/series/NHNQGSP'
        },
        'transparent_nh_revenue': {
            'name': 'NH Revenue Sources: Transparent NH',
            'url': 'https://www.nh.gov/transparentnh/where-the-money-comes-from/'
        },
        'nh_medicaid_enrollment':  {
            'name': "NH Medicaid Enrollment: NH DHHS",
            'url': 'https://www.dhhs.nh.gov/sites/g/files/ehbemt476/files/documents2/bpq-da-medicaid-enrollment.pdf?'
        },
        'nh_public_school_enrollment': {
            'name': 'New Hampshire Public School Enrollment: NH DOE',
            'url': 'https://my.doe.nh.gov/iPlatform/Report/Report?path=%2FBDMQ%2FiPlatform%20Reports%2FEnrollment%20Data%2FState%20Totals%2FState%20Totals%20Ten%20Years%20Public%20and%20Private%20Fall%20Enrollments&name=State%20Totals%20Ten%20Years%20Public%20and%20Private%20Fall%20Enrollments&categoryName=State%20Totals&categoryId=12'
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


