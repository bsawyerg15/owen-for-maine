import csv

input_file = 'a_Configs/department_mapping.csv'

# Read the CSV
with open(input_file, 'r', newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

# Strip quotes from the last field of each row
for row in rows:
    if len(row) > 0:
        row[-1] = row[-1].strip('"')

# Write back without quoting fields, as per "no quotations"
with open(input_file, 'w', newline='', encoding='utf-8') as f:
    for row in rows:
        line = ','.join(field for field in row)
        f.write(line + '\n')
