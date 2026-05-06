# -*- coding: utf-8 -*-
"""
NIFTY AUTO TRADER — FULLY AUTOMATIC
=====================================
- Sab kuch Angel One API se live
- Koi JSON file nahi
- Token auto-refresh (Future monthly, Option weekly)
- Volume: Nifty Future se real volume
- Backtest: Historical data Angel API se
- Paper + Live trading
- Sirf conditions change karne ka option

Setup:
    pip install pyotp requests pandas numpy reportlab gtts pyttsx3 smartapi-python

Run:
    python main_consolidated.py
"""

# ═══════════════════════════════════════════════════════════════════
#  SSL CERTIFICATE FIX FOR macOS
# ═══════════════════════════════════════════════════════════════════
import os
import ssl
import warnings

# Disable SSL warnings
warnings.filterwarnings('ignore')
os.environ['PYTHONHTTPSVERIFY'] = '0'
ssl._create_default_https_context = ssl._create_unverified_context

# Disable urllib3 warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Monkey patch requests to disable SSL verification globally
import requests
_original_request = requests.Session.request
_original_get = requests.get
_original_post = requests.post

def patched_request(self, method, url, **kwargs):
    kwargs['verify'] = False
    return _original_request(self, method, url, **kwargs)

def patched_get(url, **kwargs):
    kwargs['verify'] = False
    return _original_get(url, **kwargs)

def patched_post(url, **kwargs):
    kwargs['verify'] = False
    return _original_post(url, **kwargs)

requests.Session.request = patched_request
requests.get = patched_get
requests.post = patched_post

# ═══════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading, datetime, time, json, os, logging, io, re
import requests, pyotp
import pandas as pd
import numpy as np
from SmartApi import SmartConnect
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

try:
    from gtts import gTTS
    GTTS_OK = True
except:
    GTTS_OK = False

try:
    import pyttsx3
    _tts = pyttsx3.init()
    PYTTSX_OK = True
except:
    PYTTSX_OK = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[logging.FileHandler('trader.log', encoding='utf-8')]
)
logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════
#  CONFIG — sirf yahan se sab kuch control hoga
# ═══════════════════════════════════════════════════════
CFG = {
    # Angel One credentials
    "API_KEY":    "x9Zs2hWZ",
    "CLIENT_ID":  "J109737",
    "PASSWORD":   "4966",
    "TOTP":       "HDVHUMXPPC2FTJOSHKSK6CO5AA",
    # Telegram
    "BOT_TOKEN":  "8665264906:AAFJD6a08qPbw0RvLQWNL7YF6624PcSgN-w",
    "CHAT_ID":    "8748890897",
    # Trading conditions (GUI se change honge)
    "SYMBOL":     "NIFTY 50",
    "MODE":       "paper",       # paper | live | backtest
    "EMA_FAST":   9,
    "EMA_SLOW":   21,
    "EMA_GAP":    2,             # minimum EMA gap (points)
    "VOL_PERIOD": 20,            # volume average period
    "VOL_MULT":   1.2,           # volume multiplier
    "INTERVAL":   "FIVE_MINUTE",
    "DAYS":       30,            # backtest days
    "SL_PTS":     30,            # stop loss (option points)
    "TSL_PTS":    20,            # trailing SL (option points)
    "TGT_PTS":    60,            # target (option points)
    "LOT_SIZE":   50,
    "BOTH_SIDE":  True,
    "PAPER_CAP":  100000,
    "VOICE":      True,
}

# ═══════════════════════════════════════════════════════
#  INSTRUMENTS
# ═══════════════════════════════════════════════════════
INSTRUMENTS = {
    "NIFTY 50":  {"spot_token":"99926000","exchange":"NSE","lot":50, "sg":50},
    "BANKNIFTY": {"spot_token":"99926009","exchange":"NSE","lot":15, "sg":100},
    "FINNIFTY":  {"spot_token":"99926037","exchange":"NSE","lot":40, "sg":50},
    "MIDCPNIFTY":{"spot_token":"99926074","exchange":"NSE","lot":75, "sg":25},
    "RELIANCE":  {"spot_token":"2885",    "exchange":"NSE","lot":250,"sg":20},
    "TCS":       {"spot_token":"11536",   "exchange":"NSE","lot":150,"sg":50},
    "HDFCBANK":  {"spot_token":"1333",    "exchange":"NSE","lot":550,"sg":10},
    "INFY":      {"spot_token":"1594",    "exchange":"NSE","lot":300,"sg":20},
    "ICICIBANK": {"spot_token":"4963",    "exchange":"NSE","lot":700,"sg":10},
    "SBIN":      {"spot_token":"3045",    "exchange":"NSE","lot":1500,"sg":5},
    "WIPRO":     {"spot_token":"3787",    "exchange":"NSE","lot":1500,"sg":5},
    "TATAMOTORS":{"spot_token":"3456",    "exchange":"NSE","lot":1425,"sg":5},
    "BAJFINANCE":{"spot_token":"317",     "exchange":"NSE","lot":125,"sg":50},
    "MARUTI":    {"spot_token":"10999",   "exchange":"NSE","lot":25, "sg":100},
    "HCLTECH":   {"spot_token":"7229",    "exchange":"NSE","lot":350,"sg":10},
}

# Nifty indices ka future exchange
INDEX_SYMS = {"NIFTY 50","BANKNIFTY","FINNIFTY","MIDCPNIFTY"}

EXCLUDE_NIFTY = [
    "BANKNIFTY","FINNIFTY","MIDCPNIFTY","NIFTYNXT",
    "NIFTY50USD","NIFTYIT","NIFTYMID","NIFTYAUTO",
    "NIFTYBEES","NIFTYBANK","NIFTYPSE"
]

# ═══════════════════════════════════════════════════════
#  STATE
# ═══════════════════════════════════════════════════════
class ST:
    running    = False
    api        = None
    trades     = []
    positions  = []
    signals    = []
    balance    = CFG["PAPER_CAP"]
    last_sig   = None
    mode       = "paper"
    fut_tokens = {}    # auto-refreshed future tokens
    opt_tokens = {}    # auto-refreshed option tokens
    last_token_refresh = None

ST_FILE = "state.json"

def save_state():
    json.dump({
        "trades":   ST.trades[-200:],
        "positions":ST.positions,
        "balance":  ST.balance,
    }, open(ST_FILE,"w",encoding="utf-8"), indent=2, default=str)

def load_state():
    if os.path.exists(ST_FILE):
        try:
            d = json.load(open(ST_FILE,encoding="utf-8"))
            ST.trades    = d.get("trades",   [])
            ST.positions = d.get("positions",[])
            ST.balance   = d.get("balance",  CFG["PAPER_CAP"])
        except: pass

load_state()

# ═══════════════════════════════════════════════════════
#  ANGEL ONE — LOGIN + DATA
# ═══════════════════════════════════════════════════════
def angel_login():
    try:
        totp = pyotp.TOTP(CFG["TOTP"]).now()
        s    = SmartConnect(api_key=CFG["API_KEY"])
        d    = s.generateSession(CFG["CLIENT_ID"], CFG["PASSWORD"], totp)
        if d["status"]:
            ST.api = s
            logger.info("Angel One login OK")
            return True
        logger.error(f"Login failed: {d['message']}")
        return False
    except Exception as e:
        logger.error(f"Login error: {e}")
        return False

def get_ltp(token, exchange):
    try:
        return float(ST.api.ltpData(exchange,"",token)["data"]["ltp"])
    except: return None

def fetch_candles(token, exchange, interval, days, name=""):
    """Angel API se historical OHLCV data fetch karo."""
    to  = datetime.datetime.now()
    frm = to - datetime.timedelta(days=days)
    try:
        r = ST.api.getCandleData({
            "exchange":    exchange,
            "symboltoken": token,
            "interval":    interval,
            "fromdate":    frm.strftime("%Y-%m-%d %H:%M"),
            "todate":      to.strftime("%Y-%m-%d %H:%M"),
        })
        if r["status"] and r["data"]:
            df = pd.DataFrame(r["data"],
                 columns=["dt","open","high","low","close","volume"])
            df["dt"] = pd.to_datetime(df["dt"])
            df = df.set_index("dt").sort_index()
            for c in ["open","high","low","close","volume"]:
                df[c] = pd.to_numeric(df[c])
            logger.info(f"Fetched {len(df)} candles: {name}")
            return df
    except Exception as e:
        logger.error(f"Fetch {name}: {e}")
    return pd.DataFrame()

# ═══════════════════════════════════════════════════════
#  TOKEN MANAGER — AUTO REFRESH
#  Future: monthly | Option: weekly
# ═══════════════════════════════════════════════════════
def get_weekly_expiry():
    """
    Current active weekly expiry ka Thursday do.
    Agar aaj Thursday hai aur market band ho gayi (3:30 ke baad)
    toh next Thursday do — kyunki purane tokens expire ho gaye.
    """
    now   = datetime.datetime.now()
    today = now.date()
    d     = (3 - today.weekday()) % 7  # days to Thursday
    exp   = today + datetime.timedelta(days=d)

    # Agar aaj Thursday hai
    if d == 0:
        # 3:30 PM ke baad next week ka expiry use karo
        market_close = now.replace(hour=15, minute=30, second=0)
        if now >= market_close:
            exp += datetime.timedelta(days=7)

    if exp < today:
        exp += datetime.timedelta(days=7)
    return exp

def start_token_auto_refresh():
    """
    Background thread — har din subah 9:00 baje tokens auto-refresh karo.
    Thursday ke baad next week ke tokens automatically fetch honge.
    Koi manual kaam nahi!
    """
    def _loop():
        while True:
            try:
                now      = datetime.datetime.now()
                today    = now.date()
                week_exp = get_weekly_expiry()

                # Refresh kab karna hai?
                # 1. Subah 9:00-9:05 ke beech (market open se pehle)
                # 2. Thursday 3:30 ke baad (expiry ke baad)
                morning_refresh = (
                    now.hour == 9 and now.minute < 5 and
                    (ST.last_token_refresh is None or
                     ST.last_token_refresh.date() < today)
                )
                expiry_refresh = (
                    today.weekday() == 3 and  # Thursday
                    now.hour >= 15 and now.minute >= 31 and
                    ST.last_token_refresh is not None and
                    ST.last_token_refresh.date() == today and
                    ST.last_token_refresh.hour < 15
                )

                if morning_refresh or expiry_refresh:
                    reason = "Morning refresh" if morning_refresh else "Post-expiry refresh"
                    logger.info(f"Auto token refresh: {reason}")
                    if ST.api:
                        refresh_tokens(force=True)
                    else:
                        logger.warning("Auto refresh: API not connected yet")

            except Exception as e:
                logger.error(f"Auto refresh loop: {e}")

            time.sleep(60)  # Har 1 minute check karo

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    logger.info("Token auto-refresh thread started")

def get_monthly_expiry():
    """Is mahine ka last Thursday."""
    today = datetime.date.today()
    if today.month == 12:
        nm = datetime.date(today.year+1, 1, 1)
    else:
        nm = datetime.date(today.year, today.month+1, 1)
    ld = nm - datetime.timedelta(days=1)
    while ld.weekday() != 3:
        ld -= datetime.timedelta(days=1)
    return ld

def parse_expiry(s):
    for fmt in ["%d%b%Y","%Y-%m-%d","%d-%m-%Y"]:
        try: return datetime.datetime.strptime(str(s)[:9].upper(), fmt).date()
        except: pass
    return None

def refresh_tokens(log_fn=None, force=False):
    """
    Angel One API se LIVE token master download karke
    Future aur Option tokens auto-refresh karo.

    Auto-refresh logic:
    - App start: hamesha refresh
    - Har din: subah 9:00 baje refresh
    - Thursday expiry ke baad: next week ka token auto-lo
    - force=True: manually force refresh
    """
    def _log(msg):
        logger.info(msg)
        if log_fn: log_fn(msg, "info")

    # Check: refresh zaroor hai?
    now      = datetime.datetime.now()
    today    = now.date()
    week_exp = get_weekly_expiry()

    # Refresh conditions:
    # 1. force=True
    # 2. Pehli baar (last_token_refresh = None)
    # 3. Aaj refresh nahi hua
    # 4. Expiry aa gayi (Thursday)
    need_refresh = (
        force or
        ST.last_token_refresh is None or
        ST.last_token_refresh.date() < today or
        week_exp <= today  # expiry ho gayi — next week ke token chahiye
    )

    if not need_refresh:
        hrs = (now - ST.last_token_refresh).total_seconds() / 3600
        _log(f"Tokens fresh ({hrs:.1f}h ago) — skip refresh")
        return True

    if week_exp <= today:
        _log(f"Expiry ho gayi ({week_exp}) — next week ke tokens fetch ho rahe hain...")
    else:
        _log(f"Token refresh: {today} (expiry: {week_exp})")

    _log("Token refresh ho raha hai Angel API se...")

    try:
        # Angel One ka live scrip master download karo
        token_url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        resp = requests.get(token_url, timeout=60)
        if resp.status_code != 200:
            _log(f"Scrip master download failed: {resp.status_code}")
            return False

        items = resp.json()
        _log(f"Scrip master loaded: {len(items)} tokens")

        today     = datetime.date.today()
        week_exp  = get_weekly_expiry()
        fut_found = {}
        opt_found = {}

        for item in items:
            if not isinstance(item, dict): continue
            name    = str(item.get("name") or item.get("symbol") or
                         item.get("tradingsymbol") or "").upper()
            token   = str(item.get("token") or item.get("symboltoken") or "")
            exch    = str(item.get("exch_seg") or item.get("exchange") or "").upper()
            itype   = str(item.get("instrumenttype") or "").upper()
            exp_str = str(item.get("expiry") or "")
            strike  = item.get("strike") or item.get("strikeprice") or 0

            if not token or exch != "NFO": continue
            exp = parse_expiry(exp_str)
            if not exp or exp < today: continue

            # ── FUTURES ────────────────────────────────────────────
            if "FUT" in itype:
                sym_map = [
                    ("NIFTY 50",   "NIFTY",      EXCLUDE_NIFTY),
                    ("BANKNIFTY",  "BANKNIFTY",  []),
                    ("FINNIFTY",   "FINNIFTY",   []),
                    ("MIDCPNIFTY", "MIDCPNIFTY", []),
                ]
                for sym_key, prefix, excl in sym_map:
                    if not name.startswith(prefix): continue
                    if any(name.startswith(x) for x in excl): continue
                    if sym_key not in fut_found or exp < fut_found[sym_key]["exp"]:
                        fut_found[sym_key] = {
                            "token":token,"exp":exp,"name":name,"exchange":"NFO"
                        }

            # ── OPTIONS — OPTIDX only (index options) ─────────────
            if itype != "OPTIDX": continue

            # name field = "NIFTY" exactly (MIDCPNIFTY, NIFTYNXT50 exclude)
            item_name = str(item.get("name","")).upper()
            if item_name != "NIFTY": continue

            # symbol field se CE/PE type lo
            sym_field = str(item.get("symbol","")).upper()
            if sym_field.endswith("CE"):   opt_type = "CE"
            elif sym_field.endswith("PE"): opt_type = "PE"
            else: continue

            # Sirf near-expiry (14 din ke andar)
            if (exp - today).days > 14: continue

            # Strike: field value / 100 = actual strike
            # e.g. '2125000.000000' / 100 = 21250
            try:
                strike_val = int(float(item.get("strike", 0)) / 100)
            except: continue

            if not (18000 <= strike_val <= 30000): continue

            # Key: symbol field directly use karo (exact trading symbol)
            # e.g. NIFTY12MAY2624100CE
            okey = sym_field  # exact symbol as key
            if okey not in opt_found:
                opt_found[okey] = {
                    "token":  token,
                    "strike": strike_val,
                    "type":   opt_type,
                    "expiry": str(item.get("expiry","")),
                    "symbol": sym_field,
                }

        # Store in ST
        ST.fut_tokens = fut_found
        ST.opt_tokens = opt_found
        ST.last_token_refresh = now

        # Log results
        for sym, data in fut_found.items():
            _log(f"Future token: {sym} -> {data['name']} ({data['token']})")
        _log(f"Option tokens: {len(opt_found)} (week expiry: {week_exp})")

        return True

    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return False

def get_future_token(sym="NIFTY 50"):
    """Current month ka future token do."""
    data = ST.fut_tokens.get(sym)
    if data:
        return data["token"], "NFO"
    return None, None

def get_option_token(sym, strike, opt_type):
    """
    Current week ka ATM option token do.
    Symbol format: NIFTY12MAY2624100CE
    Expiry format: DDMMMYY (2 digit year) e.g. 12MAY26
    """
    if not ST.opt_tokens:
        return None, None

    # Try nearest expiry first (weekly), then next
    for exp_offset in [0, 7, -7]:
        exp     = get_weekly_expiry() + datetime.timedelta(days=exp_offset)
        # Angel format: DDMMMYY (2 digit year)
        exp_str = exp.strftime("%d%b%Y")[:-2].upper()  # e.g. 12MAY26

        # Try ATM + nearby strikes
        for delta in [0, 50,-50, 100,-100, 150,-150, 200,-200]:
            s   = int(strike) + delta
            key = f"NIFTY{exp_str}{s}{opt_type}"
            if key in ST.opt_tokens:
                d = ST.opt_tokens[key]
                return d["token"], d["symbol"]

    return None, None

def get_option_ltp_live(sym, spot, opt_type):
    """
    Real option LTP Angel API se fetch karo.
    Angel format confirmed:
      symbol: NIFTY12MAY2624100CE
      token:  41xxx
      LTP:    real premium (e.g. 145.30)
    """
    try:
        info   = INSTRUMENTS.get(sym, {})
        sg     = info.get("sg", 50)
        strike = round(spot / sg) * sg

        # Stored tokens se dhundo
        token, opt_sym = get_option_token(sym, strike, opt_type)

        if token and opt_sym and ST.api:
            try:
                r = ST.api.ltpData("NFO", opt_sym, token)
                if isinstance(r, dict) and r.get("status"):
                    d = r.get("data", {})
                    if isinstance(d, dict):
                        ltp = float(d.get("ltp", 0))
                        if ltp > 0:
                            logger.info(f"Option LTP (REAL): {opt_sym} = {ltp}")
                            return ltp
            except Exception as e1:
                logger.warning(f"LTP fetch failed: {e1}")

        # Fallback: 0.5% of spot (sirf tab jab token na mile)
        est = round(spot * 0.005, 2)
        logger.warning(f"Option LTP ESTIMATED (token nahi mila): {est}")
        return est

    except Exception as e:
        logger.error(f"Option LTP error: {e}")
        return round(spot * 0.005, 2)

# ═══════════════════════════════════════════════════════
#  INDICATORS — EMA + Volume
# ═══════════════════════════════════════════════════════
def calc_indicators(price_df, vol_df=None):
    """
    EMA 9/21 + Volume filter calculate karo.
    price_df: Nifty spot/index price
    vol_df:   Nifty Future volume (real volume)
    """
    f   = CFG["EMA_FAST"]
    s   = CFG["EMA_SLOW"]
    vp  = CFG["VOL_PERIOD"]
    gap = CFG["EMA_GAP"]
    df  = price_df.copy()

    df["ema_f"]   = df["close"].ewm(span=f, adjust=False).mean()
    df["ema_s"]   = df["close"].ewm(span=s, adjust=False).mean()
    df["ema_gap"] = df["ema_f"] - df["ema_s"]

    # Volume: Future se real volume use karo
    if vol_df is not None and not vol_df.empty and vol_df["volume"].sum() > 0:
        df = df.join(
            vol_df[["volume"]].rename(columns={"volume":"fvol"}),
            how="left"
        )
        df["fvol"]    = df["fvol"].ffill().fillna(0)
        df["vol_avg"] = df["fvol"].rolling(vp, min_periods=1).mean().fillna(0)
        df["vol_ok"]  = (df["vol_avg"] > 0) & \
                        (df["fvol"] >= df["vol_avg"] * CFG["VOL_MULT"])
        logger.info(f"Future volume used | vol_ok: {df['vol_ok'].sum()}/{len(df)}")
    else:
        # Index spot ka volume 0 hota hai — filter skip
        df["vol_avg"] = 0
        df["vol_ok"]  = True
        logger.info("Volume filter disabled (index spot data, no volume)")

    # Signals: EMA cross + gap confirm + volume
    df["ce_sig"] = (
        (df["ema_gap"] >= gap) &
        (df["ema_gap"].shift(1) < gap) &
        df["vol_ok"]
    )
    df["pe_sig"] = (
        (df["ema_gap"] <= -gap) &
        (df["ema_gap"].shift(1) > -gap) &
        df["vol_ok"]
    )

    return df.dropna(subset=["ema_f","ema_s","ema_gap"])

# ═══════════════════════════════════════════════════════
#  P&L + SL/TSL
# ═══════════════════════════════════════════════════════
def opt_pnl(entry, exit_p, lot):
    """Option P&L: (exit - entry) * lot — same for CE and PE."""
    return (exit_p - entry) * lot

def opt_price_est(spot, spot_entry, opt_entry, otype):
    """
    Historical option price estimate (backtest ke liye).
    Delta ~0.5 ATM ke liye.
    CE: spot upar gaya toh option price badhti hai
    PE: spot neeche gaya toh option price badhti hai
    """
    move = spot - spot_entry
    if otype == "CE":
        price = opt_entry + move * 0.5
    else:
        price = opt_entry - move * 0.5
    return max(0.05, round(price, 2))

def check_sl_tsl_tgt(pos, cur_opt_price):
    """
    SL, TSL, Target check karo — points mein.
    Returns (should_exit, reason)
    """
    entry    = pos["opt_entry"]
    sl_pts   = CFG["SL_PTS"]
    tsl_pts  = CFG["TSL_PTS"]
    tgt_pts  = CFG["TGT_PTS"]
    best     = pos.get("best_opt", entry)

    # Best track karo
    if cur_opt_price > best:
        best = cur_opt_price
    pos["best_opt"] = best

    sl_level  = entry - sl_pts
    tsl_level = best  - tsl_pts
    eff_sl    = max(sl_level, tsl_level)
    tgt_level = entry + tgt_pts

    if cur_opt_price <= eff_sl:
        return True, f"SL/TSL hit ({eff_sl:.0f})"
    if cur_opt_price >= tgt_level:
        return True, f"Target hit ({tgt_level:.0f})"
    return False, ""

# ═══════════════════════════════════════════════════════
#  TELEGRAM + VOICE
# ═══════════════════════════════════════════════════════
def tg(msg):
    try:
        requests.post(
            f"https://api.telegram.org/bot{CFG['BOT_TOKEN']}/sendMessage",
            data={"chat_id":CFG["CHAT_ID"],"text":msg,"parse_mode":"HTML"},
            timeout=10)
    except: pass

def tg_file(path, cap=""):
    try:
        with open(path,"rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{CFG['BOT_TOKEN']}/sendDocument",
                data={"chat_id":CFG["CHAT_ID"],"caption":cap},
                files={"document":f}, timeout=30)
    except: pass

def voice(text):
    def _l():
        if PYTTSX_OK and CFG["VOICE"]:
            try: _tts.say(text); _tts.runAndWait()
            except: pass
    def _t():
        if GTTS_OK and CFG["VOICE"]:
            try:
                g = gTTS(text=text, lang="hi", slow=False)
                b = io.BytesIO(); g.write_to_fp(b); b.seek(0)
                requests.post(
                    f"https://api.telegram.org/bot{CFG['BOT_TOKEN']}/sendAudio",
                    data={"chat_id":CFG["CHAT_ID"],"title":"Alert"},
                    files={"audio":("a.mp3",b,"audio/mpeg")}, timeout=20)
            except: pass
    threading.Thread(target=_l, daemon=True).start()
    threading.Thread(target=_t, daemon=True).start()

# ═══════════════════════════════════════════════════════
#  PDF REPORT
# ═══════════════════════════════════════════════════════
def make_pdf(trades, fname=None):
    if not fname:
        fname = f"report_{datetime.date.today()}.pdf"
    doc    = SimpleDocTemplate(fname, pagesize=letter,
             rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    el     = []

    el.append(Paragraph("Nifty Auto Trader — Report", styles["Title"]))
    el.append(Paragraph(
        f"{datetime.date.today().strftime('%d %B %Y')} | "
        f"{CFG['SYMBOL']} | {ST.mode.upper()}", styles["Normal"]))
    el.append(Spacer(1,12))

    total = sum(t.get("pnl",0) for t in trades)
    wins  = sum(1 for t in trades if t.get("pnl",0)>0)
    rate  = wins/len(trades)*100 if trades else 0
    ce_c  = sum(1 for t in trades if t.get("otype")=="CE")
    pe_c  = sum(1 for t in trades if t.get("otype")=="PE")

    sdata = [
        ["Metric","Value"],
        ["Symbol",    CFG["SYMBOL"]],
        ["Mode",      ST.mode.upper()],
        ["Total",     str(len(trades))],
        ["CE",        str(ce_c)],
        ["PE",        str(pe_c)],
        ["Wins",      str(wins)],
        ["Losses",    str(len(trades)-wins)],
        ["Win Rate",  f"{rate:.1f}%"],
        ["P&L",       f"Rs.{total:,.2f}"],
        ["SL pts",    str(CFG["SL_PTS"])],
        ["TSL pts",   str(CFG["TSL_PTS"])],
        ["TGT pts",   str(CFG["TGT_PTS"])],
        ["EMA Gap",   f"{CFG['EMA_GAP']} pts"],
        ["Volume",    f"{CFG['VOL_PERIOD']} x {CFG['VOL_MULT']}"],
    ]
    t = Table(sdata, colWidths=[180,160])
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0,0),(-1,0),colors.white),
        ("FONTNAME",  (0,0),(-1,0),"Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#f0f9ff"),colors.white]),
        ("GRID",(0,0),(-1,-1),0.5,colors.grey),
        ("FONTSIZE",(0,0),(-1,-1),10),
        ("PADDING",(0,0),(-1,-1),8),
    ]))
    el.append(Paragraph("<b>Summary</b>", styles["Heading2"]))
    el.append(t)
    el.append(Spacer(1,14))

    if trades:
        el.append(Paragraph("<b>Trade Log</b>", styles["Heading2"]))
        hdr  = ["Time","OType","Dir","Strike","Spot Entry","Opt Entry","Opt Exit","P&L","Reason"]
        rows = [hdr]
        for tr in trades[-50:]:
            p  = tr.get("pnl",0)
            ot = tr.get("otype","CE")
            rows.append([
                str(tr.get("entry_time",""))[:16],
                ot,
                "Bull" if ot=="CE" else "Bear",
                str(tr.get("strike","")),
                f"Rs.{tr.get('spot_entry',0):.0f}",
                f"Rs.{tr.get('opt_entry',0):.2f}",
                f"Rs.{tr.get('opt_exit',0):.2f}",
                f"Rs.{p:.2f}",
                tr.get("reason",""),
            ])
        tbl = Table(rows, colWidths=[78,38,35,50,60,55,55,60,62])
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1e293b")),
            ("TEXTCOLOR", (0,0),(-1,0),colors.white),
            ("FONTNAME",  (0,0),(-1,0),"Helvetica-Bold"),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.HexColor("#f8fafc"),colors.white]),
            ("GRID",(0,0),(-1,-1),0.5,colors.grey),
            ("FONTSIZE",(0,0),(-1,-1),7.5),
            ("PADDING",(0,0),(-1,-1),4),
        ]))
        el.append(tbl)

    doc.build(el)
    return fname

# ═══════════════════════════════════════════════════════
#  BACKTEST — Angel API se live historical data
# ═══════════════════════════════════════════════════════
def run_backtest(sym, days, log_fn):
    """
    Backtest: Angel API se historical data fetch karo — koi file nahi.
    Days change karo jitne din ka backtest chahiye.
    """
    info = INSTRUMENTS.get(sym, INSTRUMENTS["NIFTY 50"])
    log_fn(f"Data fetch ho raha hai: {sym} | {days} days", "info")

    # Step 1: Spot/Index price data
    price_df = fetch_candles(
        info["spot_token"], info["exchange"],
        CFG["INTERVAL"], days, sym
    )
    if price_df.empty:
        log_fn("Data nahi mila! Market hours mein try karo (9:15-15:30).", "err")
        return []

    log_fn(f"Price data: {len(price_df)} candles | {price_df.index[0].date()} to {price_df.index[-1].date()}", "sig")

    # Step 2: Future volume data (real volume)
    vol_df = pd.DataFrame()
    if sym in INDEX_SYMS:
        fut_token, fut_exch = get_future_token(sym)
        if fut_token:
            log_fn(f"Future volume fetch: token={fut_token}", "info")
            vol_df = fetch_candles(fut_token, fut_exch, CFG["INTERVAL"], days+5, f"{sym}_FUT")
            if not vol_df.empty and vol_df["volume"].sum() > 0:
                log_fn(f"Volume data: {len(vol_df)} candles | sum={vol_df['volume'].sum():,.0f}", "sig")
            else:
                log_fn("Volume = 0, filter disable hoga", "warn")
        else:
            log_fn("Future token nahi mila — volume filter disable", "warn")

    # Step 3: Indicators
    df = calc_indicators(price_df, vol_df if not vol_df.empty else None)
    log_fn(f"Indicators ready | CE signals: {df['ce_sig'].sum()} | PE signals: {df['pe_sig'].sum()}", "info")

    if df["ce_sig"].sum() + df["pe_sig"].sum() == 0:
        log_fn("0 signals! EMA Gap ya Volume settings check karo.", "warn")
        return []

    # Step 4: Backtest loop
    lot     = info["lot"]
    trades  = []
    pos     = None
    cap     = CFG["PAPER_CAP"]
    sg      = info["sg"]

    for ts, row in df.iterrows():
        # EXIT check
        if pos:
            cur_opt = opt_price_est(
                row["close"], pos["spot_entry"],
                pos["opt_entry"], pos["otype"]
            )
            should_exit, reason = check_sl_tsl_tgt(pos, cur_opt)
            if not should_exit:
                if pos["otype"]=="CE" and row["pe_sig"]:
                    should_exit, reason = True, "Reverse->PE"
                elif pos["otype"]=="PE" and row["ce_sig"]:
                    should_exit, reason = True, "Reverse->CE"

            if should_exit:
                p = opt_pnl(pos["opt_entry"], cur_opt, lot)
                cap += p
                trades.append({**pos,
                    "exit_time": str(ts),
                    "opt_exit":  round(cur_opt, 2),
                    "spot_exit": round(row["close"], 2),
                    "pnl":       round(p, 2),
                    "reason":    reason,
                    "cap_after": round(cap, 2),
                })
                log_fn(
                    f"EXIT {pos['otype']} | "
                    f"Spot:{row['close']:.0f} Opt:{cur_opt:.1f} | "
                    f"{reason} | P&L:Rs.{p:+.0f}",
                    "sig" if p >= 0 else "err"
                )
                pos = None

        # ENTRY check
        if not pos:
            if row["ce_sig"]:
                strike    = round(row["close"] / sg) * sg
                opt_price = round(row["close"] * 0.005, 2)
                pos = {
                    "entry_time": str(ts),
                    "otype":      "CE",
                    "strike":     strike,
                    "spot_entry": round(row["close"], 2),
                    "opt_entry":  opt_price,
                    "best_opt":   opt_price,
                    "symbol":     sym,
                }
                log_fn(
                    f"BUY CE | Spot:{row['close']:.0f} "
                    f"Strike:{strike} Opt~{opt_price:.1f} | "
                    f"Gap:{row['ema_gap']:+.1f}",
                    "sig"
                )
            elif row["pe_sig"] and CFG["BOTH_SIDE"]:
                strike    = round(row["close"] / sg) * sg
                opt_price = round(row["close"] * 0.005, 2)
                pos = {
                    "entry_time": str(ts),
                    "otype":      "PE",
                    "strike":     strike,
                    "spot_entry": round(row["close"], 2),
                    "opt_entry":  opt_price,
                    "best_opt":   opt_price,
                    "symbol":     sym,
                }
                log_fn(
                    f"BUY PE | Spot:{row['close']:.0f} "
                    f"Strike:{strike} Opt~{opt_price:.1f} | "
                    f"Gap:{row['ema_gap']:+.1f}",
                    "sig"
                )

    # Close open position at end
    if pos:
        last  = df.iloc[-1]
        cur   = opt_price_est(last["close"], pos["spot_entry"],
                              pos["opt_entry"], pos["otype"])
        p     = opt_pnl(pos["opt_entry"], cur, lot)
        cap  += p
        trades.append({**pos,
            "exit_time": str(df.index[-1]),
            "opt_exit":  round(cur, 2),
            "spot_exit": round(last["close"], 2),
            "pnl":       round(p, 2),
            "reason":    "EOD",
            "cap_after": round(cap, 2),
        })

    ST.trades = trades
    save_state()
    return trades

# ═══════════════════════════════════════════════════════
#  PAPER / LIVE TRADING LOOP
# ═══════════════════════════════════════════════════════
def trading_loop(log_fn):
    sym  = CFG["SYMBOL"]
    info = INSTRUMENTS.get(sym, INSTRUMENTS["NIFTY 50"])
    log_fn(f"Trading loop: {sym} | {ST.mode.upper()}", "sig")

    tg(
        f"<b>Nifty Auto Trader — Shuru New Tanishka!</b>\n"
        f"Symbol: {sym} | Mode: {ST.mode.upper()}\n"
        f"EMA:{CFG['EMA_FAST']}/{CFG['EMA_SLOW']} Gap:{CFG['EMA_GAP']}pt\n"
        f"SL:{CFG['SL_PTS']}pt TSL:{CFG['TSL_PTS']}pt TGT:{CFG['TGT_PTS']}pt\n"
        f"/start /stop /status /report /help"
    )
    voice(f"Nifty auto trader shuru. {sym} mein trading chalegi.")

    # Future token
    fut_token, fut_exch = get_future_token(sym) if sym in INDEX_SYMS else (None, None)

    while ST.running:
        try:
            now  = datetime.datetime.now()
            mo   = now.replace(hour=9,  minute=15, second=0, microsecond=0)
            mc   = now.replace(hour=15, minute=30, second=0, microsecond=0)

            if now.weekday() >= 5 or not (mo <= now <= mc):
                time.sleep(30)
                continue

            # Weekly token refresh check
            exp = get_weekly_expiry()
            if exp <= datetime.date.today():
                log_fn("Weekly expiry! Token refresh ho raha hai...", "warn")
                refresh_tokens(log_fn)
                fut_token, fut_exch = get_future_token(sym)

            # Spot price
            spot = get_ltp(info["spot_token"], info["exchange"])
            if not spot:
                time.sleep(60); continue

            # Price candles
            price_df = fetch_candles(
                info["spot_token"], info["exchange"],
                CFG["INTERVAL"], 2, sym
            )
            if price_df.empty or len(price_df) < CFG["EMA_SLOW"] + 3:
                time.sleep(60); continue

            # Future volume
            vol_df = pd.DataFrame()
            if fut_token:
                vol_df = fetch_candles(fut_token, fut_exch,
                                       CFG["INTERVAL"], 2, f"{sym}_FUT")

            df   = calc_indicators(price_df, vol_df if not vol_df.empty else None)
            last = df.iloc[-1]
            sg   = info["sg"]
            strike = round(spot / sg) * sg

            # Check existing position SL/TSL/TGT
            if ST.positions:
                pos = ST.positions[-1]
                # Real option LTP
                cur_opt = get_option_ltp_live(sym, spot, pos["otype"])
                should_exit, reason = check_sl_tsl_tgt(pos, cur_opt)
                if not should_exit:
                    if pos["otype"]=="CE" and last["pe_sig"]:
                        should_exit, reason = True, "Reverse->PE"
                    elif pos["otype"]=="PE" and last["ce_sig"]:
                        should_exit, reason = True, "Reverse->CE"

                if should_exit:
                    p = opt_pnl(pos["opt_entry"], cur_opt, info["lot"])
                    ST.balance += p
                    trade = {**pos,
                        "exit_time": str(now),
                        "opt_exit":  round(cur_opt, 2),
                        "spot_exit": round(spot, 2),
                        "pnl":       round(p, 2),
                        "reason":    reason,
                    }
                    ST.trades.append(trade)
                    ST.positions.clear()
                    save_state()

                    r_str = "munafa" if p >= 0 else "nuksan"
                    log_fn(f"EXIT {pos['otype']} | {reason} | P&L:Rs.{p:+.0f}", "sig" if p>=0 else "err")
                    tg(f"{'OK' if p>=0 else 'LOSS'} <b>{sym} {pos['otype']} EXIT</b>\n"
                       f"{reason}\nP&L: Rs.{p:,.2f}")
                    voice(f"{sym} trade band. {abs(int(p))} rupaye {r_str}.")

            # New entry
            if not ST.positions:
                if last["ce_sig"]:
                    ltp = get_option_ltp_live(sym, spot, "CE")
                    pos = {"entry_time":str(now),"otype":"CE","strike":strike,
                           "spot_entry":round(spot,2),"opt_entry":round(ltp,2),
                           "best_opt":round(ltp,2),"symbol":sym}
                    ST.positions.append(pos)
                    ST.last_sig = pos
                    save_state()
                    log_fn(f"BUY CE | Spot:{spot:.0f} Strike:{strike} LTP:{ltp:.2f}", "sig")
                    tg(f"<b>{sym} CE BUY</b>\nSpot:{spot:.0f} Strike:{strike} LTP:{ltp:.2f}\n"
                       f"SL:{CFG['SL_PTS']}pt TSL:{CFG['TSL_PTS']}pt TGT:{CFG['TGT_PTS']}pt")
                    voice(f"{sym} mein call buy. Spot {int(spot)}.")
                    if ST.mode == "live":
                        place_order(sym, "CE", strike, "BUY", info["lot"])

                elif last["pe_sig"] and CFG["BOTH_SIDE"]:
                    ltp = get_option_ltp_live(sym, spot, "PE")
                    pos = {"entry_time":str(now),"otype":"PE","strike":strike,
                           "spot_entry":round(spot,2),"opt_entry":round(ltp,2),
                           "best_opt":round(ltp,2),"symbol":sym}
                    ST.positions.append(pos)
                    ST.last_sig = pos
                    save_state()
                    log_fn(f"BUY PE | Spot:{spot:.0f} Strike:{strike} LTP:{ltp:.2f}", "sig")
                    tg(f"<b>{sym} PE BUY</b>\nSpot:{spot:.0f} Strike:{strike} LTP:{ltp:.2f}\n"
                       f"SL:{CFG['SL_PTS']}pt TSL:{CFG['TSL_PTS']}pt TGT:{CFG['TGT_PTS']}pt")
                    voice(f"{sym} mein put buy. Spot {int(spot)}.")
                    if ST.mode == "live":
                        place_order(sym, "PE", strike, "BUY", info["lot"])

            time.sleep(300)

        except Exception as e:
            log_fn(f"Loop error: {e}", "err")
            time.sleep(60)

    # Trading band hone par EOD report
    send_eod_report(log_fn)

def place_order(sym, otype, strike, txn, lot):
    try:
        # Correctly unpack token and symbol
        token, opt_sym = get_option_token(sym, strike, otype)

        if not token or not opt_sym:
            tg(f"Order FAILED: Token not found for {sym} {strike} {otype}")
            return

        # Place Order API call
        params = {
            "variety": "NORMAL",
            "tradingsymbol": opt_sym,
            "symboltoken": token,
            "transactiontype": txn,
            "exchange": "NFO",
            "ordertype": "MARKET",
            "producttype": "INTRADAY",
            "duration": "DAY",
            "price": "0",
            "quantity": str(lot)
        }

        response = ST.api.placeOrder(params)
        if response and response.get('status'):
            order_id = response.get('data', {}).get('orderid', 'N/A')
            tg(f"<b>LIVE ORDER PLACED</b>\nID: {order_id}\n{opt_sym} {txn}")
        else:
            tg(f"Order REJECTED: {response.get('message', 'Unknown Error')}")

    except Exception as e:
        logger.error(f"Order Error: {e}")

def send_eod_report(log_fn=None):
    today  = [t for t in ST.trades
              if str(datetime.date.today()) in str(t.get("entry_time",""))]
    pnl    = sum(t.get("pnl",0) for t in today)
    wins   = sum(1 for t in today if t.get("pnl",0)>0)
    if not today:
        tg("EOD: Aaj koi trade nahi hua.")
        return
    fname = make_pdf(today)
    tg_file(fname, f"EOD Report | {CFG['SYMBOL']} | {datetime.date.today()}")
    voice(f"Aaj ki report bhej di. {len(today)} trade. {abs(int(pnl))} rupaye {'faayda' if pnl>=0 else 'nuksan'}.")
    if log_fn:
        log_fn(f"EOD PDF sent | T:{len(today)} W:{wins} P&L:Rs.{pnl:.0f}", "sig")

# ═══════════════════════════════════════════════════════
#  TELEGRAM POLLING
# ═══════════════════════════════════════════════════════
def poll_telegram(log_fn, start_cb, stop_cb):
    offset = 0
    url    = f"https://api.telegram.org/bot{CFG['BOT_TOKEN']}/getUpdates"
    while True:
        try:
            r    = requests.get(url, params={"offset":offset,"timeout":30}, timeout=35)
            data = r.json()
            for upd in data.get("result",[]):
                offset = upd["update_id"] + 1
                msg    = upd.get("message",{})
                txt    = msg.get("text","").strip().lower()
                chat   = str(msg.get("chat",{}).get("id",""))
                if chat != CFG["CHAT_ID"]: continue
                log_fn(f"TG: {txt}", "info")
                if txt == "/start":
                    if not ST.running: start_cb()
                    else: tg("Already running!")
                elif txt == "/stop":
                    stop_cb()
                elif txt == "/status":
                    today = [t for t in ST.trades if str(datetime.date.today()) in str(t.get("entry_time",""))]
                    p     = sum(t.get("pnl",0) for t in today)
                    w     = sum(1 for t in today if t.get("pnl",0)>0)
                    tg(f"Status\nMode:{ST.mode.upper()}\n"
                       f"Running:{'YES' if ST.running else 'NO'}\n"
                       f"Symbol:{CFG['SYMBOL']}\n"
                       f"Today:{len(today)} trades | Wins:{w}\n"
                       f"P&L:Rs.{p:,.2f}\nBalance:Rs.{ST.balance:,.2f}")
                elif txt == "/report":
                    send_eod_report(log_fn)
                elif txt == "/help":
                    tg("/start /stop /status /report /help")
        except Exception as e:
            logger.error(f"TG poll: {e}")
            time.sleep(5)

# ═══════════════════════════════════════════════════════════════════════
#  GUI
# ═══════════════════════════════════════════════════════════════════════
BG=   "#07090f"; S1=  "#0c1220";  CARD="#111828"
BDR=  "#1a2840"; ACC= "#00e5ff";  GRN= "#00ff88"
RED=  "#ff4466"; GOLD="#ffd700";  TXT= "#ddeeff"
MUT=  "#4a6080"; FONT="Consolas"

root = tk.Tk()
root.title("NIFTY AUTO TRADER — FULLY AUTOMATIC")
root.geometry("1080x700")
root.configure(bg=BG)
root.resizable(True, True)

style = ttk.Style()
style.theme_use("default")
style.configure("TNotebook",      background=BG,   borderwidth=0)
style.configure("TNotebook.Tab",  background=S1,   foreground=MUT,
                font=(FONT,10,"bold"), padding=[14,6])
style.map("TNotebook.Tab",
          background=[("selected",CARD)],
          foreground=[("selected",ACC)])
style.configure("Treeview", background=S1, foreground=TXT,
    rowheight=26, fieldbackground=S1, font=(FONT,10))
style.configure("Treeview.Heading", background=CARD,
    foreground=ACC, font=(FONT,10,"bold"))
style.map("Treeview", background=[("selected","#1a3a5c")])

def _btn(parent, text, cmd, bg=ACC, fg="#000", w=16):
    b = tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                  font=(FONT,10,"bold"), relief="flat", cursor="hand2",
                  width=w, pady=6, activebackground=bg, activeforeground=fg)
    return b

def _entry(parent, var, w=16, show=None):
    e = tk.Entry(parent, textvariable=var, bg=S1, fg=ACC,
                 insertbackground=ACC, relief="flat",
                 font=(FONT,10), width=w,
                 highlightthickness=1,
                 highlightbackground=BDR, highlightcolor=ACC)
    if show: e.config(show=show)
    return e

def _lbl(parent, text, sz=10, fg=TXT, bold=False, bg=BG):
    return tk.Label(parent, text=text, bg=bg, fg=fg,
                    font=(FONT, sz, "bold" if bold else "normal"))

# ── TOP BAR ───────────────────────────────────────────────────────────
top = tk.Frame(root, bg="#050810", height=50)
top.pack(fill="x")
_lbl(top,"  NIFTY AUTO TRADER",14,ACC,True,"#050810").pack(side="left",pady=10)
lbl_run  = tk.Label(top,text="IDLE",bg="#050810",fg=MUT,font=(FONT,11,"bold"))
lbl_run.pack(side="right",padx=14)
lbl_mode = tk.Label(top,text="PAPER",bg="#050810",fg=ACC,font=(FONT,11,"bold"))
lbl_mode.pack(side="right",padx=8)
lbl_sym  = tk.Label(top,text="NIFTY 50",bg="#050810",fg=GOLD,font=(FONT,11,"bold"))
lbl_sym.pack(side="right",padx=8)

nb = ttk.Notebook(root)
nb.pack(fill="both", expand=True, padx=6, pady=(4,6))

# ═══════════════════════════════════════════════
# TAB 1 — TRADING
# ═══════════════════════════════════════════════
t1 = tk.Frame(nb, bg=BG); nb.add(t1, text="  Trading  ")

lp = tk.Frame(t1, bg=CARD, width=215)
lp.pack(side="left", fill="y", padx=(8,4), pady=8, ipadx=8, ipady=8)
lp.pack_propagate(False)

_lbl(lp,"SYMBOL",9,MUT,bg=CARD).pack(anchor="w",padx=10,pady=(10,2))
v_sym = tk.StringVar(value=CFG["SYMBOL"])
sym_dd= ttk.Combobox(lp,textvariable=v_sym,values=list(INSTRUMENTS.keys()),
                     state="readonly",width=17)
sym_dd.pack(padx=10,pady=(0,6))

_lbl(lp,"MODE",9,MUT,bg=CARD).pack(anchor="w",padx=10,pady=(6,2))
v_mode = tk.StringVar(value="paper")
for m,c,t in [("backtest",GOLD,"Backtest"),("paper",ACC,"Paper"),("live",RED,"Live")]:
    tk.Radiobutton(lp,text=t,variable=v_mode,value=m,
                   bg=CARD,fg=c,selectcolor=S1,
                   activebackground=CARD,font=(FONT,10,"bold"),
                   relief="flat").pack(anchor="w",padx=10,pady=2)

tk.Frame(lp,bg=BDR,height=1).pack(fill="x",padx=8,pady=8)

lbl_pnl = tk.Label(lp,text="Today P&L\nRs.0.00",bg=CARD,fg=GRN,font=(FONT,12,"bold"))
lbl_pnl.pack(pady=4)
lbl_bal = tk.Label(lp,text="Balance: Rs.25,000",bg=CARD,fg=TXT,font=(FONT,9))
lbl_bal.pack(pady=2)
lbl_pos = tk.Label(lp,text="Pos:0  Trades:0",bg=CARD,fg=MUT,font=(FONT,9))
lbl_pos.pack(pady=2)

tk.Frame(lp,bg=BDR,height=1).pack(fill="x",padx=8,pady=8)

btn_start = _btn(lp,"START",None,GRN,"#000",16)
btn_start.pack(padx=8,pady=4,fill="x")
btn_stop  = _btn(lp,"STOP", None,RED,"#fff",16)
btn_stop.pack(padx=8,pady=4,fill="x")
btn_stop.config(state="disabled")

_btn(lp,"TG Status",  None,GOLD,"#000",16).pack(padx=8,pady=3,fill="x")
_btn(lp,"EOD Report", None,ACC, "#000",16).pack(padx=8,pady=3,fill="x")
_btn(lp,"Test TG",    None,"#334",TXT,  16).pack(padx=8,pady=3,fill="x")

rp = tk.Frame(t1,bg=BG)
rp.pack(side="left",fill="both",expand=True,padx=(4,8),pady=8)
_lbl(rp,"LIVE LOG",9,MUT).pack(anchor="w")
log_box = scrolledtext.ScrolledText(rp,bg=S1,fg=ACC,font=(FONT,10),
    relief="flat",insertbackground=ACC,wrap="word",state="disabled")
log_box.pack(fill="both",expand=True)
log_box.tag_config("sig", foreground=GRN)
log_box.tag_config("err", foreground=RED)
log_box.tag_config("warn",foreground=GOLD)
log_box.tag_config("info",foreground=ACC)
log_box.tag_config("mut", foreground=MUT)

def log(msg, tag="info"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    log_box.config(state="normal")
    log_box.insert("end",f"[{ts}] ","mut")
    log_box.insert("end",msg+"\n",tag)
    log_box.see("end")
    log_box.config(state="disabled")
    logger.info(msg)

# ═══════════════════════════════════════════════
# TAB 2 — BACKTEST
# ═══════════════════════════════════════════════
t2 = tk.Frame(nb,bg=BG); nb.add(t2,text="  Backtest  ")

blp = tk.Frame(t2,bg=CARD,width=220)
blp.pack(side="left",fill="y",padx=(8,4),pady=8,ipadx=8,ipady=8)
blp.pack_propagate(False)

_lbl(blp,"SYMBOL",9,MUT,bg=CARD).pack(anchor="w",padx=10,pady=(10,2))
v_bt_sym = tk.StringVar(value="NIFTY 50")
ttk.Combobox(blp,textvariable=v_bt_sym,values=list(INSTRUMENTS.keys()),
             state="readonly",width=17).pack(padx=10,pady=(0,8))

_lbl(blp,"DAYS (Angel API se live data)",9,MUT,bg=CARD).pack(anchor="w",padx=10)
v_bt_days = tk.StringVar(value="30")
_entry(blp,v_bt_days,17).pack(padx=10,pady=(2,8))

_lbl(blp,"",9,MUT,bg=CARD).pack(anchor="w",padx=10)
tk.Label(blp,
    text="Koi file nahi — seedha\nAngel API se data lega.\nDays badlo jitna chahiye.",
    bg=CARD,fg=MUT,font=(FONT,9),justify="left").pack(padx=10,pady=4,anchor="w")

btn_bt = _btn(blp,"RUN BACKTEST",None,GOLD,"#000",18)
btn_bt.pack(padx=8,pady=10,fill="x")

brp = tk.Frame(t2,bg=BG)
brp.pack(side="left",fill="both",expand=True,padx=(4,8),pady=8)
_lbl(brp,"RESULTS",9,MUT).pack(anchor="w")
bt_log = scrolledtext.ScrolledText(brp,bg=S1,fg=TXT,font=(FONT,10),
    relief="flat",wrap="word")
bt_log.pack(fill="both",expand=True)

def bt_write(msg, tag=""):
    bt_log.insert("end", msg+"\n")
    bt_log.see("end")

# ═══════════════════════════════════════════════
# TAB 3 — SCANNER
# ═══════════════════════════════════════════════
t3 = tk.Frame(nb,bg=BG); nb.add(t3,text="  Scanner  ")

sc_top = tk.Frame(t3,bg=BG)
sc_top.pack(fill="x",padx=8,pady=(8,4))
btn_scan = _btn(sc_top,"Scan Now",None,ACC,"#000",12)
btn_scan.pack(side="left",padx=4)
lbl_scan = tk.Label(sc_top,text="",bg=BG,fg=MUT,font=(FONT,9))
lbl_scan.pack(side="left",padx=10)

sc_cols = ("Symbol","LTP","EMA Gap","Vol OK","Signal","Direction","Time")
sc_tree = ttk.Treeview(t3,columns=sc_cols,show="headings",height=22)
for c in sc_cols:
    w = 130 if c in ("Symbol","Direction") else 90
    sc_tree.heading(c,text=c); sc_tree.column(c,width=w)
sc_sb = ttk.Scrollbar(t3,orient="vertical",command=sc_tree.yview)
sc_tree.configure(yscrollcommand=sc_sb.set)
sc_tree.pack(fill="both",expand=True,padx=(8,0),pady=(0,8),side="left")
sc_sb.pack(side="right",fill="y",pady=(0,8),padx=(0,8))
sc_tree.tag_configure("ce",  background="#0d2010",foreground=GRN)
sc_tree.tag_configure("pe",  background="#200d10",foreground=RED)
sc_tree.tag_configure("norm",background=S1,       foreground=TXT)

# ═══════════════════════════════════════════════
# TAB 4 — TRADE LOG
# ═══════════════════════════════════════════════
t4 = tk.Frame(nb,bg=BG); nb.add(t4,text="  Trades  ")
tr_top = tk.Frame(t4,bg=BG)
tr_top.pack(fill="x",padx=8,pady=(8,4))
btn_ref = _btn(tr_top,"Refresh",None,ACC,"#000",10)
btn_ref.pack(side="left",padx=4)

tr_cols = ("Time","OType","Dir","Strike","Spot","Opt Entry","Opt Exit","P&L","Reason")
tr_tree = ttk.Treeview(t4,columns=tr_cols,show="headings",height=22)
for c in tr_cols:
    w = 120 if c=="Time" else 50 if c in ("OType","Dir") else 80
    tr_tree.heading(c,text=c); tr_tree.column(c,width=w)
tr_sb = ttk.Scrollbar(t4,orient="vertical",command=tr_tree.yview)
tr_tree.configure(yscrollcommand=tr_sb.set)
tr_tree.pack(fill="both",expand=True,padx=(8,0),pady=(0,8),side="left")
tr_sb.pack(side="right",fill="y",pady=(0,8),padx=(0,8))
tr_tree.tag_configure("win", foreground=GRN)
tr_tree.tag_configure("loss",foreground=RED)

# ═══════════════════════════════════════════════
# TAB 5 — SETTINGS (sirf conditions)
# ═══════════════════════════════════════════════
t5 = tk.Frame(nb,bg=BG); nb.add(t5,text="  Settings  ")

sf = tk.LabelFrame(t5,text=" Trading Conditions ",bg=CARD,fg=ACC,
                   font=(FONT,10,"bold"),relief="flat")
sf.pack(side="left",padx=(10,4),pady=10,fill="y",ipadx=8,ipady=8)

v_ef  = tk.StringVar(value=str(CFG["EMA_FAST"]))
v_es  = tk.StringVar(value=str(CFG["EMA_SLOW"]))
v_eg  = tk.StringVar(value=str(CFG["EMA_GAP"]))
v_vp  = tk.StringVar(value=str(CFG["VOL_PERIOD"]))
v_vm  = tk.StringVar(value=str(CFG["VOL_MULT"]))
v_sl  = tk.StringVar(value=str(CFG["SL_PTS"]))
v_tsl = tk.StringVar(value=str(CFG["TSL_PTS"]))
v_tgt = tk.StringVar(value=str(CFG["TGT_PTS"]))
v_cap = tk.StringVar(value=str(CFG["PAPER_CAP"]))
v_both= tk.BooleanVar(value=CFG["BOTH_SIDE"])
v_voi = tk.BooleanVar(value=CFG["VOICE"])

fields = [
    ("EMA Fast",        v_ef),
    ("EMA Slow",        v_es),
    ("EMA Gap (pts)",   v_eg),
    ("Volume Period",   v_vp),
    ("Volume Mult",     v_vm),
    ("SL (pts)",        v_sl),
    ("TSL (pts)",       v_tsl),
    ("Target (pts)",    v_tgt),
    ("Paper Capital",   v_cap),
]
for i,(lbl_t,var) in enumerate(fields):
    tk.Label(sf,text=lbl_t,bg=CARD,fg=MUT,
             font=(FONT,9),width=18,anchor="w").grid(
        row=i,column=0,padx=(12,4),pady=4,sticky="w")
    _entry(sf,var,14).grid(row=i,column=1,padx=4,pady=4,sticky="w")

r = len(fields)
tk.Label(sf,text="Both Side CE+PE",bg=CARD,fg=MUT,
         font=(FONT,9)).grid(row=r,column=0,padx=(12,4),pady=4,sticky="w")
tk.Checkbutton(sf,variable=v_both,bg=CARD,activebackground=CARD,
               selectcolor=S1,fg=ACC).grid(row=r,column=1,sticky="w")

tk.Label(sf,text="Voice Alerts",bg=CARD,fg=MUT,
         font=(FONT,9)).grid(row=r+1,column=0,padx=(12,4),pady=4,sticky="w")
tk.Checkbutton(sf,variable=v_voi,bg=CARD,activebackground=CARD,
               selectcolor=S1,fg=ACC).grid(row=r+1,column=1,sticky="w")

btn_save = _btn(sf,"Save Settings",None,ACC,"#000",20)
btn_save.grid(row=r+2,column=0,columnspan=2,padx=12,pady=12,sticky="ew")

# Info box
ib = tk.Frame(t5,bg=CARD)
ib.pack(side="left",padx=(4,10),pady=10,fill="y",ipadx=10,ipady=10)
info_txt = (
    "AUTO SYSTEM:\n\n"
    "Data: Angel API se live\n"
    "Koi file nahi\n\n"
    "Future token:\n"
    "  Monthly auto-refresh\n\n"
    "Option token:\n"
    "  Weekly auto-refresh\n\n"
    "Volume:\n"
    "  Nifty Future se real\n\n"
    "Backtest:\n"
    "  Days field mein likho\n"
    "  Angel API se lega\n\n"
    "Sirf conditions\n"
    "yahan change karo"
)
tk.Label(ib,text=info_txt,bg=CARD,fg=TXT,
         font=(FONT,9),justify="left",anchor="nw").pack(padx=8,anchor="nw")

# ═══════════════════════════════════════════════
# TAB 6 — CREDENTIALS
# ═══════════════════════════════════════════════
t6 = tk.Frame(nb,bg=BG); nb.add(t6,text="  Credentials  ")
cf = tk.LabelFrame(t6,text=" API Credentials ",bg=CARD,fg=ACC,
                   font=(FONT,10,"bold"),relief="flat")
cf.pack(padx=20,pady=20,ipadx=12,ipady=12)

v_api  = tk.StringVar(value=CFG["API_KEY"])
v_cid  = tk.StringVar(value=CFG["CLIENT_ID"])
v_pwd  = tk.StringVar(value=CFG["PASSWORD"])
v_totp = tk.StringVar(value=CFG["TOTP"])
v_bot  = tk.StringVar(value=CFG["BOT_TOKEN"])
v_chat = tk.StringVar(value=CFG["CHAT_ID"])

creds = [
    ("API Key",     v_api,  False),
    ("Client ID",   v_cid,  False),
    ("Password",    v_pwd,  True),
    ("TOTP Secret", v_totp, False),
    ("Bot Token",   v_bot,  False),
    ("Chat ID",     v_chat, False),
]
for i,(lbl_t,var,hide) in enumerate(creds):
    tk.Label(cf,text=lbl_t,bg=CARD,fg=MUT,
             font=(FONT,9),width=14,anchor="w").grid(
        row=i,column=0,padx=(12,4),pady=6,sticky="w")
    e = tk.Entry(cf,textvariable=var,bg=S1,fg=ACC,
                 insertbackground=ACC,relief="flat",
                 font=(FONT,10),width=50,
                 highlightthickness=1,
                 highlightbackground=BDR,highlightcolor=ACC)
    if hide: e.config(show="*")
    e.grid(row=i,column=1,padx=4,pady=6,sticky="w")

cbf = tk.Frame(cf,bg=CARD)
cbf.grid(row=len(creds),column=0,columnspan=2,pady=12,padx=12,sticky="w")
btn_save_cred = _btn(cbf,"Save",None,ACC,"#000",10)
btn_save_cred.pack(side="left",padx=4)
btn_test_tg   = _btn(cbf,"Test TG",None,GOLD,"#000",10)
btn_test_tg.pack(side="left",padx=4)

# ═══════════════════════════════════════════════
# FUNCTIONS
# ═══════════════════════════════════════════════
_poll_started = [False]

def refresh_ui():
    today = [t for t in ST.trades
             if str(datetime.date.today()) in str(t.get("entry_time",""))]
    pnl   = sum(t.get("pnl",0) for t in today)
    wins  = sum(1 for t in today if t.get("pnl",0)>0)
    clr   = GRN if pnl>=0 else RED
    lbl_pnl.config(
        text=f"Today P&L\n{'+' if pnl>=0 else ''}Rs.{pnl:,.2f}", fg=clr)
    lbl_bal.config(text=f"Balance: Rs.{ST.balance:,.2f}")
    lbl_pos.config(text=f"Pos:{len(ST.positions)}  Trades:{len(today)}  W:{wins}")
    root.after(5000, refresh_ui)

def do_start():
    if ST.running:
        log("Already running!", "warn")
        return

    # Latest UI inputs ko CFG mein load karo
    CFG["SYMBOL"] = v_sym.get()
    CFG["MODE"]   = v_mode.get()
    ST.mode       = CFG["MODE"]

    # Credentials update karo UI se
    CFG["API_KEY"] = v_api.get()
    CFG["CLIENT_ID"] = v_cid.get()
    CFG["PASSWORD"] = v_pwd.get()
    CFG["TOTP"] = v_totp.get()

    if ST.mode == "live":
        if not messagebox.askyesno("LIVE MODE", "Real money involves risk! Proceed?"):
            return

    log("Logging into Angel One...", "info")
    if not angel_login():
        log("Login failed! Please check credentials.", "err")
        return

    log("Login Successful!", "sig")

    # Tokens ko refresh karna mandatory hai start par
    log("Refreshing tokens from API...", "info")
    if refresh_tokens(log, force=True):
        log("Tokens updated successfully.", "sig")
    else:
        log("Token refresh failed. Market data might be stale.", "err")

    ST.running = True
    btn_start.config(state="disabled")
    btn_stop.config(state="normal")

    # Telegram Polling start karo agar nahi hui hai
    if not _poll_started[0]:
        _poll_started[0] = True
        threading.Thread(target=poll_telegram, args=(log, do_start, do_stop), daemon=True).start()
        log("Telegram bot active.", "info")

    # Trading loop ko separate thread mein chalayein
    threading.Thread(target=trading_loop, args=(log,), daemon=True).start()

def do_backtest_auto():
    """Trading tab se backtest chalao."""
    sym  = CFG["SYMBOL"]
    days = 30
    bt_log.delete("1.0","end")
    trades = run_backtest(sym, days, log)
    _show_bt_results(trades, sym)
    ST.running = False
    root.after(0, lambda: btn_start.config(state="normal"))
    root.after(0, lambda: btn_stop.config(state="disabled"))
    root.after(0, lambda: lbl_run.config(text="DONE",fg=GOLD))

def do_stop():
    ST.running = False
    btn_start.config(state="normal")
    btn_stop.config(state="disabled")
    lbl_run.config(text="STOPPED",fg=RED)
    log("Trading stopped","warn")
    today = [t for t in ST.trades
             if str(datetime.date.today()) in str(t.get("entry_time",""))]
    pnl   = sum(t.get("pnl",0) for t in today)
    tg(f"Trading Stopped\nToday:{len(today)} trades P&L:Rs.{pnl:,.2f}")
    voice(f"Trading band. {abs(int(pnl))} rupaye {'faayda' if pnl>=0 else 'nuksan'}.")
    if today:
        f = make_pdf(today)
        tg_file(f, f"EOD | {datetime.date.today()}")
    root.after(500, refresh_ui)
    root.after(500, load_trades)

def do_tg_status():
    today = [t for t in ST.trades if str(datetime.date.today()) in str(t.get("entry_time",""))]
    pnl   = sum(t.get("pnl",0) for t in today)
    w     = sum(1 for t in today if t.get("pnl",0)>0)
    tg(f"Status\nMode:{ST.mode.upper()}\n"
       f"Running:{'YES' if ST.running else 'NO'}\n"
       f"Symbol:{CFG['SYMBOL']}\n"
       f"Today:{len(today)} W:{w} P&L:Rs.{pnl:,.2f}")
    log("TG status sent","sig")

def do_eod():
    send_eod_report(log)

def do_test_tg():
    tg("Test — Nifty Auto Trader OK")
    log("Test TG sent","sig")

def do_save_settings():
    try:
        CFG["EMA_FAST"]   = int(v_ef.get())
        CFG["EMA_SLOW"]   = int(v_es.get())
        CFG["EMA_GAP"]    = int(v_eg.get())
        CFG["VOL_PERIOD"] = int(v_vp.get())
        CFG["VOL_MULT"]   = float(v_vm.get())
        CFG["SL_PTS"]     = int(v_sl.get())
        CFG["TSL_PTS"]    = int(v_tsl.get())
        CFG["TGT_PTS"]    = int(v_tgt.get())
        CFG["PAPER_CAP"]  = int(v_cap.get())
        CFG["BOTH_SIDE"]  = v_both.get()
        CFG["VOICE"]      = v_voi.get()
        log("Settings saved!","sig")
        messagebox.showinfo("Saved","Settings save ho gayi!")
    except Exception as e:
        log(f"Settings error: {e}","err")

def do_save_creds():
    CFG["API_KEY"]   = v_api.get()
    CFG["CLIENT_ID"] = v_cid.get()
    CFG["PASSWORD"]  = v_pwd.get()
    CFG["TOTP"]      = v_totp.get()
    CFG["BOT_TOKEN"] = v_bot.get()
    CFG["CHAT_ID"]   = v_chat.get()
    log("Credentials saved!","sig")
    messagebox.showinfo("Saved","Credentials save ho gayi!")

# ── BACKTEST TAB ──────────────────────────────────────────────────────
def do_run_bt():
    sym  = v_bt_sym.get()
    days = int(v_bt_days.get() or 30)
    bt_log.delete("1.0","end")
    bt_write(f"Backtest: {sym} | {days} days | Angel API se live data")
    bt_write("-" * 50)

    def _run():
        if not ST.api:
            if not angel_login():
                bt_write("Login fail!"); return
            # Token refresh
            refresh_tokens(lambda m,t="": bt_write(m))

        trades = run_backtest(sym, days, lambda m,t="": bt_write(m))
        _show_bt_results(trades, sym)
        root.after(0, load_trades)

    threading.Thread(target=_run, daemon=True).start()

def _show_bt_results(trades, sym):
    if not trades:
        bt_write("\n0 trades hue! Settings check karo.")
        return
    pnl  = sum(t["pnl"] for t in trades)
    wins = sum(1 for t in trades if t["pnl"]>0)
    ce_c = sum(1 for t in trades if t.get("otype")=="CE")
    pe_c = sum(1 for t in trades if t.get("otype")=="PE")
    rate = wins/len(trades)*100

    # SUMMARY
    summary = (
        f"\n{'='*75}\n"
        f"  {sym} — BACKTEST RESULTS\n"
        f"{'='*75}\n"
        f"  Total Trades : {len(trades)}  |  CE: {ce_c}  PE: {pe_c}\n"
        f"  Wins: {wins}  |  Losses: {len(trades)-wins}  |  Win Rate: {rate:.1f}%\n"
        f"  Total P&L    : Rs.{pnl:,.2f}\n"
        f"  Settings: SL={CFG['SL_PTS']}pt TSL={CFG['TSL_PTS']}pt TGT={CFG['TGT_PTS']}pt EMA_GAP={CFG['EMA_GAP']}pt\n"
        f"{'='*75}\n\n"
    )
    bt_write(summary)

    # DETAILED TRADE LOG WITH TIMESTAMPS
    header = f"{'DATE':<12} {'TIME':<9} {'TYPE':<5} {'ACTION':<6} {'SPOT':<8} {'STRIKE':<7} {'PREMIUM':<8} {'P&L':<10} {'REASON':<20}"
    bt_write(header)
    bt_write("-" * 95)

    for t in trades:
        entry_dt = str(t.get("entry_time",""))
        exit_dt  = str(t.get("exit_time",""))
        otype    = t.get("otype","--")
        strike   = t.get("strike","--")
        spot_e   = t.get("spot_entry",0)
        spot_x   = t.get("spot_exit",0)
        opt_e    = t.get("opt_entry",0)
        opt_x    = t.get("opt_exit",0)
        p        = t.get("pnl",0)
        reason   = t.get("reason","")

        # Entry line
        if len(entry_dt) >= 19:
            date_str = entry_dt[:10]
            time_str = entry_dt[11:19]
        else:
            date_str = "--"
            time_str = "--"

        entry_line = f"{date_str:<12} {time_str:<9} {otype:<5} {'BUY':<6} {spot_e:>7.0f}  {int(strike):>6}  {opt_e:>7.1f}  {' ':>9} (entry)"
        bt_write(entry_line)

        # Exit line
        if len(exit_dt) >= 19:
            date_str = exit_dt[:10]
            time_str = exit_dt[11:19]
        else:
            date_str = "--"
            time_str = "--"

        p_str = f"Rs.{p:+.0f}"
        reason_short = reason[:18]
        exit_line = f"{date_str:<12} {time_str:<9} {otype:<5} {'SELL':<6} {spot_x:>7.0f}  {int(strike):>6}  {opt_x:>7.1f}  {p_str:>9}  {reason_short}"
        bt_write(exit_line)
        bt_write("")  # blank line between trades

    bt_write("\n" + "="*75 + "\n")
    fname = make_pdf(trades, f"backtest_{sym.replace(' ','_')}_{datetime.date.today()}.pdf")
    tg_file(fname, f"Backtest:{sym} P&L:Rs.{pnl:.0f}")
    log(f"Backtest done | {sym} | T:{len(trades)} W:{wins} P&L:Rs.{pnl:.0f}","sig")
    voice(f"{sym} backtest khatam. {len(trades)} trade. {abs(int(pnl))} rupaye {'faayda' if pnl>=0 else 'nuksan'}.")

def do_scan():
    log("Scanner chal raha hai...","warn")
    def _scan():
        if not ST.api:
            if not angel_login(): return
        results = []
        for sym, info in INSTRUMENTS.items():
            try:
                df = fetch_candles(info["spot_token"],info["exchange"],
                                   CFG["INTERVAL"], 3, sym)
                if df.empty or len(df) < CFG["EMA_SLOW"]+3:
                    results.append((sym,"-","-","--","--","--","-")); continue

                # Volume
                vol_df = pd.DataFrame()
                if sym in INDEX_SYMS:
                    ft, fe = get_future_token(sym)
                    if ft:
                        vol_df = fetch_candles(ft, fe, CFG["INTERVAL"], 3, f"{sym}_FUT")

                df   = calc_indicators(df, vol_df if not vol_df.empty else None)
                last = df.iloc[-1]
                sig  = dir_ = "--"
                if last["ce_sig"]:  sig,dir_ = "BUY CE","BULLISH"
                elif last["pe_sig"]:sig,dir_ = "BUY PE","BEARISH"
                results.append((
                    sym,
                    f"{last['close']:.0f}",
                    f"{last['ema_gap']:+.1f}",
                    "YES" if last["vol_ok"] else "NO",
                    sig, dir_,
                    datetime.datetime.now().strftime("%H:%M")
                ))
            except Exception as e:
                results.append((sym,"-","-","NO","ERR",str(e)[:20],"-"))

        root.after(0, lambda: render_scan(results))
        sigs = [r for r in results if "CE" in str(r[4]) or "PE" in str(r[4])]
        if sigs:
            msg = "SCANNER ALERT\n"
            for r in sigs:
                msg += f"{r[0]} -> {r[4]} Gap:{r[2]}\n"
            tg(msg)

    threading.Thread(target=_scan, daemon=True).start()

def render_scan(results):
    sc_tree.delete(*sc_tree.get_children())
    sigs = 0
    for r in sorted(results, key=lambda x: (x[4]=="--", x[0])):
        tag = "ce" if "CE" in str(r[4]) else "pe" if "PE" in str(r[4]) else "norm"
        if tag != "norm": sigs += 1
        sc_tree.insert("","end",values=r,tags=(tag,))
    lbl_scan.config(
        text=f"Last:{datetime.datetime.now().strftime('%H:%M:%S')} | {sigs} signals | {len(results)} scanned")
    log(f"Scan done | {sigs} signals","sig")

# ── TRADE LOG ─────────────────────────────────────────────────────────
def load_trades():
    tr_tree.delete(*tr_tree.get_children())
    for t in reversed(ST.trades[-100:]):
        p  = t.get("pnl",0)
        ot = t.get("otype","CE")
        tr_tree.insert("","end",values=(
            str(t.get("entry_time",""))[:16],
            ot,
            "Bull" if ot=="CE" else "Bear",
            str(t.get("strike","ATM")),
            f"{t.get('spot_entry',0):.0f}",
            f"Rs.{t.get('opt_entry',0):.2f}",
            f"Rs.{t.get('opt_exit',0):.2f}",
            f"Rs.{p:.2f}",
            t.get("reason",""),
        ), tags=("win" if p>=0 else "loss",))

# ── WIRE BUTTONS ──────────────────────────────────────────────────────
btn_start.config(command=do_start)
btn_stop.config( command=do_stop)
btn_bt.config(   command=do_run_bt)
btn_scan.config( command=do_scan)
btn_ref.config(  command=load_trades)
btn_save.config( command=do_save_settings)
btn_save_cred.config(command=do_save_creds)
btn_test_tg.config(  command=do_test_tg)

for w in lp.winfo_children():
    if isinstance(w, tk.Button):
        t = w.cget("text")
        if "Status" in t: w.config(command=do_tg_status)
        if "Report" in t: w.config(command=do_eod)
        if "Test"   in t: w.config(command=do_test_tg)

# ── START ─────────────────────────────────────────────────────────────
refresh_ui()
load_trades()
log("Ready! Symbol chuno -> Mode chuno -> START dabaao","sig")
log("Tokens auto-refresh honge (Future monthly, Option weekly)","info")
root.mainloop()

