"""Print the default scenario and optional exploratory validation stresses."""
import argparse
import json

from engine import Settings, demo_data, evaluate, load_data

SCENARIOS = {
    "default": Settings(),
    "short-window": Settings(months=24),
    "estimates": Settings(equity_shift=-.03, shrink=.25),
    "cost": Settings(costs_bps=100),
    "stop": Settings(risk_multiple=0),
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=SCENARIOS, default="default")
    parser.add_argument("--demo", action="store_true", help="Use original synthetic example data.")
    args = parser.parse_args()
    data = demo_data() if args.demo else load_data()
    print(json.dumps(evaluate(*data, SCENARIOS[args.scenario]), indent=2, allow_nan=False))
