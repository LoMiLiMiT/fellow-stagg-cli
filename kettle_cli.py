#!/usr/bin/env python3

import argparse
import sys

from kettle_control import PRESETS_C, KettleController, cli_json, normalize_preset_name


def build_parser():
    parser = argparse.ArgumentParser(
        description="Control the Stagg kettle from the command line."
    )
    parser.add_argument(
        "--subnet",
        default="192.168.1",
        help="Subnet prefix to scan, e.g. 192.168.1",
    )
    parser.add_argument(
        "--ip",
        default=None,
        help="Kettle IP address (skips LAN scan entirely)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("discover", help="Find the kettle IP on the LAN")
    subparsers.add_parser("state", help="Show the current kettle state")
    subparsers.add_parser("presets", help="List the built-in tea presets")
    subparsers.add_parser("off", help="Turn the kettle off")

    heat = subparsers.add_parser(
        "heat",
        help="Heat using a preset name or explicit temperature in Celsius",
    )
    heat.add_argument(
        "target",
        help="Preset name like green_tea, or a Celsius temperature like 69",
    )

    set_temp = subparsers.add_parser("set-temp", help="Set an explicit temperature in Celsius")
    set_temp.add_argument("temp_c", type=int)

    return parser


def main():
    parser = build_parser()
    argv = sys.argv[1:]
    json_anywhere = False
    if "--json" in argv:
        argv = [arg for arg in argv if arg != "--json"]
        json_anywhere = True

    args = parser.parse_args(argv)
    args.json = args.json or json_anywhere
    controller = KettleController(subnet=args.subnet, preferred_ip=args.ip)

    try:
        if args.command == "discover":
            ip = controller.find_kettle(force=True)
            if not ip:
                raise Exception("Kettle not found")
            result = {"ip": ip}
        elif args.command == "state":
            result = controller.state().to_api_dict()
        elif args.command == "presets":
            result = {"presets": PRESETS_C}
        elif args.command == "off":
            result = controller.turn_off()
        elif args.command == "set-temp":
            result = controller.set_temp_c(args.temp_c)
        elif args.command == "heat":
            target = args.target.strip()
            if target.isdigit():
                result = controller.set_temp_c(int(target))
            else:
                result = controller.set_preset(normalize_preset_name(target))
        else:
            parser.error(f"Unknown command: {args.command}")
            return 2

        if args.json:
            cli_json(result)
        elif isinstance(result, dict):
            status = result.get("status")
            if status:
                print(status)
            else:
                print(result)
        else:
            print(result)
        return 0
    except Exception as exc:
        if args.json:
            cli_json({"error": str(exc)})
        else:
            print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
