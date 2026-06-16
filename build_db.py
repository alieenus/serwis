"""
build_db.py — JEDNORAZOWY skrypt budujący lokalną bazę danych SQLite
(dane_gpw.db) z ok. 2 lat dziennych notowań OHLCV dla wszystkich
spółek z available_tickers.csv.

Uruchamiasz GO LOKALNIE (tam gdzie yfinance działa), a powstały plik
dane_gpw.db wgrywasz do repozytorium GitHub razem z aplikacją.

Wymagania: pip install yfinance pandas
"""

import sqlite3
import time
import pandas as pd
import yfinance as yf

DB_PATH = "dane_gpw.db"
AVAILABLE_TICKERS_FILE = "available_tickers.csv"
OKRES = "2y"


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


def init_db(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS notowania (
            ticker TEXT NOT NULL,
            data   TEXT NOT NULL,
            open   REAL,
            high   REAL,
            low    REAL,
            close  REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, data)
        )
    """)
    con.commit()


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
    print(f"Wczytano {len(tickery)} tickerow.")

    con = sqlite3.connect(DB_PATH)
    init_db(con)

    ok, bledy = 0, 0
    for i, symbol in enumerate(tickery, 1):
        ticker_bare = symbol[:-3]  # usuń ".WA"
        try:
            df = yf.download(symbol, period=OKRES, interval="1d",
                              progress=False, auto_adjust=True)
            n = zapisz(con, ticker_bare, df)
            if n > 0:
                ok += 1
                print(f"[{i}/{len(tickery)}] {symbol}: zapisano {n} sesji")
            else:
                bledy += 1
                print(f"[{i}/{len(tickery)}] {symbol}: brak danych")
        except Exception as e:
            bledy += 1
            print(f"[{i}/{len(tickery)}] {symbol}: BLAD ({e})")
        time.sleep(0.3)  # nie obciążaj API za szybko

    con.close()
    print(f"\nGotowe. OK: {ok}, bez danych/błędów: {bledy}")
    print(f"Baza zapisana w: {DB_PATH}")


if __name__ == "__main__":
    main()
