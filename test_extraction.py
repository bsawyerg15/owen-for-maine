import pdfplumber
import pandas as pd

revenue_path = 'z_Data/ME_Revenue/FY 2025 Revenue ME.pdf'

# Extract table from page 6 as text
with pdfplumber.open(revenue_path) as pdf:
    page_text = pdf.pages[5].extract_text()  # Page 6 is index 5

# Find table boundaries
lines = page_text.split('\n')
start_idx = None
end_idx = None
for i, line in enumerate(lines):
    if 'Comparison to Budget' in line:
        start_idx = i + 1
    if line.startswith('NOTES:'):
        end_idx = i
        break

# Extract table lines
table_lines = [line.strip() for line in lines[start_idx:end_idx] if line.strip()]

print('Total table lines:', len(table_lines))
print('Sample lines:')
for i in range(min(15, len(table_lines))):
    print(f'{i}: {repr(table_lines[i])}')

# Parse table data - each row has 10 elements: source + 9 values
data = []
for i in range(0, len(table_lines), 10):
    if i + 9 < len(table_lines):
        row_lines = table_lines[i:i+10]
        source = row_lines[0]
        values = row_lines[1:]

        # Clean values: remove $, %, commas, handle negatives
        cleaned_values = []
        for val in values:
            val = val.replace('$', '').replace('%', '').replace(',', '')
            if val.startswith('(') and val.endswith(')'):
                val = '-' + val[1:-1]
            try:
                if '.' in val:
                    cleaned_values.append(float(val))
                else:
                    cleaned_values.append(int(val))
            except ValueError:
                cleaned_values.append(0)  # Default to 0 if not parseable

        row = [source] + cleaned_values
        data.append(row)

# Create DataFrame
columns = ['Source', 'Month Actual', 'Month Budget', 'Month Variance', 'Month %', 'FYTD Actual', 'FYTD Budget', 'FYTD Variance', 'FYTD %', 'Total Budgeted FY']
df_text = pd.DataFrame(data, columns=columns)
print('DataFrame shape:', df_text.shape)
print(df_text.head(5))
