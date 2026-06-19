import streamlit as st
import pandas as pd
import pandas_ta as ta
import sqlite3
import time
from datetime import datetime, date, timedelta

try:
    import yfinance as yf
    YFINANCE_OK = True
except ImportError:
    YFINANCE_OK = False

# ══════════════════════════════════════════════════════════════════════════════
# LISTA SPÓŁEK — parsowana z Twojego pliku
# ══════════════════════════════════════════════════════════════════════════════
LISTA_RAW = "###BIG60,GPW:11B,GPW:ABE,GPW:ACP,GPW:ALE,GPW:ALR,GPW:APR,GPW:ASB,GPW:ATT,GPW:BDX,GPW:BFT,GPW:BHW,GPW:BNP,GPW:CAR,GPW:CDR,GPW:CPS,GPW:DNP,GPW:DOM,GPW:DVL,GPW:EAT,GPW:ENA,GPW:EUR,GPW:GPW,GPW:ING,GPW:JSW,GPW:KGH,GPW:KRU,GPW:KTY,GPW:LPP,GPW:MAB,GPW:MBK,GPW:MIL,GPW:MRC,GPW:NEU,GPW:OPL,GPW:PCO,GPW:PEO,GPW:PEP,GPW:PGE,GPW:PKN,GPW:PKO,GPW:PKP,GPW:PZU,GPW:RBW,GPW:SLV,GPW:SNT,GPW:TEN,GPW:TPE,GPW:TXT,GPW:WPL,GPW:ZAB,###SWIG80,GPW:AGO,GPW:AMB,GPW:AMC,GPW:APT,GPW:ART,GPW:ASE,GPW:AST,GPW:ATC,GPW:ATD,GPW:BBT,GPW:BMC,GPW:BMX,GPW:BOS,GPW:BOW,GPW:BRS,GPW:CBF,GPW:CIG,GPW:CLN,GPW:COG,GPW:CRM,GPW:DAT,GPW:EAH,GPW:ENT,GPW:ERB,GPW:GEA,GPW:GPP,GPW:GRN,GPW:HUG,GPW:KER,GPW:LWB,GPW:MBR,GPW:MDV,GPW:MOC,GPW:MRB,GPW:NWG,GPW:OND,GPW:OPN,GPW:PCX,GPW:PLW,GPW:PXM,GPW:RVU,GPW:STP,GPW:STX,GPW:TOA,GPW:TOR,GPW:UNT,GPW:VGO,GPW:VOT,GPW:VOX,GPW:VRC,GPW:VRG,GPW:WWL,GPW:XTB,###GPW,GPW:06N,GPW:1AT,GPW:ACG,GPW:ACT,GPW:AGT,GPW:ALG,GPW:ANR,GPW:ATR,GPW:AWM,GPW:BCS,GPW:BCX,GPW:BIO,GPW:BLO,GPW:CLE,GPW:CPD,GPW:CRI,GPW:CRJ,GPW:CTX,GPW:DAD,GPW:DBC,GPW:DEL,GPW:DIA,GPW:DIG,GPW:ECH,GPW:ELT,GPW:ENG,GPW:ETL,GPW:FRO,GPW:FTE,GPW:GIF,GPW:GMT,GPW:GOP,GPW:GRX,GPW:GTN,GPW:HRP,GPW:IBS,GPW:ICE,GPW:IFI,GPW:IMS,GPW:IPE,GPW:IZO,GPW:IZS,GPW:JWW,GPW:KCH,GPW:KGN,GPW:KPL,GPW:KRK,GPW:KSG,GPW:KVT,GPW:LRQ,GPW:MAK,GPW:MCI,GPW:MDG,GPW:MFO,GPW:MLK,GPW:MLS,GPW:MON,GPW:MOV,GPW:MSW,GPW:MSZ,GPW:MZA,GPW:NTT,GPW:OPM,GPW:OTS,GPW:PBX,GPW:PCF,GPW:PCR,GPW:PEN,GPW:PRT,GPW:PTG,GPW:PUR,GPW:RLP,GPW:RNK,GPW:RWL,GPW:SCP,GPW:SEL,GPW:SGN,GPW:SHO,GPW:SIM,GPW:SKH,GPW:SNK,GPW:SNX,GPW:TRK,GPW:ULG,GPW:WLT,GPW:WPR,GPW:WTN,GPW:XTP,GPW:ZAP,GPW:ZEP,GPW:ZMT,GPW:ZRE,###NC,NEWCONNECT:ATA,NEWCONNECT:CHP,NEWCONNECT:ECT,NEWCONNECT:EXC,NEWCONNECT:F51,NEWCONNECT:GMV,NEWCONNECT:GTS,NEWCONNECT:GX1,NEWCONNECT:HOR,NEWCONNECT:HPM,NEWCONNECT:HUB,NEWCONNECT:INM,NEWCONNECT:IVO,NEWCONNECT:JJB,NEWCONNECT:KLE,NEWCONNECT:KLK,NEWCONNECT:KUB,NEWCONNECT:LCN,NEWCONNECT:LTM,NEWCONNECT:MNS,NEWCONNECT:MPY,NEWCONNECT:NOV,NEWCONNECT:ONE,NEWCONNECT:RSP,NEWCONNECT:RST,NEWCONNECT:SDS,NEWCONNECT:SOK,NEWCONNECT:STA,NEWCONNECT:SUN,NEWCONNECT:VEE"

def parsuj_liste(raw):
    """
    Zwraca:
      - spolki: list[dict]  z kluczami ticker, rynek, kategoria
      - kategorie: dict[nazwa] -> list[dict]
    """
    spolki = []
    kategorie = {}
    aktualna_kat = "Inne"
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if token.startswith("###"):
            aktualna_kat = token[3:].strip()
            kategorie.setdefault(aktualna_kat, [])
            continue
        if ":" not in token:
            continue
        prefix, ticker = token.split(":", 1)
        ticker = ticker.strip().upper()
        if prefix == "GPW":
            rynek = "GPW"
        elif prefix in ("NEWCONNECT", "NC"):
            rynek = "NC"
        else:
            rynek = prefix
        rec = {"ticker": ticker, "rynek": rynek, "kategoria": aktualna_kat}
        spolki.append(rec)
        kategorie.setdefault(aktualna_kat, []).append(rec)
    return spolki, kategorie

WSZYSTKIE_SPOLKI, KATEGORIE = parsuj_liste(LISTA_RAW)
TICKER_INFO = {s["ticker"]: s for s in WSZYSTKIE_SPOLKI}  # szybki lookup

# ══════════════════════════════════════════════════════════════════════════════
# LISTA SPÓŁEK DOSTĘPNYCH NA YFINANCE (gpw.csv, nc.csv, available_tickers.csv)
# ══════════════════════════════════════════════════════════════════════════════
def wczytaj_tickery_z_pliku(path):
    """Wczytuje tickery z prostego CSV (jedna kolumna, bez .WA)."""
    tickery = set()
    try:
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                t = line.strip().upper()
                if t and t.lower() != "ticker":
                    tickery.add(t)
    except FileNotFoundError:
        pass
    return tickery

def wczytaj_dostepne_yfinance(avail_path="available_tickers.csv",
                               gpw_path="gpw.csv", nc_path="nc.csv"):
    """
    Zwraca listę słowników {ticker, rynek} na podstawie available_tickers.csv
    (kolumna 'ticker' z sufiksem .WA). Rynek (GPW/NC) ustalany jest:
    1) na podstawie WSZYSTKIE_SPOLKI (lista wbudowana), a jeśli nie znaleziono,
    2) na podstawie przynależności do gpw.csv / nc.csv (jeśli pliki obecne).
    """
    gpw_set = wczytaj_tickery_z_pliku(gpw_path)
    nc_set  = wczytaj_tickery_z_pliku(nc_path)

    spolki = []
    try:
        with open(avail_path, encoding="utf-8-sig") as f:
            for line in f:
                t = line.strip().upper()
                if not t or t == "TICKER":
                    continue
                t_bare = t[:-3] if t.endswith(".WA") else t  # usuń sufiks .WA
                rynek = TICKER_INFO.get(t_bare, {}).get("rynek")
                if not rynek:
                    if t_bare in gpw_set:
                        rynek = "GPW"
                    elif t_bare in nc_set:
                        rynek = "NC"
                    else:
                        rynek = "?"
                spolki.append({"ticker": t_bare, "rynek": rynek})
    except FileNotFoundError:
        pass
    return spolki

DOSTEPNE_YFINANCE = wczytaj_dostepne_yfinance()

# ══════════════════════════════════════════════════════════════════════════════
# BAZA DANYCH
# ══════════════════════════════════════════════════════════════════════════════
def init_db():
    con = sqlite3.connect("gpw.db")
    con.execute("""
        CREATE TABLE IF NOT EXISTS notatki (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker  TEXT,
            data    TEXT,
            tresc   TEXT
        )
    """)
    con.commit()
    return con

con = init_db()

# ══════════════════════════════════════════════════════════════════════════════
# DANE NOTOWAŃ — czytane z lokalnej bazy SQLite (dane_gpw.db)
# Baza jest budowana/aktualizowana przez build_db.py / update_db.py
# (patrz INSTRUKCJA.md). Aplikacja NIE łączy się z yfinance.
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_resource
def get_dane_con():
    return sqlite3.connect("dane_gpw.db", check_same_thread=False)

@st.cache_data(ttl=3600)
def wczytaj_notowania(ticker):
    """Wczytuje pełną historię dziennych notowań dla tickera z bazy lokalnej."""
    con_d = get_dane_con()
    try:
        df = pd.read_sql(
            "SELECT data, open, high, low, close, volume "
            "FROM notowania WHERE ticker=? ORDER BY data",
            con_d, params=(ticker.upper(),)
        )
    except Exception:
        return pd.DataFrame(columns=["Open","High","Low","Close","Volume"])
    if df.empty:
        return pd.DataFrame(columns=["Open","High","Low","Close","Volume"])
    df["data"] = pd.to_datetime(df["data"])
    df = df.set_index("data").sort_index()
    df.columns = ["Open","High","Low","Close","Volume"]
    return df

def aktualizuj_baze_na_zywo(lista_tickerow, pasek=None):
    """
    Próbuje pobrać ostatnie notowania (10 dni) z yfinance dla podanej listy
    tickerów i zapisać/nadpisać je w lokalnej bazie dane_gpw.db (UPSERT).
    Zwraca (ok, bledy, pierwszy_blad_tekst).
    Uwaga: zadziała tylko jeśli serwer hostingu ma dostęp sieciowy do Yahoo
    Finance — może nie działać na każdym hostingu (np. Streamlit Cloud blokuje).
    """
    if not YFINANCE_OK:
        return 0, len(lista_tickerow), "Biblioteka yfinance nie jest zainstalowana na serwerze."

    con_d = get_dane_con()
    ok, bledy = 0, 0
    pierwszy_blad = None
    for i, ticker in enumerate(lista_tickerow):
        if pasek is not None:
            pasek.progress((i+1)/max(len(lista_tickerow),1),
                           text=f"Aktualizuję: {ticker} ({i+1}/{len(lista_tickerow)})")
        symbol = ticker.upper() + ".WA"
        try:
            df = yf.download(symbol, period="10d", interval="1d",
                              progress=False, auto_adjust=True)
            df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            if df.empty:
                continue
            rows = []
            for idx, row in df.iterrows():
                if pd.isna(row.get("Close")):
                    continue
                rows.append((
                    ticker.upper(),
                    idx.strftime("%Y-%m-%d"),
                    float(row["Open"]) if not pd.isna(row.get("Open")) else None,
                    float(row["High"]) if not pd.isna(row.get("High")) else None,
                    float(row["Low"]) if not pd.isna(row.get("Low")) else None,
                    float(row["Close"]),
                    int(row["Volume"]) if not pd.isna(row.get("Volume")) else None,
                ))
            con_d.executemany(
                "INSERT OR REPLACE INTO notowania (ticker, data, open, high, low, close, volume) "
                "VALUES (?,?,?,?,?,?,?)",
                rows
            )
            con_d.commit()
            ok += 1
        except Exception as e:
            bledy += 1
            if pierwszy_blad is None:
                pierwszy_blad = str(e)
    return ok, bledy, pierwszy_blad

def pobierz_dane(ticker, period="2y", interval="1d", data_koniec=None):
    """
    Zwraca DataFrame OHLCV (kolumny Open/High/Low/Close/Volume, index = daty)
    z lokalnej bazy dane_gpw.db. 'period' jest tu tylko orientacyjne — baza
    zawiera ok. 2 lat historii, co dla danych tygodniowych daje ~100 tygodni.
    """
    df = wczytaj_notowania(ticker)
    if df.empty:
        return df

    if data_koniec:
        df = df[df.index.date <= data_koniec]

    if interval == "1wk":
        df = df.resample("W-FRI").agg({
            "Open": "first", "High": "max", "Low": "min",
            "Close": "last", "Volume": "sum",
        }).dropna(subset=["Close"])

    return df.copy()

def licz_adr(df, okresy=20):
    """Average Daily Range — średni zakres dzienny z ostatnich N sesji (w %)."""
    df = df.copy()
    high = df["High"].astype(float)
    low  = df["Low"].astype(float)
    close_prev = df["Close"].shift(1).astype(float)
    # zakres jako % ceny zamknięcia poprzedniej sesji
    daily_range_pct = (high - low) / close_prev * 100
    df["ADR20"] = daily_range_pct.rolling(window=okresy).mean()
    return df

def licz_wskazniki(df):
    df = df.copy()
    df["RSI"]        = ta.rsi(df["Close"], length=14)
    df["EMA10"]      = ta.ema(df["Close"], length=10)
    df["EMA20"]      = ta.ema(df["Close"], length=20)
    df["EMA50"]      = ta.ema(df["Close"], length=50)
    df["EMA150"]     = ta.ema(df["Close"], length=150)
    df["EMA200"]     = ta.ema(df["Close"], length=200)
    df["VOL_AVG60"]  = df["Volume"].rolling(window=60).mean()
    df["VOL_AVG24M"] = df["Volume"].rolling(window=504).mean()
    macd = ta.macd(df["Close"])
    if macd is not None:
        df["MACD"]   = macd.iloc[:, 0]
        df["SIGNAL"] = macd.iloc[:, 1]
    adx = ta.adx(df["High"], df["Low"], df["Close"], length=14)
    if adx is not None:
        df["ADX14"] = adx.iloc[:, 0]
        df["DMP14"] = adx.iloc[:, 1]  # +DI
        df["DMN14"] = adx.iloc[:, 2]  # -DI
    return df

def licz_wskazniki_tygodniowe(df):
    df = df.copy()
    df["VOL_AVG52W"] = df["Volume"].rolling(window=52).mean()
    return df

# ══════════════════════════════════════════════════════════════════════════════
# WARUNKI SKANERA
# ══════════════════════════════════════════════════════════════════════════════
def sprawdz_ema_warunki(row, w1, w2, w_ema20_50, w3):
    wyniki = []
    if w1:
        wyniki.append(not pd.isna(row.get("EMA10")) and not pd.isna(row.get("EMA20"))
                      and row["EMA10"] > row["EMA20"])
    if w2:
        wyniki.append(not pd.isna(row.get("EMA50")) and not pd.isna(row.get("EMA150"))
                      and row["EMA50"] > row["EMA150"])
    if w_ema20_50:
        e20, e50 = row.get("EMA20"), row.get("EMA50")
        if not pd.isna(e20) and not pd.isna(e50) and e50 != 0:
            wyniki.append(abs(e20 - e50) / e50 * 100 <= 0.5)
        else:
            wyniki.append(False)
    if w3:
        e150, e200 = row.get("EMA150"), row.get("EMA200")
        if not pd.isna(e150) and not pd.isna(e200) and e200 != 0:
            wyniki.append(abs(e150 - e200) / e200 * 100 <= 0.5)
        else:
            wyniki.append(False)
    return all(wyniki) if wyniki else True

def sprawdz_wolumen_dzienny(row, uzyj, mnoznik):
    if not uzyj: return True
    vol, avg = row.get("Volume"), row.get("VOL_AVG60")
    if pd.isna(vol) or pd.isna(avg) or avg == 0: return False
    return float(vol) >= mnoznik * float(avg)

def sprawdz_wolumen_tygodniowy(row, uzyj, mnoznik):
    if not uzyj: return True
    vol, avg = row.get("Volume"), row.get("VOL_AVG52W")
    if pd.isna(vol) or pd.isna(avg) or avg == 0: return False
    return float(vol) >= mnoznik * float(avg)

def pobierz_ref_kurs(ref, row_d, row_w, df_d):
    """Zwraca wartość referencyjną dla warunku kursu lub None jeśli niedostępna."""
    ref = ref.upper().strip()
    # EMA-y są dostępne z danych dziennych
    if ref in ("EMA10", "EMA20", "EMA50", "EMA150", "EMA200"):
        val = row_d.get(ref)
        return float(val) if val is not None and not pd.isna(val) else None
    return None

def sprawdz_warunek_kurs(uzyj, okres, relacja, ref, row_d, row_w, df_d):
    """Sprawdza pojedynczy warunek kursu. Zwraca True jeśli warunek spełniony lub nieaktywny."""
    if not uzyj:
        return True
    # Wybierz kurs wg okresu
    if okres == "D":
        if len(df_d) < 1: return False
        kurs = float(df_d["Close"].iloc[-1])
    elif okres == "T":
        if len(df_d) < 5: return False
        kurs = float(df_d["Close"].iloc[-5])
    elif okres == "M":
        if len(df_d) < 20: return False
        kurs = float(df_d["Close"].iloc[-20])
    else:
        return False
    ref_val = pobierz_ref_kurs(ref, row_d, row_w, df_d)
    if ref_val is None: return False
    TOL = 0.001  # tolerancja dla "równy" (~0.1%)
    if relacja == "powyżej":
        return kurs > ref_val
    elif relacja == "poniżej":
        return kurs < ref_val
    elif relacja == "równy":
        return abs(kurs - ref_val) / ref_val <= TOL if ref_val != 0 else False
    return False

def wykryj_crossover_ema(df, ema_szybka="EMA20", ema_wolna="EMA50",
                          data_od=None, data_do=None):
    """
    Sprawdza przeciecie dwóch wskazanych EMA.
    Jesli data_od/data_do podane, przeszukuje caly ten zakres kalendarzowy
    i zwraca (kierunek, data_sygnalu) dla NAJNOWSZEGO znalezionego przeciecia.
    Jesli nie podane, sprawdza tylko ostatnia sesje vs poprzednia.
    Zwraca: (kierunek, data) gdzie kierunek to "up"/"down"/None,
            data to obiekt date sygnalu (lub None jesli brak).
    """
    f = df[ema_szybka]
    w = df[ema_wolna]
    if data_od is not None and data_do is not None:
        maska = (df.index.date >= data_od) & (df.index.date <= data_do)
        indeksy = [i for i in range(1, len(df)) if maska[i]]
    else:
        indeksy = [len(df) - 1] if len(df) >= 2 else []

    for i in reversed(indeksy):  # od najnowszego do najstarszego
        f_now, w_now   = f.iloc[i],   w.iloc[i]
        f_prev, w_prev = f.iloc[i-1], w.iloc[i-1]
        if pd.isna(f_now) or pd.isna(w_now) or pd.isna(f_prev) or pd.isna(w_prev):
            continue
        if f_prev <= w_prev and f_now > w_now:
            return "up", df.index[i].date()
        if f_prev >= w_prev and f_now < w_now:
            return "down", df.index[i].date()
    return None, None

def wykryj_crossover_dmi(df, n_sesji=2):
    """
    Sprawdza, czy w ostatnich n_sesji nastapilo przeciecie +DI od dolu przez -DI
    (czyli +DI <= -DI w sesji poprzedniej, a +DI > -DI w sesji biezacej -
    sygnal "Positive -> Negative" / bycze przeciecie DMI).
    Zwraca (True/False, data_sygnalu) dla NAJNOWSZEGO znalezionego przeciecia
    w zakresie ostatnich n_sesji.
    """
    if "DMP14" not in df.columns or "DMN14" not in df.columns:
        return False, None
    if len(df) < n_sesji + 1:
        return False, None
    p = df["DMP14"]
    n = df["DMN14"]
    for i in range(len(df) - 1, len(df) - 1 - n_sesji, -1):
        if i < 1:
            break
        p_now, n_now   = p.iloc[i],   n.iloc[i]
        p_prev, n_prev = p.iloc[i-1], n.iloc[i-1]
        if pd.isna(p_now) or pd.isna(n_now) or pd.isna(p_prev) or pd.isna(n_prev):
            continue
        if p_prev <= n_prev and p_now > n_now:
            return True, df.index[i].date()
    return False, None

def kurs_na_poczatek_okresu(df, data_referencyjna, okres):
    """
    Zwraca kurs zamknięcia z ostatniej sesji PRZED początkiem bieżącego
    okresu kalendarzowego (tydzien: od poniedziałku; miesiac: od 1-go dnia).
    Jeśli takiej sesji nie ma w danych (za krótka historia), zwraca None.
    """
    if okres == "tydzien":
        poczatek = data_referencyjna - timedelta(days=data_referencyjna.weekday())  # poniedziałek
    else:  # miesiac
        poczatek = data_referencyjna.replace(day=1)

    df_przed = df[df.index.date < poczatek]
    if df_przed.empty:
        return None
    return float(df_przed["Close"].iloc[-1])

def wykryj_doji(row, tolerancja_pct=0.1):
    h, l = float(row["High"]), float(row["Low"])
    zakres = h - l
    if zakres == 0: return False
    return (abs(float(row["Close"]) - float(row["Open"])) / zakres) <= tolerancja_pct

def wykryj_bycza_swiece(row, min_body_pct=3.0, max_dolny_cien_pct=30.0):
    o, c, h, l = float(row["Open"]), float(row["Close"]), float(row["High"]), float(row["Low"])
    if c <= o: return False
    body = c - o
    zakres_od_low = c - l
    if zakres_od_low == 0: return False
    body_pct  = body / zakres_od_low * 100
    cien_pct  = (o - l) / body * 100 if body > 0 else 999
    return body_pct >= min_body_pct and cien_pct <= max_dolny_cien_pct

# ══════════════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="Moj serwis GPW", layout="wide")

_ostatnia_pkn = wczytaj_notowania("PKN")
if not _ostatnia_pkn.empty:
    _data_bazy = _ostatnia_pkn.index[-1].date()
    _roznica = (date.today() - _data_bazy).days
    _kolor = "🟢" if _roznica <= 1 else ("🟡" if _roznica <= 4 else "🔴")
    _godzina_info = ""
    if st.session_state.get("ostatnia_aktualizacja_godz"):
        _godzina_info = f" ({st.session_state['ostatnia_aktualizacja_godz']})"
    st.sidebar.caption(f"{_kolor} Dane w bazie: {_data_bazy.strftime('%d.%m.%Y')}{_godzina_info}")
else:
    st.sidebar.caption("🔴 Brak danych w bazie")

if st.sidebar.button("🔄 Aktualizuj teraz (na żywo)", use_container_width=True):
    lista_live = [s["ticker"] for s in DOSTEPNE_YFINANCE]
    total_live = len(lista_live)
    pasek_live = st.sidebar.progress(0, text=f"Łączenie z Yahoo Finance (0/{total_live})...")
    ok_live, bledy_live, blad_txt = aktualizuj_baze_na_zywo(lista_live, pasek_live)
    pasek_live.empty()
    wczytaj_notowania.clear()
    if ok_live > 0:
        st.session_state["ostatnia_aktualizacja_godz"] = datetime.now().strftime("%H:%M")
        st.session_state["live_update_komunikat"] = ("success", f"Zaktualizowano {ok_live} z {total_live} tickerów ({bledy_live} błędów).")
        st.rerun()
    else:
        st.session_state["live_update_komunikat"] = ("error", f"Nie udało się połączyć z Yahoo Finance z tego serwera. Błąd: {blad_txt or 'brak danych'}")
        st.rerun()

if st.session_state.get("live_update_komunikat"):
    _typ, _tekst = st.session_state.pop("live_update_komunikat")
    getattr(st.sidebar, _typ)(_tekst)

nav = st.sidebar.radio("", ["🔍 Spolka", "📋 Baza", "⭐ Top Lista", "📡 Skaner"])

# ══════════════════════════════════════════════════════════════════════════════
# ZAKŁADKA 1 — SPÓŁKA
# ══════════════════════════════════════════════════════════════════════════════
if nav == "🔍 Spolka":
    st.header("Karta spolki")
    ticker = st.text_input("Wpisz ticker (bez .WA):", placeholder="np. CDR, PKN")

    if ticker:
        info = TICKER_INFO.get(ticker.upper(), {})
        if info:
            st.caption(f"Rynek: **{info['rynek']}** | Kategoria: *{info['kategoria']}*")

        with st.spinner("Pobieram dane..."):
            df   = pobierz_dane(ticker, period="2y", interval="1d")
            df_w = pobierz_dane(ticker, period="5y", interval="1wk")

        if df.empty:
            st.error("Nie znaleziono danych. Sprawdz ticker.")
        else:
            df   = licz_wskazniki(df)
            df_w = licz_wskazniki_tygodniowe(df_w)
            ostatni   = df.iloc[-1]
            ostatni_w = df_w.iloc[-1]

            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("Kurs",     f"{ostatni['Close']:.2f} zl")
            col2.metric("RSI (14)", f"{ostatni['RSI']:.1f}"   if not pd.isna(ostatni['RSI'])   else "-")
            col3.metric("EMA10",    f"{ostatni['EMA10']:.2f}" if not pd.isna(ostatni['EMA10']) else "-")
            col4.metric("EMA20",    f"{ostatni['EMA20']:.2f}" if not pd.isna(ostatni['EMA20']) else "-")
            col5.metric("EMA50",    f"{ostatni['EMA50']:.2f}" if not pd.isna(ostatni['EMA50']) else "-")

            col6, col7, col8, col9 = st.columns(4)
            col6.metric("EMA150",      f"{ostatni['EMA150']:.2f}"       if not pd.isna(ostatni['EMA150'])     else "-")
            col7.metric("EMA200",      f"{ostatni['EMA200']:.2f}"       if not pd.isna(ostatni['EMA200'])     else "-")
            col8.metric("Wolumen D",   f"{int(ostatni['Volume']):,}"    if not pd.isna(ostatni['Volume'])     else "-")
            col9.metric("Sr. vol 60D", f"{int(ostatni['VOL_AVG60']):,}" if not pd.isna(ostatni['VOL_AVG60']) else "-")

            col10, col11 = st.columns(2)
            col10.metric("Wolumen W",   f"{int(ostatni_w['Volume']):,}"     if not pd.isna(ostatni_w.get('Volume', float('nan')))     else "-")
            col11.metric("Sr. vol 52W", f"{int(ostatni_w['VOL_AVG52W']):,}" if not pd.isna(ostatni_w.get('VOL_AVG52W', float('nan'))) else "-")

            if not pd.isna(ostatni["Volume"]) and not pd.isna(ostatni["VOL_AVG60"]) and ostatni["VOL_AVG60"] > 0:
                kd = float(ostatni["Volume"]) / float(ostatni["VOL_AVG60"])
                if kd >= 2:
                    st.info(f"Wolumen dzienny: **{kd:.1f}x** sredniej z 60 sesji")
            vw = ostatni_w.get("Volume", float("nan"))
            aw = ostatni_w.get("VOL_AVG52W", float("nan"))
            if not pd.isna(vw) and not pd.isna(aw) and aw > 0:
                kw = float(vw) / float(aw)
                if kw >= 2:
                    st.info(f"Wolumen tygodniowy: **{kw:.1f}x** sredniej z 52 tygodni")

            st.subheader("Warunki EMA")
            c1, c2, c3, c4 = st.columns(4)
            e10  = ostatni.get("EMA10")
            e20  = ostatni.get("EMA20")
            e50  = ostatni.get("EMA50")
            e150 = ostatni.get("EMA150")
            e200 = ostatni.get("EMA200")
            with c1:
                if not pd.isna(e10) and not pd.isna(e20):
                    if float(e10) > float(e20):
                        st.success("✅ EMA10 > EMA20")
                    else:
                        st.error("❌ EMA10 ≤ EMA20")
            with c2:
                if not pd.isna(e50) and not pd.isna(e150):
                    if float(e50) > float(e150):
                        st.success("✅ EMA50 > EMA150")
                    else:
                        st.error("❌ EMA50 ≤ EMA150")
            with c3:
                if not pd.isna(e20) and not pd.isna(e50) and float(e50) != 0:
                    odch_20_50 = (float(e20) - float(e50)) / float(e50) * 100
                    if abs(odch_20_50) <= 0.5:
                        st.success(f"✅ EMA20 ≈ EMA50 ({odch_20_50:+.2f}%)")
                    else:
                        st.warning(f"⚠️ EMA20 vs EMA50: {odch_20_50:+.2f}%")
            with c4:
                if not pd.isna(e150) and not pd.isna(e200) and float(e200) != 0:
                    odch = (float(e150) - float(e200)) / float(e200) * 100
                    if odch >= 0:
                        st.success(f"↑ EMA150 powyżej EMA200 o +{odch:.2f}%")
                    else:
                        st.error(f"↓ EMA150 poniżej EMA200 o {odch:.2f}%")

            st.subheader("Wykres kursu + EMA")
            st.line_chart(df[["Close","EMA10","EMA20","EMA50","EMA150","EMA200"]].dropna(), height=280)

            st.subheader("RSI (14)")
            st.line_chart(df[["RSI"]].dropna(), height=160)
            if not pd.isna(ostatni["RSI"]):
                if ostatni["RSI"] < 30:
                    st.warning("RSI ponizej 30 - strefa wyprzedania")
                elif ostatni["RSI"] > 70:
                    st.warning("RSI powyzej 70 - strefa wykupienia")

            st.subheader("Wolumen dzienny (ostatnie 60 sesji)")
            st.bar_chart(df[["Volume"]].tail(60), height=180)

            st.subheader("Wolumen tygodniowy (ostatnie 52 tygodnie)")
            st.bar_chart(df_w[["Volume"]].tail(52), height=180)

            st.subheader("MACD")
            if "MACD" in df.columns:
                st.line_chart(df[["MACD","SIGNAL"]].dropna(), height=160)

            st.divider()
            st.subheader("Notatki")
            nowa = st.text_area("Dodaj przemyslenie:")
            if st.button("Zapisz notatke"):
                if nowa.strip():
                    con.execute(
                        "INSERT INTO notatki (ticker, data, tresc) VALUES (?,?,?)",
                        (ticker.upper(), datetime.now().strftime("%Y-%m-%d %H:%M"), nowa)
                    )
                    con.commit()
                    st.success("Zapisano!")
            notatki = pd.read_sql(
                "SELECT data, tresc FROM notatki WHERE ticker=? ORDER BY id DESC",
                con, params=(ticker.upper(),)
            )
            for _, row in notatki.iterrows():
                with st.expander(f"{row['data']}"):
                    st.write(row["tresc"])

# ══════════════════════════════════════════════════════════════════════════════
# ZAKŁADKA 2 — MOJE SPÓŁKI
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "📋 Baza":
    st.header("Moje spolki — lista i status danych")
    st.caption(f"Lacznie: {len(WSZYSTKIE_SPOLKI)} spolek z Twojej listy")

    if st.button("🔄 Sprawdz status danych w lokalnej bazie"):
        con_d = get_dane_con()
        try:
            status_df = pd.read_sql(
                "SELECT ticker, COUNT(*) AS n, MAX(data) AS ostatnia FROM notowania GROUP BY ticker",
                con_d
            )
            status_map = {
                row["ticker"]: (int(row["n"]), row["ostatnia"])
                for _, row in status_df.iterrows()
            }
        except Exception:
            status_map = {}

        wyniki_check = []
        for s in WSZYSTKIE_SPOLKI:
            info = status_map.get(s["ticker"])
            if info is None:
                status = "❌ Brak danych w bazie"
            else:
                n, ostatnia = info
                status = f"✅ OK ({ostatnia}, {n} sesji)"
            wyniki_check.append({
                "Ticker":     s["ticker"],
                "Gielda":     s["rynek"],
                "Kategoria":  s["kategoria"],
                "Status":     status,
            })
        st.session_state["check_wyniki"] = wyniki_check

    # pokaż tabelę — z podziałem na kategorie
    dane_do_pokazania = st.session_state.get("check_wyniki", None)

    if dane_do_pokazania:
        df_check = pd.DataFrame(dane_do_pokazania)
        for kat in KATEGORIE.keys():
            df_kat = df_check[df_check["Kategoria"] == kat]
            if df_kat.empty:
                continue
            ok    = (df_kat["Status"].str.startswith("✅")).sum()
            brak  = len(df_kat) - ok
            st.subheader(f"{kat}  —  {len(df_kat)} spółek  |  ✅ {ok}  ❌ {brak}")
            st.dataframe(df_kat[["Ticker","Gielda","Status"]], use_container_width=True, hide_index=True)
    else:
        # bez sprawdzania — pokaż samą listę
        for kat, spol in KATEGORIE.items():
            st.subheader(f"{kat}  ({len(spol)} spółek)")
            df_kat = pd.DataFrame(spol)[["ticker","rynek","kategoria"]]
            df_kat.columns = ["Ticker","Gielda","Kategoria"]
            st.dataframe(df_kat[["Ticker","Gielda"]], use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# ZAKŁADKA 3 — TOP (najbardziej rosnące / spadające w 5 sesji)
# ══════════════════════════════════════════════════════════════════════════════
elif nav == "⭐ Top Lista":
    st.header("Top — gotowe listy")

    if "top_widok" not in st.session_state:
        st.session_state["top_widok"] = None

    col_b1, col_b2, col_b3 = st.columns(3)
    with col_b1:
        if st.button("📊 Naj/Naj", use_container_width=True):
            st.session_state["top_widok"] = "naj_naj"
    with col_b2:
        if st.button("🔀 Cross 20/50 (3 sesje)", use_container_width=True):
            st.session_state["top_widok"] = "cross_20_50"
    with col_b3:
        if st.button("📐 ADX/DMI + EMA50 (2 sesje)", use_container_width=True):
            st.session_state["top_widok"] = "adx_dmi_ema50"

    st.markdown("---")

    # ── LISTA 1: NAJ/NAJ ──────────────────────────────────────────────
    if st.session_state["top_widok"] == "naj_naj":
        st.subheader("Top 10 — zmiana w ostatnich 5 sesjach")
        st.caption("Bazuje na liście all GPW+NC (yfinance)")

        wyniki_top = []
        pasek_top = st.progress(0, text="Liczenie zmian...")
        lista_top = DOSTEPNE_YFINANCE
        for i, s in enumerate(lista_top):
            pasek_top.progress((i+1)/max(len(lista_top),1), text=f"Sprawdzam: {s['ticker']}")
            df_t = wczytaj_notowania(s["ticker"])
            if len(df_t) < 6:
                continue
            k_teraz = float(df_t["Close"].iloc[-1])
            k_5sesji = float(df_t["Close"].iloc[-6])
            if k_5sesji == 0:
                continue
            zmiana = (k_teraz - k_5sesji) / k_5sesji * 100
            wyniki_top.append({
                "Ticker": s["ticker"],
                "Gielda": {"GPW": "G", "NC": "N"}.get(s["rynek"], s["rynek"]),
                "Kurs": k_teraz,
                "Zmiana 5D (%)": zmiana,
            })
        pasek_top.empty()

        if not wyniki_top:
            st.warning("Brak danych do obliczenia (sprawdz baze dane_gpw.db).")
        else:
            df_top = pd.DataFrame(wyniki_top)
            top_rosnace  = df_top.sort_values("Zmiana 5D (%)", ascending=False).head(10).reset_index(drop=True)
            top_spadajace = df_top.sort_values("Zmiana 5D (%)", ascending=True).head(10).reset_index(drop=True)

            def styl_top(df_, kolor):
                return (
                    df_.style
                    .format({"Kurs": "{:.3f}", "Zmiana 5D (%)": "{:+.1f}%"})
                    .apply(lambda col: [f"color: {kolor}; font-weight:600" if col.name=="Zmiana 5D (%)" else "" for _ in col], axis=0)
                )

            col_lewa, col_sep, col_prawa = st.columns([10, 1, 10])
            with col_lewa:
                st.subheader("📈 Najbardziej rosnące")
                st.dataframe(styl_top(top_rosnace, "#4ade80"), use_container_width=True, hide_index=True)
            with col_sep:
                st.markdown(
                    "<div style='border-left:3px solid #888; height:420px; margin:38px auto 0;'></div>",
                    unsafe_allow_html=True
                )
            with col_prawa:
                st.subheader("📉 Najbardziej spadające")
                st.dataframe(styl_top(top_spadajace, "#f87171"), use_container_width=True, hide_index=True)

    # ── LISTA 2: CROSS 20/50 (ostatnie 3 sesje) ───────────────────────
    elif st.session_state["top_widok"] == "cross_20_50":
        st.subheader("Cross EMA20/50 — ostatnie 3 sesje")
        st.caption("Bazuje na liście all GPW+NC (yfinance)")

        wyniki_cross = []
        pasek_cross = st.progress(0, text="Skanowanie...")
        lista_cross = DOSTEPNE_YFINANCE
        for i, s in enumerate(lista_cross):
            pasek_cross.progress((i+1)/max(len(lista_cross),1), text=f"Sprawdzam: {s['ticker']}")
            df_t = wczytaj_notowania(s["ticker"])
            if len(df_t) < 51:
                continue
            df_t = licz_wskazniki(df_t)
            if len(df_t) < 4:
                continue

            ostatnie_3_sesje = df_t.index[-3:]
            sygnal_kierunek, sygnal_data = None, None
            for sesja_data in reversed(ostatnie_3_sesje):
                idx_sesji = df_t.index.get_loc(sesja_data)
                if idx_sesji < 1:
                    continue
                f_now, w_now   = df_t["EMA20"].iloc[idx_sesji],   df_t["EMA50"].iloc[idx_sesji]
                f_prev, w_prev = df_t["EMA20"].iloc[idx_sesji-1], df_t["EMA50"].iloc[idx_sesji-1]
                if pd.isna(f_now) or pd.isna(w_now) or pd.isna(f_prev) or pd.isna(w_prev):
                    continue
                if f_prev <= w_prev and f_now > w_now:
                    sygnal_kierunek, sygnal_data = "up", sesja_data.date()
                    break
                if f_prev >= w_prev and f_now < w_now:
                    sygnal_kierunek, sygnal_data = "down", sesja_data.date()
                    break

            if sygnal_kierunek is not None:
                sesje_temu = len(df_t) - 1 - df_t.index.get_loc(pd.Timestamp(sygnal_data))
                wyniki_cross.append({
                    "Ticker":  s["ticker"],
                    "Gielda":  {"GPW": "G", "NC": "N"}.get(s["rynek"], s["rynek"]),
                    "Kurs":    float(df_t["Close"].iloc[-1]),
                    "Cross":   "▲" if sygnal_kierunek == "up" else "▼",
                    "_sort":   sygnal_data,
                    "Data":    f"{sygnal_data.strftime('%d.%m')} ({sesje_temu} sesj{'a' if sesje_temu==1 else 'e' if 2<=sesje_temu<=4 else 'i'} temu)",
                })
        pasek_cross.empty()

        if not wyniki_cross:
            st.info("Brak spolek z przecieciem EMA20/50 w ostatnich 3 sesjach.")
        else:
            df_cross = pd.DataFrame(wyniki_cross).sort_values("_sort", ascending=False).drop(columns=["_sort"]).reset_index(drop=True)
            styled_cross = (
                df_cross.style
                .format({"Kurs": "{:.3f}"})
                .apply(lambda col: [
                    ("color: #4ade80; font-weight:700" if v == "▲" else "color: #f87171; font-weight:700")
                    if col.name == "Cross" else "" for v in col
                ], axis=0)
            )
            st.dataframe(styled_cross, use_container_width=True, hide_index=True)

    # ── LISTA 3: ADX < 22, DMI cross (2 sesje), Max ponad EMA50 0-30% ──
    elif st.session_state["top_widok"] == "adx_dmi_ema50":
        st.subheader("ADX < 22  +  DMI cross (Positive ↗ Negative, 2 sesje)  +  Max > EMA50 (0–30%)")
        st.caption("Bazuje na liście all GPW+NC (yfinance)")

        wyniki_adx = []
        pasek_adx = st.progress(0, text="Skanowanie...")
        lista_adx = DOSTEPNE_YFINANCE
        for i, s in enumerate(lista_adx):
            pasek_adx.progress((i+1)/max(len(lista_adx),1), text=f"Sprawdzam: {s['ticker']}")
            df_t = wczytaj_notowania(s["ticker"])
            if len(df_t) < 51:
                continue
            df_t = licz_wskazniki(df_t)
            if len(df_t) < 3:
                continue

            # Sprawdzamy ostatnie 2 sesje osobno — każda sesja to potencjalny sygnał
            for sesja_offset in [0, 1]:  # 0 = ostatnia sesja, 1 = przedostatnia
                idx_sesji = len(df_t) - 1 - sesja_offset
                if idx_sesji < 2:
                    continue

                df_do_sesji = df_t.iloc[:idx_sesji + 1]
                row_sesji = df_do_sesji.iloc[-1]
                data_sesji = df_do_sesji.index[-1].date()

                # Warunek 1: ADX(14) < 22 na tej sesji
                adx_val = row_sesji.get("ADX14")
                if pd.isna(adx_val) or float(adx_val) >= 22:
                    continue

                # Warunek 2: DMI cross +DI przecina -DI od dolu DOKŁADNIE na tej sesji
                p_now  = row_sesji.get("DMP14")
                n_now  = row_sesji.get("DMN14")
                p_prev = df_do_sesji["DMP14"].iloc[-2]
                n_prev = df_do_sesji["DMN14"].iloc[-2]
                if any(pd.isna(v) for v in [p_now, n_now, p_prev, n_prev]):
                    continue
                if not (float(p_prev) <= float(n_prev) and float(p_now) > float(n_now)):
                    continue

                # Warunek 5: Maksimum (High) powyzej EMA50 o 0% do 30% na tej sesji
                high_val  = row_sesji.get("High")
                ema50_val = row_sesji.get("EMA50")
                if pd.isna(high_val) or pd.isna(ema50_val) or float(ema50_val) == 0:
                    continue
                odchylenie = (float(high_val) - float(ema50_val)) / float(ema50_val) * 100
                if odchylenie < 0 or odchylenie > 30:
                    continue

                sesje_temu = sesja_offset
                etykieta = "dzisiaj" if sesje_temu == 0 else "wczoraj"
                wyniki_adx.append({
                    "Ticker":           s["ticker"],
                    "Gielda":           {"GPW": "G", "NC": "N"}.get(s["rynek"], s["rynek"]),
                    "Kurs":             float(df_t["Close"].iloc[-1]),
                    "ADX14":            float(adx_val),
                    "Max vs EMA50 (%)": odchylenie,
                    "DMI cross":        f"{data_sesji.strftime('%d.%m')} ({etykieta})",
                    "_sort":            data_sesji,
                })
        pasek_adx.empty()

        if not wyniki_adx:
            st.info("Brak spolek spelniajacych warunki ADX/DMI/EMA50.")
        else:
            df_adx = pd.DataFrame(wyniki_adx).sort_values("_sort", ascending=False).drop(columns=["_sort"]).reset_index(drop=True)
            styled_adx = (
                df_adx.style
                .format({"Kurs": "{:.3f}", "ADX14": "{:.1f}", "Max vs EMA50 (%)": "{:+.1f}%"})
                .apply(lambda col: ["color: #4ade80; font-weight:600" for _ in col]
                       if col.name == "Max vs EMA50 (%)" else ["" for _ in col], axis=0)
            )
            st.dataframe(styled_adx, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════════════════
# ZAKŁADKA 4 — SKANER
# ══════════════════════════════════════════════════════════════════════════════
else:
    st.header("Skaner sygnalow")

    st.sidebar.markdown("---")

    # ── DATA ──────────────────────────────────────────
    st.sidebar.markdown("### 📅 Data skanowania")
    typ_daty = st.sidebar.radio("", ["Dzień", "Zakres dat"], horizontal=True, label_visibility="collapsed")

    if typ_daty == "Dzień":
        data_skan = st.sidebar.date_input(
            "Sprawdz sygnaly na dzien:",
            value=date.today(),
            min_value=date.today() - timedelta(days=730),
            max_value=date.today(),
        )
        if isinstance(data_skan, (list, tuple)):
            data_skan = data_skan[0]
        zakres_od, zakres_do = data_skan, data_skan
    else:
        zakres_wybrany = st.sidebar.date_input(
            "Sprawdz sygnaly w zakresie:",
            value=(date.today() - timedelta(days=7), date.today()),
            min_value=date.today() - timedelta(days=730),
            max_value=date.today(),
        )
        if isinstance(zakres_wybrany, (list, tuple)) and len(zakres_wybrany) == 2:
            zakres_od, zakres_do = zakres_wybrany
        else:
            zakres_od = zakres_do = date.today()
        data_skan = zakres_do  # koniec zakresu jako "dzień referencyjny"

    if data_skan < date.today():
        st.sidebar.info(f"Tryb historyczny: do {data_skan.strftime('%d.%m.%Y')}")

    # ── RYNEK ─────────────────────────────────────────
    st.sidebar.markdown("### 🌍 Rynek")
    opcje_rynku = ["GPW", "NC", "GPW + NC",
                    "all GPW (yfinance)", "all NC (yfinance)", "all GPW+NC (yfinance)"]
    rynek_wybor = st.sidebar.radio("", opcje_rynku)

    # ── WARUNKI KURSU ─────────────────────────────────
    st.sidebar.markdown("### 💰 Warunki")

    DOSTEPNE_REF = ["EMA10", "EMA20", "EMA50", "EMA150", "EMA200"]

    def warunek_kurs_ui(nr):
        """Zwraca (uzyj, okres, relacja, referencja) dla jednego warunku kursu."""
        uzyj = st.sidebar.checkbox(f"Warunek {nr}", value=False, key=f"kurs_uzyj_{nr}")
        if not uzyj:
            return False, None, None, None
        col_a, col_b = st.sidebar.columns(2)
        with col_a:
            okres = st.selectbox("Kurs", ["D", "T", "M"], key=f"kurs_okres_{nr}")
        with col_b:
            relacja = st.selectbox("Relacja", ["powyżej", "poniżej", "równy"], key=f"kurs_relacja_{nr}")
        ref_raw = st.sidebar.text_input(
            "Czego? (np. EMA50, EMA150)",
            value="EMA50",
            key=f"kurs_ref_{nr}",
        ).strip().upper()
        return True, okres, relacja, ref_raw

    uzyj_k1, kurs_okres1, kurs_relacja1, kurs_ref1 = warunek_kurs_ui(1)
    uzyj_k2, kurs_okres2, kurs_relacja2, kurs_ref2 = warunek_kurs_ui(2)

    # ── WSKAŹNIKI ─────────────────────────────────────
    st.sidebar.markdown("### 📉 Wskaźniki")
    uzyj_rsi = st.sidebar.checkbox("Filtruj po RSI", value=False)
    if uzyj_rsi:
        tryb = st.sidebar.radio("Tryb:", ["Wyprzedanie (RSI niski)", "Wykupienie (RSI wysoki)"])
        prog_rsi = st.sidebar.slider(
            "RSI maksymalnie:" if tryb == "Wyprzedanie (RSI niski)" else "RSI minimalnie:",
            *(10, 50, 35) if tryb == "Wyprzedanie (RSI niski)" else (50, 90, 65)
        )
    else:
        tryb, prog_rsi = None, None

    uzyj_adr = st.sidebar.checkbox("Filtruj po ADR (20 sesji)", value=False)
    if uzyj_adr:
        zakres_adr = st.sidebar.slider("ADR (%) — zakres:", 0.0, 20.0, (2.0, 20.0), 0.5, format="%.1f%%")
        min_adr, max_adr = zakres_adr
    else:
        min_adr, max_adr = 0.0, 20.0

    # ── ŚREDNIE ───────────────────────────────────────
    st.sidebar.markdown("### 📈 Średnie")
    war_ema1 = st.sidebar.checkbox("EMA10 > EMA20",            value=False)
    war_ema2 = st.sidebar.checkbox("EMA50 > EMA150",           value=False)
    war_ema20_50 = st.sidebar.checkbox("EMA20 +/-0.5% od EMA50",  value=False)
    war_ema3 = st.sidebar.checkbox("EMA150 +/-0.5% od EMA200", value=False)
    war_cross20_50 = st.sidebar.checkbox("Cross EMA20/50", value=False)
    war_cross150_200 = st.sidebar.checkbox("Cross EMA150/200", value=False)

    # ── WOLUMEN ───────────────────────────────────────
    st.sidebar.markdown("### 📊 Wolumen")
    uzyj_vol_d = st.sidebar.checkbox("Dzienny", value=False)
    mnoznik_d  = st.sidebar.slider("Vol dzienny >= X x srednia 60 sesji:", 1.0, 10.0, 4.0, 0.5) if uzyj_vol_d else 4.0

    uzyj_vol_w = st.sidebar.checkbox("Tygodniowy", value=False)
    mnoznik_w  = st.sidebar.slider("Vol tygodniowy >= X x srednia 52 tyg.:", 1.0, 10.0, 3.0, 0.5) if uzyj_vol_w else 3.0

    uzyj_vol_m = st.sidebar.checkbox("Miesieczny", value=False)
    mnoznik_m  = st.sidebar.slider("Vol miesieczny >= X x srednia 24 mies.:", 1.0, 10.0, 2.0, 0.5) if uzyj_vol_m else 2.0

    # ── ŚWIECE ───────────────────────────────────────
    st.sidebar.markdown("### 🕯️ Swiecew")
    uzyj_swiece = st.sidebar.checkbox("Filtruj po formacji swiecowej", value=False)
    typ_swiecy = doji_tolerancja = bycza_min_body = bycza_max_cien = None
    if uzyj_swiece:
        typ_swiecy = st.sidebar.radio("Typ swiecy:", ["Doji", "Bycza swieca"])
        if typ_swiecy == "Doji":
            doji_tolerancja = st.sidebar.slider("Maks. body jako % zakresu swiecy:", 1, 20, 10)
        else:
            bycza_min_body = st.sidebar.slider("Min. body jako % zakresu Low->Close:", 1, 20, 3)
            bycza_max_cien = st.sidebar.slider("Maks. dolny cien jako % body:", 5, 100, 30)

    # ── ZMIANA KURSU ─────────────────────────────────
    st.sidebar.markdown("### 🔀 Zmiana kursu")

    uzyj_zmiana_d = st.sidebar.checkbox("Dzienna", value=False, key="zmd")
    if uzyj_zmiana_d:
        zakres_zmiana_d = st.sidebar.slider("Zmiana dzienna (%):", -20, 20, (-20,20), 1, format="%d%%")
        min_zm_d, max_zm_d = zakres_zmiana_d
        st.sidebar.caption(f"{'< -20%' if min_zm_d==-20 else f'{min_zm_d:+d}%'} do {'> +20%' if max_zm_d==20 else f'{max_zm_d:+d}%'}")
    else:
        min_zm_d, max_zm_d = -20, 20

    uzyj_zmiana_w = st.sidebar.checkbox("Tygodniowa", value=False, key="zmw")
    if uzyj_zmiana_w:
        zakres_zmiana_w = st.sidebar.slider("Zmiana tygodniowa (%):", -20, 20, (-20,20), 1, format="%d%%")
        min_zm_w, max_zm_w = zakres_zmiana_w
        st.sidebar.caption(f"{'< -20%' if min_zm_w==-20 else f'{min_zm_w:+d}%'} do {'> +20%' if max_zm_w==20 else f'{max_zm_w:+d}%'}")
    else:
        min_zm_w, max_zm_w = -20, 20

    uzyj_zmiana_m = st.sidebar.checkbox("Miesieczna", value=False, key="zmm")
    if uzyj_zmiana_m:
        zakres_zmiana_m = st.sidebar.slider("Zmiana miesieczna (%):", -20, 20, (-20,20), 1, format="%d%%")
        min_zm_m, max_zm_m = zakres_zmiana_m
        st.sidebar.caption(f"{'< -20%' if min_zm_m==-20 else f'{min_zm_m:+d}%'} do {'> +20%' if max_zm_m==20 else f'{max_zm_m:+d}%'}")
    else:
        min_zm_m, max_zm_m = -20, 20

    # ── FILTRUJ TICKERY PO RYNKU ──────────────────────
    if rynek_wybor == "GPW + NC":
        tickery = [(s["ticker"], s["rynek"]) for s in WSZYSTKIE_SPOLKI]
    elif rynek_wybor in ("GPW", "NC"):
        tickery = [(s["ticker"], s["rynek"]) for s in WSZYSTKIE_SPOLKI if s["rynek"] == rynek_wybor]
    elif rynek_wybor == "all GPW (yfinance)":
        tickery = [(s["ticker"], s["rynek"]) for s in DOSTEPNE_YFINANCE if s["rynek"] == "GPW"]
    elif rynek_wybor == "all NC (yfinance)":
        tickery = [(s["ticker"], s["rynek"]) for s in DOSTEPNE_YFINANCE if s["rynek"] == "NC"]
    else:  # all GPW+NC (yfinance)
        tickery = [(s["ticker"], s["rynek"]) for s in DOSTEPNE_YFINANCE]

    if rynek_wybor.endswith("(yfinance)") and not tickery:
        st.sidebar.warning("Brak pliku available_tickers.csv w katalogu aplikacji — lista jest pusta.")

    st.info(f"Spolek do przeskanowania: **{len(tickery)}**")

    if st.button("🚀 Uruchom skaner"):
        wyniki = []
        pasek  = st.progress(0, text="Skanuje...")
        bledy  = 0
        czas_start = time.time()

        for i, (t, rynek_t) in enumerate(tickery):
            pasek.progress((i+1)/len(tickery), text=f"Skanuje: {t} ({i+1}/{len(tickery)})")
            try:
                df = pobierz_dane(t, period="2y", interval="1d", data_koniec=data_skan)
                if df.empty or len(df) < 200:
                    bledy += 1
                    continue
                df  = licz_wskazniki(df)
                df  = licz_adr(df, 20)
                row = df.iloc[-1]

                row_w = None
                if uzyj_vol_w:
                    df_w = pobierz_dane(t, period="5y", interval="1wk", data_koniec=data_skan)
                    if not df_w.empty and len(df_w) >= 52:
                        df_w  = licz_wskazniki_tygodniowe(df_w)
                        row_w = df_w.iloc[-1]

                # KURS
                if not sprawdz_warunek_kurs(uzyj_k1, kurs_okres1, kurs_relacja1, kurs_ref1 or "", row, None, df): continue
                if not sprawdz_warunek_kurs(uzyj_k2, kurs_okres2, kurs_relacja2, kurs_ref2 or "", row, None, df): continue

                # RSI
                rsi = row.get("RSI")
                if uzyj_rsi:
                    if pd.isna(rsi): continue
                    if tryb == "Wyprzedanie (RSI niski)":
                        if float(rsi) > prog_rsi: continue
                    else:
                        if float(rsi) < prog_rsi: continue

                # ADR
                if uzyj_adr:
                    adr = row.get("ADR20")
                    if pd.isna(adr): continue
                    adr_val = float(adr)
                    if adr_val < min_adr or adr_val > max_adr: continue

                # EMA
                if not sprawdz_ema_warunki(row, war_ema1, war_ema2, war_ema20_50, war_ema3): continue

                # crossover EMA20/EMA50 i EMA150/EMA200
                cross_20_50, data_cross_20_50 = wykryj_crossover_ema(
                    df, "EMA20", "EMA50", zakres_od, zakres_do)
                cross_150_200, data_cross_150_200 = wykryj_crossover_ema(
                    df, "EMA150", "EMA200", zakres_od, zakres_do)

                if war_cross20_50 and cross_20_50 is None: continue
                if war_cross150_200 and cross_150_200 is None: continue

                # wolumen dzienny
                if not sprawdz_wolumen_dzienny(row, uzyj_vol_d, mnoznik_d): continue

                # wolumen tygodniowy
                if uzyj_vol_w:
                    if row_w is None: continue
                    if not sprawdz_wolumen_tygodniowy(row_w, True, mnoznik_w): continue

                # wolumen miesięczny (24 mies.)
                if uzyj_vol_m:
                    vol_d, avg_24m = row.get("Volume"), row.get("VOL_AVG24M")
                    if avg_24m is None or pd.isna(vol_d) or pd.isna(avg_24m) or float(avg_24m)==0: continue
                    if float(vol_d) < mnoznik_m * float(avg_24m): continue

                # świece
                if uzyj_swiece:
                    if typ_swiecy == "Doji":
                        if not wykryj_doji(row, doji_tolerancja/100): continue
                    else:
                        if not wykryj_bycza_swiece(row, bycza_min_body, bycza_max_cien): continue

                # zmiany kursu
                kurs_teraz = float(row["Close"])
                data_sesji = row.name.date() if hasattr(row.name, "date") else df.index[-1].date()
                zm_d_val = zm_w_val = zm_m_val = float('nan')

                if len(df) >= 2:
                    k = float(df["Close"].iloc[-2])
                    if k != 0:
                        zm_d = (kurs_teraz - k) / k * 100
                        zm_d_val = zm_d
                        if uzyj_zmiana_d:
                            if not ((True if min_zm_d==-20 else zm_d>=min_zm_d) and
                                    (True if max_zm_d== 20 else zm_d<=max_zm_d)): continue
                elif uzyj_zmiana_d: continue

                # Zmiana 1W: od ostatniej sesji PRZED poniedziałkiem bieżącego tygodnia
                k = kurs_na_poczatek_okresu(df, data_sesji, "tydzien")
                if k is not None and k != 0:
                    zm_w = (kurs_teraz - k) / k * 100
                    zm_w_val = zm_w
                    if uzyj_zmiana_w:
                        if not ((True if min_zm_w==-20 else zm_w>=min_zm_w) and
                                (True if max_zm_w== 20 else zm_w<=max_zm_w)): continue
                elif uzyj_zmiana_w: continue

                # Zmiana 1M: od ostatniej sesji PRZED 1-szym dniem bieżącego miesiąca
                k = kurs_na_poczatek_okresu(df, data_sesji, "miesiac")
                if k is not None and k != 0:
                    zm_m = (kurs_teraz - k) / k * 100
                    zm_m_val = zm_m
                    if uzyj_zmiana_m:
                        if not ((True if min_zm_m==-20 else zm_m>=min_zm_m) and
                                (True if max_zm_m== 20 else zm_m<=max_zm_m)): continue
                elif uzyj_zmiana_m: continue

                # wolumen ratios
                vol_d = row.get("Volume")
                avg_d = row.get("VOL_AVG60")
                e150  = row.get("EMA150")
                e200  = row.get("EMA200")

                odch_val = float('nan')
                vd_val   = float('nan')
                if not pd.isna(e150) and not pd.isna(e200) and e200 != 0:
                    odch_val = (float(e150) - float(e200)) / float(e200) * 100
                if not pd.isna(vol_d) and not pd.isna(avg_d) and avg_d != 0:
                    vd_val = float(vol_d)/float(avg_d)

                adr20 = row.get("ADR20")
                kurs_val = float(row["Close"])
                kurs_fmt = round(kurs_val, 3)
                cross_20_50_txt   = {"up": "▲", "down": "▼"}.get(cross_20_50, "—")
                cross_150_200_txt = {"up": "▲", "down": "▼"}.get(cross_150_200, "—")
                data_cross_20_50_txt   = data_cross_20_50.strftime("%d.%m")   if data_cross_20_50   else "—"
                data_cross_150_200_txt = data_cross_150_200.strftime("%d.%m") if data_cross_150_200 else "—"

                wynik_wiersz = {
                    "Ticker":         t,
                    "Gielda":         {"GPW": "G", "NC": "N"}.get(rynek_t, rynek_t),
                    "Kategoria":      TICKER_INFO.get(t, {}).get("kategoria", "—"),
                    "Kurs":           kurs_fmt,
                    "ADR20 (%)":      float(adr20) if not pd.isna(adr20) else float('nan'),
                    "Zmiana 1D":      zm_d_val,
                    "Zmiana 1W":      zm_w_val,
                    "Zmiana 1M":      zm_m_val,
                    "RSI":            float(rsi) if not pd.isna(rsi) else float('nan'),
                    "EMA150vsEMA200": odch_val,
                    "Vol/Sr.60D":     vd_val,
                    "Cross 20/50":    cross_20_50_txt,
                }
                if typ_daty == "Zakres dat":
                    wynik_wiersz["Data 20/50"] = data_cross_20_50_txt
                if war_cross150_200:
                    wynik_wiersz["Cross 150/200"] = cross_150_200_txt
                    if typ_daty == "Zakres dat":
                        wynik_wiersz["Data 150/200"] = data_cross_150_200_txt

                wyniki.append(wynik_wiersz)

            except Exception:
                bledy += 1
                continue

        pasek.empty()
        czas_s = int(time.time() - czas_start)
        tryb_info = f"📅 Sygnaly na dzien: **{data_skan.strftime('%d.%m.%Y')}**" + (
            " *(tryb historyczny)*" if data_skan < date.today() else " *(dzisiaj)*"
        )
        st.markdown(tryb_info)
        st.success(f"Skanowanie {czas_s}s zakonczone — znaleziono **{len(wyniki)}** spolek "
                   f"({bledy} bez danych / pominiętych)")

        if wyniki:
            df_wyniki = pd.DataFrame(wyniki)

            def koloruj(val, kolumna):
                if kolumna in ("Zmiana 1D", "Zmiana 1W", "Zmiana 1M"):
                    try:
                        v = float(val)
                        if v >= 2:   return "color: #4ade80; font-weight:600"  # zielony
                        if v <= -2:  return "color: #f87171; font-weight:600"  # czerwony
                    except (TypeError, ValueError): pass
                if kolumna == "EMA150vsEMA200":
                    try:
                        v = float(val)
                        if v >= 0:  return "color: #4ade80; font-weight:600"
                        return "color: #f87171; font-weight:600"
                    except (TypeError, ValueError): pass
                if kolumna == "Cross 20/50":
                    if val == "▲": return "color: #4ade80; font-weight:700; font-size:1.1em"
                    if val == "▼": return "color: #f87171; font-weight:700; font-size:1.1em"
                if kolumna == "Cross 150/200":
                    if val == "▲": return "color: #60a5fa; font-weight:700; font-size:1.1em"
                    if val == "▼": return "color: #60a5fa; font-weight:700; font-size:1.1em"
                return ""

            FORMAT_KOLUMN = {
                "Kurs":           "{:.3f}",
                "ADR20 (%)":      "{:.1f}%",
                "Zmiana 1D":      "{:+.1f}%",
                "Zmiana 1W":      "{:+.1f}%",
                "Zmiana 1M":      "{:+.1f}%",
                "RSI":            "{:.0f}",
                "EMA150vsEMA200": "{:+.2f}%",
                "Vol/Sr.60D":     "{:.1f}x",
            }

            styled = (
                df_wyniki.style
                .apply(lambda col: [koloruj(v, col.name) for v in col], axis=0)
                .format(FORMAT_KOLUMN, na_rep="—")
            )
            st.dataframe(styled, use_container_width=True, hide_index=True)
            csv = df_wyniki.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Pobierz wyniki jako CSV",
                               csv, "wyniki_skanera.csv", "text/csv")
        else:
            st.info("Brak spolek spelniajacych podane warunki.")
