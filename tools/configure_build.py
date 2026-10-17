from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--application-id", default="1539198053570060299")
    parser.add_argument("--activity-name", default="Яндекс Музыка")
    args = parser.parse_args()
    application_id = args.application_id.strip()
    if application_id and (not application_id.isdigit() or not 17 <= len(application_id) <= 20):
        raise SystemExit("Discord Application ID must contain 17-20 digits")
    destination = Path(__file__).resolve().parents[1] / "src" / "resources" / "build.json"
    destination.write_text(
        json.dumps(
            {
                "discord_application_id": application_id,
                "discord_activity_name": args.activity_name.strip() or "Яндекс Музыка",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
