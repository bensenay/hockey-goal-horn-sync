"""
╔══════════════════════════════════════════════════════╗
║       🏒  CANADIENS GOAL HORN  🔴⚪🔵                 ║
║   Real-time goal detection + Bluetooth audio/lights  ║
╚══════════════════════════════════════════════════════╝

SETUP INSTRUCTIONS
──────────────────
1. Install dependencies:
       pip install requests pygame

2. Put your goal horn audio file in the same folder as this script.
   Rename it to "canadiens_horn.mp3" (or update HORN_FILE below).
   Search: "Montreal Canadiens goal horn mp3"

3. Pair your Bluetooth speaker and set it as Windows/Mac DEFAULT audio output.
   pygame plays through whatever your system default is — no extra config needed.

4. Configure the settings below (CONFIGURATION section).

5. Run:
       python canadiens_goal_horn_FINAL.py

GOVEE SETUP (pick one option)
──────────────────────────────
Option A — LAN Control (faster, recommended):
  - Open Govee Home app → your strip → Settings (gear) → enable "LAN Control"
  - Find your strip's local IP in your router's device list
  - Paste it into GOVEE_IP below

Option B — Cloud API (all devices):
  - Open Govee Home app → Profile → About Us → Apply for API Key
  - Get device ID by calling: https://developer-api.govee.com/v1/devices
    with header "Govee-API-Key: YOUR_KEY"
  - Fill in GOVEE_API_KEY, GOVEE_DEVICE_ID, GOVEE_MODEL below

TV DELAY CALIBRATION
─────────────────────
Run with LOG_ONLY_MODE = True to measure your exact TV delay:
  1. Start the script during a live game
  2. When a goal is scored, press ENTER the moment you see it on your TV
  3. Script calculates and displays your measured delay
  4. After 2-3 goals, set TV_DELAY_SECONDS to the average shown
  5. Set LOG_ONLY_MODE = False and enjoy!

COLORS
─────────────────────
THIS WAS DESIGNED FOR MONTREAL CANADIENS FANS. You can change the RGB values below to match your favorite team or personal preference.
SEE otherteams.txt for other nhl teams

  
  Disclaimer: This script is for personal use only. It is not affiliated with the NHL, Govee, or the Montreal Canadiens. Use at your own risk.

"""

import argparse
import requests
import time
import json
import socket
import threading
from datetime import datetime

# ─────────────────────────────────────────────────────
#  CONFIGURATION  —  Edit these values before running
# ─────────────────────────────────────────────────────

TV_DELAY_SECONDS = 0           # Bell Fibe is typically ~8-10s behind API, but varies. Calibrate to your setup.
HORN_FILE        = "canadiens_horn.mp3"   # Audio file in same folder as this script
LOG_ONLY_MODE    = False       # Set True to calibrate delay without triggering horn/lights

# — Govee LAN (Option A, faster) —
GOVEE_IP   = ""               # e.g. "192.168.1.105"  — leave blank to use Cloud API
GOVEE_PORT = 4003

# — Govee Cloud API (Option B) —
GOVEE_API_KEY   = ""          # Your Govee API key
GOVEE_DEVICE_ID = ""          # Your device ID  e.g. "AB:CD:EF:..."
GOVEE_MODEL     = ""          # Your model      e.g. "H619B"

# — Light colors —
HABS_RED     = {"r": 200, "g": 0,   "b": 20}   # Deep Canadiens red
HABS_WHITE   = {"r": 255, "g": 255, "b": 255}
HABS_BLUE    = {"r": 25,  "g": 33,  "b": 104}  # Optional accent
NORMAL_COLOR = {"r": 220, "g": 95,  "b": 20}   # Warm orange-red — your default ambiance

# ─────────────────────────────────────────────────────
#  AUDIO SETUP
# ─────────────────────────────────────────────────────

try:
    import pygame
    pygame.mixer.init()
    AUDIO_READY = True
except ImportError:
    AUDIO_READY = False
    print("⚠️  pygame not found. Run: pip install pygame")

HORN_MAX_SECONDS = 45   # Stop playback after this many seconds

def play_horn():
    """Play the goal horn through the system default audio output (your BT speaker).
    Playback is automatically stopped after HORN_MAX_SECONDS seconds."""
    if LOG_ONLY_MODE:
        print("   [LOG MODE] Horn would play here.")
        return
    if not AUDIO_READY:
        print("   ⚠️  Audio skipped — pygame not installed.")
        return
    try:
        pygame.mixer.music.load(HORN_FILE)
        pygame.mixer.music.play()
        print(f"   🎺 Horn playing! (auto-stop after {HORN_MAX_SECONDS}s)")

        def _stop_after_limit():
            time.sleep(HORN_MAX_SECONDS)
            pygame.mixer.music.stop()

        threading.Thread(target=_stop_after_limit, daemon=True).start()
    except Exception as e:
        print(f"   ⚠️  Audio error: {e}")
        print(f"   Make sure '{HORN_FILE}' exists in the same folder as this script.")

# ─────────────────────────────────────────────────────
#  GOVEE LIGHTS
# ─────────────────────────────────────────────────────

def _govee_lan(color):
    """Send color command via local UDP (fast, ~50ms)."""
    cmd = {
        "msg": {
            "cmd": "colorwc",
            "data": {
                "color": color,
                "colorTemInKelvin": 0
            }
        }
    }
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        sock.sendto(json.dumps(cmd).encode(), (GOVEE_IP, GOVEE_PORT))
        sock.close()
    except Exception as e:
        print(f"   ⚠️  Govee LAN error: {e}")

def _govee_cloud(color):
    """Send color command via Govee cloud REST API."""
    url = "https://developer-api.govee.com/v1/devices/control"
    headers = {
        "Govee-API-Key": GOVEE_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "device": GOVEE_DEVICE_ID,
        "model":  GOVEE_MODEL,
        "cmd": {
            "name":  "color",
            "value": color
        }
    }
    try:
        requests.put(url, headers=headers, json=payload, timeout=5)
    except Exception as e:
        print(f"   ⚠️  Govee Cloud error: {e}")

def set_color(color):
    """Use LAN if IP is configured, otherwise fall back to cloud API."""
    if GOVEE_IP:
        _govee_lan(color)
    elif GOVEE_API_KEY and GOVEE_DEVICE_ID:
        _govee_cloud(color)

def goal_lights():
    """
    Full goal celebration light sequence — runs in a background thread.

    Sequence:
      • Rapid red ↔ white flashes at 150 ms each for ~10 s
      • Hold solid Habs red for 12 seconds
      • Return to your normal color
    """
    if LOG_ONLY_MODE:
        print("   [LOG MODE] Lights would flash here.")
        return
    if not GOVEE_IP and not GOVEE_API_KEY:
        print("   ℹ️  Govee not configured — skipping lights.")
        return

    def _sequence():
        # Rapid-flash phase (~10 seconds, 150 ms per colour = ~33 cycles)
        flash_end = time.time() + 10
        toggle = True
        while time.time() < flash_end:
            set_color(HABS_RED if toggle else HABS_WHITE)
            toggle = not toggle
            time.sleep(0.15)
        # Hold red
        set_color(HABS_RED)
        time.sleep(12)
        # Return to normal
        set_color(NORMAL_COLOR)

    t = threading.Thread(target=_sequence, daemon=True)
    t.start()

# ─────────────────────────────────────────────────────
#  NHL API
# ─────────────────────────────────────────────────────

NHL_BASE   = "https://api-web.nhle.com/v1"
MTL_ABBREV = "MTL"

def get_todays_game(team_abbrev):
    """
    Fetch today's NHL schedule and find the monitored team's game.
    Returns (game_id, home_abbrev, away_abbrev) or (None, None, None).
    """
    url = f"{NHL_BASE}/schedule/now"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        for day in data.get("gameWeek", []):
            for game in day.get("games", []):
                home = game.get("homeTeam", {}).get("abbrev", "")
                away = game.get("awayTeam", {}).get("abbrev", "")
                if team_abbrev in (home, away):
                    gid   = game["id"]
                    state = game.get("gameState", "")
                    start = game.get("startTimeUTC", "")
                    print(f"   Found: {away} @ {home}  |  ID: {gid}  |  State: {state}  |  Start: {start}")
                    return gid, home, away

    except Exception as e:
        print(f"   ⚠️  Schedule fetch error: {e}")

    return None, None, None

def get_live_goals(game_id):
    """
    Fetch play-by-play data and extract all GOAL events.
    Uses play-by-play endpoint for faster goal detection than score polling.
    Returns (home_abbrev, away_abbrev, [goal_event_ids], game_state, period) or (None,…) on error.
    """
    url = f"{NHL_BASE}/gamecenter/{game_id}/play-by-play"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()

        home = data.get("homeTeam", {}).get("abbrev", "")
        away = data.get("awayTeam", {}).get("abbrev", "")
        state = data.get("gameState", "UNKNOWN")
        period = data.get("periodDescriptor", {}).get("number", 0)
        
        goal_ids = []
        for play in data.get("plays", []):
            if play.get("typeDescKey") == "goal":
                goal_ids.append(play["eventId"])
        
        return home, away, goal_ids, state, period

    except Exception as e:
        print(f"\n   ⚠️  Play-by-play fetch error: {e}")
        return None, None, None, None, None

# ─────────────────────────────────────────────────────
#  DISPLAY HELPERS
# ─────────────────────────────────────────────────────

PERIOD_LABELS = {1: "1st", 2: "2nd", 3: "3rd", 4: "OT", 5: "SO"}

def print_status(home_score, away_score, home_ab, away_ab, state, period, last_check):
    period_str = PERIOD_LABELS.get(period, f"P{period}") if period else "Pre-game"
    bar = f"{home_ab} {home_score}  –  {away_score} {away_ab}"
    print(f"\r  [{last_check}]  {bar}  |  {state} {period_str}      ", end="", flush=True)

def print_banner():
    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║       🏒  CANADIENS GOAL HORN  🔴⚪🔵               ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  TV delay offset : {TV_DELAY_SECONDS} sec                              ║")
    govee_status = f"LAN ({GOVEE_IP})" if GOVEE_IP else ("Cloud API" if GOVEE_API_KEY else "Not configured")
    audio_status = "pygame ready ✅" if AUDIO_READY else "pygame missing ❌"
    mode_str     = "⚠️  CALIBRATION / LOG ONLY" if LOG_ONLY_MODE else "🎯 LIVE — horn + lights ON"
    print(f"║  Govee           : {govee_status:<34}║")
    print(f"║  Audio           : {audio_status:<34}║")
    print(f"║  Mode            : {mode_str:<34}║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

# ─────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NHL goal horn + Govee lights")
    parser.add_argument(
        "--team", default=MTL_ABBREV, metavar="ABBREV",
        help="Three-letter team abbreviation to monitor (default: MTL). "
             "Example: --team EDM"
    )
    args = parser.parse_args()
    team_abbrev = args.team.upper()

    print_banner()

    print(f"🔍 Searching for today's {team_abbrev} game...")
    game_id, home, away = get_todays_game(team_abbrev)

    if not game_id:
        print(f"\n❌ No {team_abbrev} game found today.")
        print("   The NHL API returns today's date — check back on a game day!")
        return

    opp_abbrev = away if home == team_abbrev else home
    print(f"\n✅ Monitoring: {team_abbrev} vs {opp_abbrev}")
    print("   (Tracking goals by either team)\n")
    if LOG_ONLY_MODE:
        print("⚠️  LOG ONLY MODE — press ENTER when you see a goal on your TV")
        print("   to measure the exact TV delay.\n")

    seen_event_ids = set()
    delay_measurements = []
    consecutive_errors = 0

    while True:
        home_ab, away_ab, goal_ids, state, period = get_live_goals(game_id)

        if home_ab is None:
            consecutive_errors += 1
            if consecutive_errors >= 5:
                print(f"\n   ⚠️  5 consecutive fetch errors. Retrying in 30s...")
                time.sleep(30)
                consecutive_errors = 0
            else:
                time.sleep(2)
            continue

        consecutive_errors = 0
        
        # Map team abbreviations to their actual score
        # For now we just detect new goal events
        new_goals = [gid for gid in goal_ids if gid not in seen_event_ids]
        
        now = datetime.now().strftime("%H:%M:%S")
        
        # Determine current scores by counting goals per team (simplified)
        # In a real scenario you'd parse the play-by-play to get scorer info
        home_score = len([g for g in goal_ids])  # This is a simplification
        away_score = 0  # For full accuracy, you'd need to parse which team scored
        
        print_status(home_score, away_score, home_ab, away_ab, state, period, now)

        # First successful fetch — set baseline
        if not seen_event_ids:
            seen_event_ids = set(goal_ids)
            print(f"\n📊 Baseline set. Watching for goals from {home_ab} and {away_ab}...")
            print("   Tracking play-by-play events...\n")

        # ── GOAL DETECTED ──────────────────────────────────────
        for goal_id in new_goals:
            api_time = datetime.now()
            print(f"\n\n🚨🚨  GOAL!  🚨🚨")
            print(f"   API detected at : {api_time.strftime('%H:%M:%S.%f')[:-3]}")
            
            if LOG_ONLY_MODE:
                print("   Press ENTER the moment you see the goal on your TV...")
                input()
                measured = (datetime.now() - api_time).total_seconds()
                print(f"   TV delay measured: {measured:.1f} seconds")
                delay_measurements.append(measured)
                avg = sum(delay_measurements) / len(delay_measurements)
                n = len(delay_measurements)
                print(f"   Average over {n} goal{'s' if n != 1 else ''}: {avg:.1f}s → recommended TV_DELAY_SECONDS = {round(avg)}")
            else:
                if TV_DELAY_SECONDS > 0:
                    print(f"   Waiting {TV_DELAY_SECONDS}s for Bell Fibe TV sync...")
                    time.sleep(TV_DELAY_SECONDS)
                print(f"   Triggering now  : {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
                play_horn()
                goal_lights()
            
            seen_event_ids.add(goal_id)
            print()  # blank line before resuming status

        # ── GAME OVER ──────────────────────────────────────────
        if state in ("FINAL", "OFF"):
            print(f"\n\n🏁 Game over!")
            print("   Thanks for watching. Allez Montréal! 🔴⚪🔵\n")
            break

        time.sleep(1)   # Poll NHL API every 1 second for faster goal detection

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Stopped. Allez Montréal!")