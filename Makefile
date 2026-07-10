##############################################################################
# Makefile — Enterprise Retail Sales & Supply Chain Analytics
# Usage:
#   make install      Install Python dependencies
#   make etl          Run full ETL pipeline (clean → augment → load → queries)
#   make app          Launch Streamlit dashboard locally
#   make docker-build Build Docker image
#   make docker-run   Run Streamlit dashboard in Docker
#   make clean        Remove generated DB and processed files (prompts first)
##############################################################################

.PHONY: install etl clean app docker-build docker-run help

PYTHON   := python
PIP      := pip
SRC      := src
DATA_DIR := data/processed

## ── Install ──────────────────────────────────────────────────────────────────
install:
	$(PIP) install -r requirements.txt

## ── ETL Pipeline ─────────────────────────────────────────────────────────────
etl: install
	@echo "============================================================"
	@echo " Phase 3: Clean & Transform"
	@echo "============================================================"
	$(PYTHON) $(SRC)/clean_transform.py

	@echo "============================================================"
	@echo " Phase 4: Augment to 100K+ rows"
	@echo "============================================================"
	$(PYTHON) $(SRC)/augment_data.py

	@echo "============================================================"
	@echo " Phase 5a: Load to SQLite"
	@echo "============================================================"
	$(PYTHON) $(SRC)/load_to_db.py

	@echo "============================================================"
	@echo " Phase 5b: Run SQL Analysis Queries"
	@echo "============================================================"
	$(PYTHON) $(SRC)/run_analysis_queries.py

	@echo ""
	@echo "✅  Full ETL pipeline complete."

## ── Streamlit App ────────────────────────────────────────────────────────────
app:
	streamlit run app.py

## ── Docker ───────────────────────────────────────────────────────────────────
docker-build:
	docker build -t retail-analytics .

docker-run: docker-build
	docker run -p 8501:8501 \
		-v $(PWD)/data/processed:/app/data/processed:ro \
		retail-analytics

## ── Cleanup ──────────────────────────────────────────────────────────────────
clean:
	@echo "WARNING: This will delete data/processed/ and *.db files."
	@read -p "Continue? (y/N): " confirm && [ "$$confirm" = "y" ]
	rm -rf $(DATA_DIR)/*.csv
	rm -f *.db *.sqlite *.sqlite3
	@echo "Cleaned."

## ── Help ─────────────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "Available make targets:"
	@echo "  install       Install Python dependencies from requirements.txt"
	@echo "  etl           Run full ETL pipeline end-to-end"
	@echo "  app           Launch Streamlit dashboard (localhost:8501)"
	@echo "  docker-build  Build Docker image"
	@echo "  docker-run    Run dashboard in Docker container"
	@echo "  clean         Remove generated files (prompts for confirmation)"
	@echo ""
