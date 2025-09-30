micromamba install -y uv
apt-get update
apt-get install -f -y python3.12-dev build-essential
cd Metabiome
uv sync
uv add ipykernel
uv run python -m ipykernel install --name metabiome --display-name "Python (Metabiome)"

