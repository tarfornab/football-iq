from pathlib import Path
from runpy import run_path

app = run_path(str(Path(__file__).with_name("app(2).py")))["app"]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
