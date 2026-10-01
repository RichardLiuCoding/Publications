from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from codes.nature_insight_figures import (
    build_controller_fit_figures,
    build_fd_calibration_figures,
    build_nature_figure_package,
)


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Build Nature-style DT-SPM figure package.")
    parser.add_argument("project_root", nargs="?", default=".")
    args = parser.parse_args()
    paths = build_nature_figure_package(args.project_root)
    print(json.dumps(paths, indent=2))
