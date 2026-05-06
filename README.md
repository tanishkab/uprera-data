# Nifty Auto Trader

Automated trading bot for NIFTY options using EMA crossover strategy.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Credentials
Edit `main_consolidated.py` lines 99-105 with your Angel One API credentials:
```python
"API_KEY":    "your_api_key",
"CLIENT_ID":  "your_client_id",
"PASSWORD":   "your_password",
"TOTP":       "your_totp_secret",
```

### 3. Run
```bash
python main_consolidated.py
```

## Features

- **3 Trading Modes**: Backtest, Paper (simulation), Live
- **Auto Token Refresh**: Future (monthly) and Options (weekly)
- **EMA Strategy**: 9/21 EMA crossover with volume confirmation
- **Risk Management**: Stop Loss, Trailing SL, Target points
- **Real-time Data**: Live market data from Angel One API
- **Telegram Alerts**: Optional trade notifications
- **PDF Reports**: Automated EOD reports

## Strategy

- **Entry**: EMA 9 crosses EMA 21 with minimum gap + volume filter
- **Exit**: Stop Loss, Trailing Stop Loss, or Target hit
- **Instruments**: NIFTY, BANKNIFTY, FINNIFTY, MIDCPNIFTY + stocks
- **Default**: Paper mode with Rs. 1,00,000 virtual capital

## GUI Tabs

1. **Trading** - Start/Stop, select symbol and mode
2. **Backtest** - Test on historical data (Angel API)
3. **Scanner** - Multi-instrument signal scanning
4. **Trades** - View trade history and P&L
5. **Settings** - Adjust EMA, SL, TSL, Target, Volume filters
6. **Credentials** - Update API keys and Telegram bot

## Safety

⚠️ **Default mode is PAPER (safe, no real orders)**

- Live mode requires manual confirmation
- Built-in risk management (SL/TSL/Target)
- Test thoroughly in Paper mode first

## Requirements

- Python 3.11+
- Angel One API account
- Internet connection
- macOS/Windows/Linux

## Files

- `main_consolidated.py` - Main application (single file)
- `requirements.txt` - Python dependencies
- `state.json` - Auto-saved state (created on first run)
- `trader.log` - Application logs (created on first run)

## Configuration

All settings in `main_consolidated.py` CFG dict:
```python
"EMA_FAST":   9,      # Fast EMA period
"EMA_SLOW":   21,     # Slow EMA period
"EMA_GAP":    2,      # Min gap for signal (points)
"SL_PTS":     30,     # Stop loss (points)
"TSL_PTS":    20,     # Trailing SL (points)
"TGT_PTS":    60,     # Target (points)
"PAPER_CAP":  100000, # Paper trading capital
```

## Troubleshooting

**macOS Tkinter Error**: Install Python 3.13 via Homebrew
```bash
brew install python@3.13
/opt/homebrew/bin/python3.13 main_consolidated.py
```

**Login Failed**: Check Angel One credentials and TOTP secret

**No Trades**: Adjust EMA_GAP, volume settings, or test different symbols

## Support

Check `trader.log` for detailed error messages.

---

**⚠️ Disclaimer**: For educational purposes. Test thoroughly before live trading. Trading involves risk.