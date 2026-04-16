# Kettle Control

Command-line tool for the Fellow Stagg EKG+ (Wi-Fi) smart kettle. Talks to the
kettle directly over your LAN via its built-in HTTP `cli` endpoint — no cloud,
no account, no app.

## Requirements

- Python 3 (macOS/Linux ship with this)
- `curl` (macOS/Linux ship with this)
- The kettle powered on and connected to the same Wi-Fi/LAN

No pip packages needed. Pure stdlib.

> ⚠️ **The kettle is 2.4 GHz Wi-Fi only.** Your computer must be on the same
> subnet as the kettle. If your router exposes 2.4 GHz and 5 GHz as separate
> SSIDs on different subnets, connect your computer to the 2.4 GHz SSID when
> running this tool — otherwise LAN discovery will return "Kettle not found".

## Quick start

1. **Unzip** the package and `cd` into the folder:
   ```sh
   unzip kettle-control.zip
   cd kettle-control
   ```

2. **Make the wrapper executable** (one time):
   ```sh
   chmod +x kettle
   ```

3. **Find your LAN prefix.** On macOS:
   ```sh
   ipconfig getifaddr en0     # e.g. prints 192.168.1.42 → prefix is 192.168.1
   ```
   On Linux: `hostname -I | awk '{print $1}'` and drop the last octet.

4. **Discover the kettle** (one-time scan of 253 addresses, takes a few seconds):
   ```sh
   ./kettle --subnet 192.168.1 discover
   ```
   Replace `192.168.1` with your prefix from step 3. The found IP is cached to
   `~/.cache/kettle-control/ip` — every subsequent call is instant.

5. **Use it:**
   ```sh
   ./kettle state
   ./kettle heat green_tea
   ./kettle off
   ```

That's it. You only ever need `--subnet` on the very first run (or if the
kettle gets a new DHCP lease).

### Even faster: pin the IP

If you give the kettle a DHCP reservation in your router, or just want to skip
the cache entirely, pass `--ip` directly:

```sh
./kettle --ip 192.168.1.42 state
```

## Commands

```sh
./kettle discover                 # scan the LAN and print the kettle's IP
./kettle state                    # show current temp / mode
./kettle presets                  # list built-in tea presets
./kettle heat green_tea           # heat to a preset
./kettle heat 80                  # heat to 80 °C
./kettle set-temp 93              # same, explicit
./kettle off                      # turn off
./kettle --json state             # machine-readable output
```

### Global flags

- `--subnet X.Y.Z` — LAN prefix to scan if the cache is empty (default `192.168.1`)
- `--ip A.B.C.D` — talk directly to this IP, skip all discovery
- `--json` — print output as JSON

## Presets

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

## Why it's fast after the first call

The first `discover` writes the kettle's IP to `~/.cache/kettle-control/ip`.
Every later invocation reads that file and talks to the IP directly — no LAN
scan, no mDNS, instant response. If the kettle's IP changes, one command will
fail; just re-run `./kettle discover` to refresh the cache.

To reset: `rm ~/.cache/kettle-control/ip`.

## openclaw integration (optional)

This folder is also a ready-to-use openclaw skill. To wire it up:

```sh
mkdir -p ~/openclaw_skills
cp -R kettle-control ~/openclaw_skills/kettle_control
```

Now openclaw will load `SKILL.md` on next start and let the LLM heat your
kettle, check its state, etc. by voice or chat.

Paths in `SKILL.md` assume the install location above — adjust them if you put
the folder elsewhere.

## Files

- `kettle` — zsh wrapper that runs the CLI with system `python3`
- `kettle_cli.py` — argparse CLI
- `kettle_control.py` — controller + LAN discovery + HTTP client + disk cache
- `SKILL.md` — openclaw skill manifest (only needed if you use openclaw)

## Notes

The kettle exposes an unauthenticated HTTP endpoint on your LAN. Anyone on the
same network can control it. Keep it on a trusted network.
