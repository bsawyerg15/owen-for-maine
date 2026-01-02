# Maine Budget Tool - Development Commands

.PHONY: help preprocess preprocess-budgets preprocess-revenue preprocess-positions validate clean clean-cache

help:
	@echo "Available commands:"
	@echo "  make preprocess           - Process all PDFs"
	@echo "  make preprocess-budgets   - Process Maine budget PDFs only"
	@echo "  make preprocess-revenue   - Process revenue PDFs only"
	@echo "  make preprocess-positions - Process position data from budget PDFs only"
	@echo "  make validate             - Validate processed data"
	@echo "  make clean                - Remove processed data files"
	@echo "  make clean-cache          - Clear Streamlit cache"

preprocess:
	python scripts/preprocess_pdfs.py

preprocess-budgets:
	python scripts/preprocess_pdfs.py --budget-pdfs

preprocess-revenue:
	python scripts/preprocess_pdfs.py --revenue-pdfs

preprocess-positions:
	python scripts/preprocess_pdfs.py --positions-pdfs

validate:
	python scripts/preprocess_pdfs.py --validate

clean:
	rm -rf preprocessed_data/budgets/*.pkl
	rm -rf preprocessed_data/revenue/*.pkl
	rm -rf preprocessed_data/positions/*.pkl
	rm -rf logs/preprocessing.log

clean-cache:
	streamlit cache clear
