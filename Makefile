.PHONY: setup-files run run-1m run-3m run-6m run-12m test app audit clean privacy validate workflow

setup-files:
	python python/setup_private_files.py

run:
	python python/run_pipeline.py --dataset 12m

run-1m:
	python python/run_pipeline.py --dataset 1m

run-3m:
	python python/run_pipeline.py --dataset 3m

run-6m:
	python python/run_pipeline.py --dataset 6m

run-12m:
	python python/run_pipeline.py --dataset 12m

test:
	python -m pytest

privacy:
	python python/run_privacy_scan.py

app:
	streamlit run app/streamlit_app.py

audit:
	python python/run_pipeline.py --dataset 12m
	python -m pytest
	python python/run_privacy_scan.py

workflow:
	python python/run_workflow.py

# Full local validation gate.
validate: audit workflow
	python -c "from shared.contracts import load_contract; [load_contract(n) for n in ['product_master.yml','marketplace_transactions.yml','public_outputs/anonymized_master.yml','public_outputs/marketplace_summary.yml','public_outputs/product_performance.yml','public_outputs/inventory_action_review.yml','public_outputs/validation_summary.yml','public_outputs/dataset_profile.yml']]; print('All 8 data contracts loaded and are well-formed.')"

clean:
	rm -rf data/public/*.csv
