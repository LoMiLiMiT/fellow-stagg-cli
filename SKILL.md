---
name: kettle_control
description: Control the Fellow Stagg EKG+ smart kettle over the local network. Use when the user wants to check kettle temperature, heat water to a specific temperature or tea preset (green tea, white tea, oolong, coffee, black tea, rooibos, herbal, boiling), or turn the kettle off.
metadata:
  openclaw:
    os: [darwin, linux]
    requires:
      bins: [python3, curl]
---

# Kettle Control

Use this skill when the user wants to check or control the Fellow Stagg EKG+
smart kettle on the local network.

Primary interface:
`~/openclaw_skills/kettle_control/kettle`

Always use the `exec` tool and always pass `--json` for machine-readable output.

## Check state

Current temperature, target, and mode:
`~/openclaw_skills/kettle_control/kettle state --json`

## Heat

Heat to a preset (green_tea, white_tea, oolong, coffee, black_tea, rooibos, herbal, boil):
`~/openclaw_skills/kettle_control/kettle heat green_tea --json`
`~/openclaw_skills/kettle_control/kettle heat coffee --json`

Heat to an explicit Celsius temperature:
`~/openclaw_skills/kettle_control/kettle heat 85 --json`
`~/openclaw_skills/kettle_control/kettle set-temp 85 --json`

## Turn off

`~/openclaw_skills/kettle_control/kettle off --json`

## List presets

`~/openclaw_skills/kettle_control/kettle presets --json`

## Discover (first-time only)

If no cached kettle IP exists yet, scan the LAN once (takes a few seconds):
`~/openclaw_skills/kettle_control/kettle --subnet 192.168.1 discover --json`

Replace `192.168.1` with the user's LAN prefix. Not needed on later calls — the
IP is cached at `~/.cache/kettle-control/ip` and reused instantly.

## Presets reference

| preset     | °C  |
|------------|-----|
| green_tea  | 69  |
| white_tea  | 80  |
| oolong     | 85  |
| coffee     | 93  |
| black_tea  | 96  |
| rooibos    | 100 |
| herbal     | 100 |
| boil       | 100 |

## Response handling

Summarize the returned JSON for the user — current temperature, target
temperature, and mode (Heat / Hold / Idle / Off).

If a command fails with `Kettle not found`, suggest:

1. The kettle may be off the base or its Wi-Fi module is asleep — place the
   kettle on the base and wait ~30 s.
2. The kettle is 2.4 GHz Wi-Fi only — confirm the computer is on the same
   2.4 GHz SSID and subnet.
3. Re-run discovery: `kettle --subnet <prefix> discover --json`.

For `heat` commands, confirm the target temperature in the summary so the user
knows the kettle accepted the request.
