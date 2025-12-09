import csv
import sys

def modify_dept_in_csv(file_path):
    with open(file_path, 'r', newline='', encoding='utf-8') as infile:
        reader = csv.reader(infile)
        rows = list(reader)

    modified_rows = []
    for row in rows:
        if row and row[0].endswith('DEPT'):
            row[0] = row[0].replace('DEPT', 'DEPT OF')
        modified_rows.append(row)

    with open(file_path, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(modified_rows)

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python modify_dept.py <csv_file>")
        sys.exit(1)
    modify_dept_in_csv(sys.argv[1])
