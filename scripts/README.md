# PDF Pre-processing Pipeline

This directory contains the PDF pre-processing pipeline for the Maine Budget Tool. The pipeline converts slow-to-parse PDF files into fast-loading structured data formats.

## Overview

The pipeline processes two types of PDFs:
- **Maine Budget PDFs**: Multi-page budget documents → Parquet files
- **Revenue PDFs**: Financial tables → Pickle files

## Quick Start

### Process All PDFs
```bash
python scripts/preprocess_pdfs.py
```

### Process Specific Types
```bash
# Budget PDFs only
python scripts/preprocess_pdfs.py --budget-pdfs

# Revenue PDFs only
python scripts/preprocess_pdfs.py --revenue-pdfs

# Validation only
python scripts/preprocess_pdfs.py --validate
```

## When to Run Pre-processing

Run the pre-processing script when you:

1. **Add new PDFs**: New budget or revenue PDFs
2. **Update existing PDFs**: When PDFs are modified
3. **Change parsing logic**: If PDF parsing code is updated
4. **Fresh deployment**: To ensure processed data is available

## Output Files

Processed data is saved in `preprocessed_data/`:

```
preprocessed_data/
├── budgets/           # Maine budget data (Parquet)
│   ├── 2016-2017_budget.parquet
│   ├── 2018-2019_budget.parquet
│   └── ...
└── revenue/           # Revenue data (Pickle)
    ├── revenue_2016.pkl
    ├── revenue_2017.pkl
    └── ...
```

## Validation

The pipeline automatically validates processed data against source PDFs:
- Row count verification
- Sum totals comparison
- Data integrity checks

Check `logs/preprocessing.log` for detailed results.

## Fallback Behavior

The app automatically uses pre-processed files when available, with fallback to PDF parsing if:
- Processed file doesn't exist
- Processed file is corrupted
- Loading fails for any reason

## Performance Impact

- **Without pre-processing**: PDF parsing on every app load (~10-30 seconds)
- **With pre-processing**: Instant loading from structured files (~0.1-1 second)
- **Space overhead**: Minimal (processed files are much smaller than PDFs)

## Troubleshooting

### Common Issues

1. **Missing PDFs**: Ensure all source PDFs exist in `z_Data/`
2. **Parsing failures**: Check PDF format hasn't changed
3. **Validation errors**: Compare processed vs source data manually

### Logs
- Main log: `logs/preprocessing.log`
- Streamlit warnings: Check app logs for fallback messages

### Manual Validation
```bash
# Compare specific files
python -c "
import pandas as pd
pdf_data = pd.read_parquet('preprocessed_data/budgets/2024-2025_budget.parquet')
print('Processed shape:', pdf_data.shape)
print('Total sum:', pdf_data.sum().sum())
"
