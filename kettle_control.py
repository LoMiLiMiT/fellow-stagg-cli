#!/usr/bin/env python3

import json
import os
import subprocess
import threading
import time
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

DEFAULT_CACHE_PATH = os.path.expanduser("~/.cache/kettle-control/ip")

PRESETS_C = {
    "green_tea": 69,
    "white_tea": 80,
    "oolong": 85,
    "coffee": 93,
    "black_tea": 96,
    "rooibos": 100,
    "herbal": 100,
    "boil": 100,
}

PRESET_ALIASES = {
    "green": "green_tea",
    "white": "white_tea",
    "black": "black_tea",
    "herbal_tea": "herbal",
    "boiling": "boil",
}


def normalize_preset_name(name):
    key = name.strip().lower().replace(" ", "_").replace("-", "_")
    return PRESET_ALIASES.get(key, key)


@dataclass
class KettleState:
    raw: dict

    @property
    def temp(self):
        return float(self.raw.get("temp", self.raw.get("tempr", 0)) or 0)

    @property
    def target(self):
        return float(self.raw.get("target", self.raw.get("temprT", 0)) or 0)

    @property
    def mode(self):
        return self.raw.get("mode", "Off")

    @property
    def units(self):
        raw_units = str(self.raw.get("units", "1")).strip()
        if raw_units in {"1", "C", "c"}:
            return "C"
        return "F"

    @property
    def is_heating(self):
        return self.mode in {"Heat", "S_Heat"}

    @property
    def is_holding(self):
        return self.mode in {"Hold", "S_Hold"}

    @property
    def is_off(self):
        return self.mode in {"Off", "S_Off"}

    @property
    def is_idle(self):
        return self.mode in {"Idle", "S_Idle"}

    @property
    def is_active(self):
        return self.is_heating or self.is_holding

    def to_api_dict(self):
        payload = dict(self.raw)
        payload["temp"] = payload.get("temp", f"{self.temp}")
        payload["target"] = payload.get("target", f"{self.target}")
        payload["mode"] = self.mode
        payload["units"] = self.units
        return payload


class KettleController:
    def __init__(
        self,
        subnet="192.168.1",
        preferred_ip=None,
        probe_timeout=2,
        command_timeout=12,
        cache_path=DEFAULT_CACHE_PATH,
    ):
        self.subnet = subnet
        self.preferred_ip = preferred_ip
        self.probe_timeout = float(probe_timeout)
        self.command_timeout = float(command_timeout)
        self.cache_path = cache_path
        self._cache = {"ip": self._load_ip_from_disk(), "expires": 0}
        self._lock = threading.Lock()

    def _load_ip_from_disk(self):
        if not self.cache_path:
            return None
        try:
            with open(self.cache_path) as f:
                ip = f.read().strip()
            return ip or None
        except OSError:
            return None

    def _save_ip_to_disk(self, ip):
        if not self.cache_path or not ip:
            return
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w") as f:
                f.write(ip)
        except OSError:
            pass

    def _remember(self, ip):
        self._cache["ip"] = ip
        self._cache["expires"] = time.time() + 300
        self._save_ip_to_disk(ip)

    def _probe_ip(self, ip, timeout=None):
        timeout = self.probe_timeout if timeout is None else timeout
        try:
            body = self._send(ip, "state", timeout=timeout)
            if "tempr=" in body:
                return ip
        except Exception:
            pass
        return None

    def _send(self, ip, cmd, timeout=None):
        timeout = self.command_timeout if timeout is None else timeout
        url = f"http://{ip}/cli?cmd={quote_plus(cmd)}"
        result = subprocess.run(
            ["curl", "-fsS", "--max-time", str(timeout), url],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise Exception(result.stderr.strip() or result.stdout.strip() or "curl failed")
        return result.stdout

    def find_kettle(self, force=False):
        with self._lock:
            now = time.time()
            if not force and self._cache["ip"] and now < self._cache["expires"]:
                return self._cache["ip"]
            cached_ip = self._cache["ip"]

        if cached_ip:
            result = self._probe_ip(cached_ip)
            if result:
                with self._lock:
                    self._remember(result)
                return result

        if self.preferred_ip:
            result = self._probe_ip(self.preferred_ip)
            if result:
                with self._lock:
                    self._remember(result)
                return result

        with ThreadPoolExecutor(max_workers=50) as pool:
            futures = [
                pool.submit(self._probe_ip, f"{self.subnet}.{i}")
                for i in range(2, 255)
            ]
            for future in futures:
                result = future.result()
                if result:
                    with self._lock:
                        self._remember(result)
                    return result
        return None

    def cmd(self, cmd, timeout=None):
        timeout = self.command_timeout if timeout is None else timeout
        candidates = []
        with self._lock:
            if self._cache["ip"]:
                candidates.append(self._cache["ip"])
        if self.preferred_ip and self.preferred_ip not in candidates:
            candidates.append(self.preferred_ip)

        last_error = None
        for ip in candidates:
            try:
                body = self._send(ip, cmd, timeout=timeout)
                with self._lock:
                    self._remember(ip)
                return body
            except Exception as exc:
                last_error = exc

        ip = self.find_kettle()
        if not ip:
            raise Exception("Kettle not found on network")
        try:
            return self._send(ip, cmd, timeout=timeout)
        except Exception as exc:
            if last_error is not None:
                raise Exception(str(exc))
            raise

    def parse_state(self, raw):
        parsed = {}
        for line in raw.splitlines():
            stripped = line.strip()
            if "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            value = value.strip()
            parsed[key] = value
            if key == "tempr":
                parsed["temp"] = value.split(" ")[0]
            elif key == "temprT":
                parsed["target"] = value.split(" ")[0]
            elif key == "units":
                parsed["units"] = "C" if value.endswith("1") else "F"
        return KettleState(parsed)

    def state(self, timeout=None):
        return self.parse_state(self.cmd("state", timeout=timeout))

    def set_temp_c(self, temp_c):
        temp_c = int(temp_c)
        temp_f = round(temp_c * 9 / 5 + 32)
        self.cmd(f"setsetting settempr {temp_f}")
        self.cmd("ss S_Heat")
        self.cmd("heaton")
        return {
            "status": f"Set to {temp_c}°C ({temp_f}°F) and heating",
            "temp_c": temp_c,
            "temp_f": temp_f,
        }

    def turn_off(self):
        self.cmd("heatoff")
        self.cmd("ss S_Off")
        return {"status": "Kettle off"}

    def set_preset(self, preset_name):
        normalized = normalize_preset_name(preset_name)
        if normalized not in PRESETS_C:
            raise KeyError(f"Unknown preset: {preset_name}")
        return self.set_temp_c(PRESETS_C[normalized])


class KettleLiftMonitor:
    def __init__(
        self,
        controller,
        timer_seconds=120,
        poll_interval=2,
        on_lift=None,
        cooldown_seconds=90,
    ):
        self.controller = controller
        self.timer_seconds = int(timer_seconds)
        self.poll_interval = poll_interval
        self.on_lift = on_lift
        self.cooldown_seconds = cooldown_seconds

        self.last_state = None
        self.last_error = None
        self.last_polled_at = 0
        self.last_lift_at = 0
        self.last_lift_reason = None

        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()

    def _should_trigger_lift(self, previous, current):
        if previous is None or current is None:
            return None

        # Best-effort heuristic:
        # if the kettle was active/hot and transitions to idle/off while still hot,
        # it likely got lifted from the base for pouring.
        if previous.is_active and not current.is_active:
            hot_enough = max(previous.temp, current.temp) >= max(previous.target - 5, 70)
            if hot_enough:
                return "active_to_inactive_hot"

        if previous.is_holding and current.is_off and current.temp >= 70:
            return "hold_to_off_hot"

        return None

    def poll_once(self):
        now = time.time()
        previous = self.last_state
        try:
            current = self.controller.state()
            self.last_state = current
            self.last_error = None
        except Exception as exc:
            self.last_error = str(exc)
            current = None

        self.last_polled_at = now
        reason = self._should_trigger_lift(previous, current)
        if reason and now - self.last_lift_at >= self.cooldown_seconds:
            self.last_lift_at = now
            self.last_lift_reason = reason
            if self.on_lift:
                self.on_lift(
                    {
                        "started_at": now,
                        "seconds": self.timer_seconds,
                        "reason": reason,
                        "previous": previous.to_api_dict() if previous else None,
                        "current": current.to_api_dict() if current else None,
                    }
                )
        return current

    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self):
        self._stop.set()

    def _run(self):
        while not self._stop.is_set():
            self.poll_once()
            self._stop.wait(self.poll_interval)

    def status(self):
        state = self.last_state.to_api_dict() if self.last_state else None
        return {
            "running": bool(self._thread and self._thread.is_alive()),
            "last_polled_at": self.last_polled_at,
            "last_error": self.last_error,
            "last_lift_at": self.last_lift_at,
            "last_lift_reason": self.last_lift_reason,
            "timer_seconds": self.timer_seconds,
            "last_state": state,
        }


def cli_json(data):
    print(json.dumps(data, indent=2, sort_keys=True))
