"""
update_db.py — CODZIENNY skrypt dopisujący ostatnie notowania do bazy.
Uruchamiany automatycznie przez GitHub Actions po sesji GPW (ok. 18:00).
Pobiera ostatnie 10 dni dla każdego tickera i robi UPSERT (bez duplikatów).

Wymagania: pip install yfinance pandas
"""

import sqlite3
import time
import pandas as pd
import yfinance as yf

DB_PATH = "dane_gpw.db"
AVAILABLE_TICKERS_FILE = "available_tickers.csv"
DNI_WSTECZ = "10d"


def wczytaj_tickery(path=AVAILABLE_TICKERS_FILE):
    tickery = []
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            t = line.strip().upper()
            if not t or t == "TICKER":
                continue
            if not t.endswith(".WA"):
                t += ".WA"
            tickery.append(t)
    return tickery


def zapisz(con, ticker_bare, df):
    if df.empty:
        return 0
    df = df.copy()
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    rows = []
    for idx, row in df.iterrows():
        if pd.isna(row.get("Close")):
            continue
        rows.append((
            ticker_bare,
            idx.strftime("%Y-%m-%d"),
            float(row["Open"]) if not pd.isna(row.get("Open")) else None,
            float(row["High"]) if not pd.isna(row.get("High")) else None,
            float(row["Low"]) if not pd.isna(row.get("Low")) else None,
            float(row["Close"]),
            int(row["Volume"]) if not pd.isna(row.get("Volume")) else None,
        ))
    con.executemany(
        "INSERT OR REPLACE INTO notowania (ticker, data, open, high, low, close, volume) "
        "VALUES (?,?,?,?,?,?,?)",
        rows
    )
    con.commit()
    return len(rows)


def main():
    tickery = wczytaj_tickery()
    print(f"Aktualizacja {len(tickery)} tickerow (ostatnie {DNI_WSTECZ})...")

    con = sqlite3.connect(DB_PATH)

    ok, bledy = 0, 0
    for i, symbol in enumerate(tickery, 1):
        ticker_bare = symbol[:-3]
        try:
            df = yf.download(symbol, period=DNI_WSTECZ, interval="1d",
                              progress=False, auto_adjust=True)
            n = zapisz(con, ticker_bare, df)
            ok += 1
            print(f"[{i}/{len(tickery)}] {symbol}: +{n} rekordów")
        except Exception as e:
            bledy += 1
            print(f"[{i}/{len(tickery)}] {symbol}: BLAD ({e})")
        time.sleep(0.25)

    con.close()
    print(f"\nGotowe. Zaktualizowano: {ok}, błędy: {bledy}")


if __name__ == "__main__":
    main()
