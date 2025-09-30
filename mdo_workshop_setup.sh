apt-get update
apt-get install -f -y python3.12-dev build-essential
cd Metabiome
export UV_HTTP_TIMEOUT=3000
uv sync --active
uv add ipykernel
uv run python -m ipykernel install --name metabiome --display-name "Python (Metabiome)"

