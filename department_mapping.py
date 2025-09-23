import pandas as pd

# Maine departments from combined_df
maine_departments = [
    "DEPARTMENT OF ADMINISTRATIVE AND FINANCIAL SERVICES",
    "DEPARTMENT OF AGRICULTURE, CONSERVATION AND FORESTRY",
    "DEPARTMENT OF THE ATTORNEY GENERAL",
    "DEPARTMENT OF AUDIT",
    "DEPARTMENT OF CORRECTIONS",
    "DEPARTMENT OF DEFENSE, VETERANS AND EMERGENCY MANAGEMENT",
    "DEPARTMENT OF ECONOMIC AND COMMUNITY DEVELOPMENT",
    "DEPARTMENT OF EDUCATION",
    "DEPARTMENT OF ENERGY RESOURCES",
    "DEPARTMENT OF ENVIRONMENTAL PROTECTION",
    "EXECUTIVE DEPARTMENT",
    "DEPARTMENT OF HEALTH AND HUMAN SERVICES (Formerly DHS)",
    "DEPARTMENT OF INLAND FISHERIES AND WILDLIFE",
    "JUDICIAL DEPARTMENT",
    "DEPARTMENT OF LABOR",
    "DEPARTMENT OF MARINE RESOURCES",
    "DEPARTMENT OF TRANSPORTATION"
]

# NH departments from nh_as_reported_df
nh_departments = [
    "ADMINISTRATIVE SERV",
    "AGRICULT, MARKETS & FOOD",
    "BANKING",
    "BUS & ECON AFFAIRS",
    "COMMUNITY COLLEGE SYSTEM OF NH",
    "CORRECTIONS",
    "DEPT. OF ENERGY",
    "DEVELOPMENT DISABILITIES CNCL",
    "EDUCATION DEPT OF",
    "EMPLOYMENT SECURITY",
    "ENVIRONMENTAL SERV",
    "EXECUTIVE",
    "EXECUTIVE COUNCIL",
    "FISH AND GAME",
    "HHS: COMMISSIONER'S OFFICE",
    "INFORMATION TECHNOLOGY",
    "INSURANCE",
    "JUDICIAL BRANCH",
    "JUDICIAL COUNCIL",
    "JUSTICE",
    "LABOR",
    "LEGISLATIVE BRANCH",
    "LIQUOR COMMISSION",
    "LOTTERY COMMISSION",
    "MILITARY AFFRS & VET SVCS",
    "NATURAL & CULTURAL RESRCS",
    "PEASE DEVELOPMENT AUTHORITY",
    "POLICE STDS & TRAINING COUNCIL",
    "PROF LICENSURE & CERT OFFICE",
    "PUBLIC EMPLOYEE LABOR REL BRD",
    "RETIREMENT SYSTEM",
    "REVENUE ADMINISTRATION",
    "SAFETY",
    "STATE",
    "TAX & LAND APPEALS BOARD",
    "TRANSPORTATION",
    "TREASURY",
    "UNIVERSITY SYSTEM OF NH",
    "VETERANS HOME"
]

# Create mapping dictionary
department_mapping = {
    # Administrative
    "DEPARTMENT OF ADMINISTRATIVE AND FINANCIAL SERVICES": "Administration & Finance",
    "ADMINISTRATIVE SERV": "Administration & Finance",

    # Agriculture
    "DEPARTMENT OF AGRICULTURE, CONSERVATION AND FORESTRY": "Agriculture & Natural Resources",
    "AGRICULT, MARKETS & FOOD": "Agriculture & Natural Resources",

    # Attorney General/Justice
    "DEPARTMENT OF THE ATTORNEY GENERAL": "Attorney General",
    "JUSTICE": "Attorney General",

    # Audit
    "DEPARTMENT OF AUDIT": "Audit",

    # Banking/Financial Regulation
    "BANKING": "Banking & Insurance",

    # Business/Economic Development
    "DEPARTMENT OF ECONOMIC AND COMMUNITY DEVELOPMENT": "Economic Development",
    "BUS & ECON AFFAIRS": "Economic Development",

    # Community Colleges
    "COMMUNITY COLLEGE SYSTEM OF NH": "Community Colleges",

    # Corrections
    "DEPARTMENT OF CORRECTIONS": "Corrections",
    "CORRECTIONS": "Corrections",

    # Disabilities
    "DEVELOPMENT DISABILITIES CNCL": "Developmental Disabilities",

    # Education
    "DEPARTMENT OF EDUCATION": "Education",
    "EDUCATION DEPT OF": "Education",

    # Employment
    "EMPLOYMENT SECURITY": "Employment Security",

    # Energy
    "DEPARTMENT OF ENERGY RESOURCES": "Energy",
    "DEPT. OF ENERGY": "Energy",

    # Environment
    "DEPARTMENT OF ENVIRONMENTAL PROTECTION": "Environmental Protection",
    "ENVIRONMENTAL SERV": "Environmental Protection",

    # Executive
    "EXECUTIVE DEPARTMENT": "Executive",
    "EXECUTIVE": "Executive",
    "EXECUTIVE COUNCIL": "Executive Council",

    # Fish & Wildlife
    "DEPARTMENT OF INLAND FISHERIES AND WILDLIFE": "Fish & Wildlife",
    "FISH AND GAME": "Fish & Wildlife",

    # Health & Human Services
    "DEPARTMENT OF HEALTH AND HUMAN SERVICES (Formerly DHS)": "Health & Human Services",
    "HHS: COMMISSIONER'S OFFICE": "Health & Human Services",

    # Information Technology
    "INFORMATION TECHNOLOGY": "Information Technology",

    # Insurance
    "INSURANCE": "Insurance",

    # Judicial
    "JUDICIAL DEPARTMENT": "Judicial",
    "JUDICIAL BRANCH": "Judicial",
    "JUDICIAL COUNCIL": "Judicial Council",

    # Labor
    "DEPARTMENT OF LABOR": "Labor",
    "LABOR": "Labor",

    # Legislative
    "LEGISLATIVE BRANCH": "Legislative",

    # Liquor
    "LIQUOR COMMISSION": "Liquor Commission",

    # Lottery
    "LOTTERY COMMISSION": "Lottery Commission",

    # Marine Resources
    "DEPARTMENT OF MARINE RESOURCES": "Marine Resources",

    # Military/Veterans
    "DEPARTMENT OF DEFENSE, VETERANS AND EMERGENCY MANAGEMENT": "Military & Veterans",
    "MILITARY AFFRS & VET SVCS": "Military & Veterans",
    "VETERANS HOME": "Military & Veterans",

    # Natural & Cultural Resources
    "NATURAL & CULTURAL RESRCS": "Natural & Cultural Resources",

    # Pease Development
    "PEASE DEVELOPMENT AUTHORITY": "Pease Development Authority",

    # Police Standards
    "POLICE STDS & TRAINING COUNCIL": "Police Standards & Training",

    # Professional Licensure
    "PROF LICENSURE & CERT OFFICE": "Professional Licensure",

    # Public Employee Labor
    "PUBLIC EMPLOYEE LABOR REL BRD": "Public Employee Labor Relations",

    # Retirement
    "RETIREMENT SYSTEM": "Retirement System",

    # Revenue
    "REVENUE ADMINISTRATION": "Revenue Administration",

    # Safety
    "SAFETY": "Safety",

    # State
    "STATE": "State",

    # Tax & Land Appeals
    "TAX & LAND APPEALS BOARD": "Tax & Land Appeals",

    # Transportation
    "DEPARTMENT OF TRANSPORTATION": "Transportation",
    "TRANSPORTATION": "Transportation",

    # Treasury
    "TREASURY": "Treasury",

    # University System
    "UNIVERSITY SYSTEM OF NH": "University System"
}

# Create the mapping data
mapping_data = []

# Add Maine mappings
for dept in maine_departments:
    if dept in department_mapping:
        mapping_data.append({
            "State": "Maine",
            "Original_Department": dept,
            "Common_Department": department_mapping[dept]
        })

# Add NH mappings
for dept in nh_departments:
    if dept in department_mapping:
        mapping_data.append({
            "State": "New Hampshire",
            "Original_Department": dept,
            "Common_Department": department_mapping[dept]
        })

# Create DataFrame
df = pd.DataFrame(mapping_data)

# Sort by Common_Department, then State
df = df.sort_values(['Common_Department', 'State'])

# Save to CSV
df.to_csv('department_mapping.csv', index=False)

print("Department mapping CSV created successfully!")
print(f"Total mappings: {len(df)}")
print("\nFirst 10 rows:")
print(df.head(10))
