"""Calculate daily swing accumulation/distribution features from imported NSE bhavcopy."""
from __future__ import annotations
import os
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd

def get_conn():
    dsn = os.getenv("DATABASE_URL")
    if dsn:
        return psycopg2.connect(dsn)
    return psycopg2.connect(host=os.getenv("DB_HOST","localhost"),
        port=os.getenv("DB_PORT","5432"), dbname=os.getenv("DB_NAME","mtf_db"),
        user=os.getenv("DB_USER","bseetharaman"), password=os.getenv("DB_PASSWORD",""))

def calc_symbol(g):
    g = g.sort_values("trade_date").copy()
    close, high, low, vol = (g[c].astype(float) for c in
        ("close_price","high_price","low_price","traded_quantity"))
    prev = close.shift(1)
    g["rvol_20"] = vol / vol.shift(1).rolling(20, min_periods=10).mean()
    value = g["turnover_cr"].astype(float)
    g["turnover_rvol_20"] = value / value.shift(1).rolling(20, min_periods=10).mean()
    g["clv"] = ((close-low)-(high-close)) / (high-low).replace(0, float("nan"))
    g["clv"] = g["clv"].fillna(0).clip(-1,1)
    direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
    g["obv"] = (direction * vol).cumsum()
    g["obv_change_20"] = g["obv"].pct_change(20).replace([float("inf"),-float("inf")],0).fillna(0)
    mf_multiplier = g["clv"]
    mf_volume = mf_multiplier * vol
    g["cmf_20"] = mf_volume.rolling(20,min_periods=10).sum() / vol.rolling(20,min_periods=10).sum().replace(0,float("nan"))
    tr = pd.concat([(high-low), (high-prev).abs(), (low-prev).abs()],axis=1).max(axis=1)
    atr = tr.rolling(14,min_periods=10).mean()
    g["atr_pct_14"] = atr / close.replace(0,float("nan")) * 100
    g["return_5d"] = close.pct_change(5)
    g["return_20d"] = close.pct_change(20)
    g["delivery_pct_avg_20"] = g["delivery_pct"].astype(float).rolling(20,min_periods=10).mean()
    g["delivery_pct_delta_20"] = g["delivery_pct"].astype(float) - g["delivery_pct_avg_20"]
    return g

def score_row(r, cross_section_median):
    reasons=[]
    def clamp(x): return max(0.0,min(1.0,float(x)))
    rvol=float(r.get("rvol_20") or 0)
    delivery_delta=float(r.get("delivery_pct_delta_20") or 0)
    clv=float(r.get("clv") or 0)
    cmf=float(r.get("cmf_20") or 0)
    obv=float(r.get("obv_change_20") or 0)
    rs=float(r.get("relative_strength_20d") or 0)
    # Directional components. These are screening heuristics, not participant identification.
    components=[
      (20*clamp((rvol-0.8)/1.7), "relative volume elevated" if rvol>=1.5 else None),
      (15*clamp((delivery_delta+2)/18), "delivery participation above its 20-session mean" if delivery_delta>=5 else None),
      (15*clamp((clv+1)/2), "close in upper part of daily range" if clv>=0.5 else None),
      (15*clamp((cmf+0.15)/0.65), "positive 20-session money flow" if cmf>0.05 else None),
      (15*clamp((obv+0.1)/0.6), "OBV trend improving" if obv>0.1 else None),
      (15*clamp((rs+0.03)/0.12), "outperforming universe median" if rs>0.02 else None),
      (5*clamp((float(r.get("return_20d") or 0)+0.05)/0.15), "positive 20-session return" if (r.get("return_20d") or 0)>0 else None)
    ]
    acc=round(sum(x[0] for x in components),2)
    for _,reason in components:
        if reason: reasons.append(reason)
    # Symmetric bearish score uses inverse directional evidence.
    bearish=[
      20*clamp((rvol-0.8)/1.7),
      15*clamp((-delivery_delta+2)/18),
      15*clamp((1-clv)/2),
      15*clamp((-cmf+0.15)/0.65),
      15*clamp((-obv+0.1)/0.6),
      15*clamp((-rs+0.03)/0.12),
      5*clamp((-float(r.get("return_20d") or 0)+0.05)/0.15)
    ]
    dist=round(sum(bearish),2)
    quality=100
    if r.get("rvol_20") is None: quality-=25
    if r.get("delivery_pct") is None: quality-=15
    if r.get("return_20d") is None: quality-=20
    if int(r.get("traded_quantity") or 0)<1000: quality-=20
    if r.get("close_price") is None: quality=0
    signal="ACCUMULATION_WATCH" if acc>=65 and acc>dist else (
      "DISTRIBUTION_WATCH" if dist>=65 and dist>acc else "NEUTRAL")
    return acc,dist,max(0,quality),signal,reasons

def run(trade_date=None):
    conn=get_conn()
    try:
      with conn.cursor() as cur:
        params=[]
        where=""
        if trade_date:
          where="WHERE trade_date <= %s"
          params=[trade_date]
        cur.execute(f"""SELECT trade_date,symbol,series,high_price,low_price,close_price,
          traded_quantity,turnover_cr,delivery_pct FROM swing_daily_bhavcopy
          {where} AND series IN ('EQ','BE') ORDER BY symbol,trade_date""" if where else
          """SELECT trade_date,symbol,series,high_price,low_price,close_price,
          traded_quantity,turnover_cr,delivery_pct FROM swing_daily_bhavcopy
          WHERE series IN ('EQ','BE') ORDER BY symbol,trade_date""",params)
        rows=cur.fetchall()
      if not rows: return 0
      df=pd.DataFrame(rows,columns=["trade_date","symbol","series","high_price","low_price","close_price","traded_quantity","turnover_cr","delivery_pct"])
      parts=[calc_symbol(g) for _,g in df.groupby("symbol",sort=False)]
      feat=pd.concat(parts,ignore_index=True)
      # Cross-sectional median return is a fallback benchmark when index candles are not yet loaded.
      feat["relative_strength_20d"]=feat["return_20d"]-feat.groupby("trade_date")["return_20d"].transform("median")
      latest=feat.sort_values("trade_date").groupby("symbol").tail(1)
      out=[]
      for _,r in latest.iterrows():
        acc,dist,quality,signal,reasons=score_row(r,0)
        out.append((r.trade_date,r.symbol,r.close_price,int(r.traded_quantity or 0),r.turnover_cr,
          r.delivery_pct,r.rvol_20,r.turnover_rvol_20,r.delivery_pct_avg_20,r.delivery_pct_delta_20,
          r.clv,r.obv,r.obv_change_20,r.cmf_20,r.atr_pct_14,r.return_5d,r.return_20d,
          r.relative_strength_20d,acc,dist,quality,signal,psycopg2.extras.Json(reasons),"swing-v1"))
      sql="""INSERT INTO swing_daily_features
      (trade_date,symbol,close_price,traded_quantity,turnover_cr,delivery_pct,rvol_20,
       turnover_rvol_20,delivery_pct_avg_20,delivery_pct_delta_20,clv,obv,obv_change_20,
       cmf_20,atr_pct_14,return_5d,return_20d,relative_strength_20d,accumulation_score,
       distribution_score,data_quality_score,signal,reasons,strategy_version)
      VALUES %s ON CONFLICT (trade_date,symbol) DO UPDATE SET
       close_price=EXCLUDED.close_price,traded_quantity=EXCLUDED.traded_quantity,
       turnover_cr=EXCLUDED.turnover_cr,delivery_pct=EXCLUDED.delivery_pct,rvol_20=EXCLUDED.rvol_20,
       turnover_rvol_20=EXCLUDED.turnover_rvol_20,delivery_pct_avg_20=EXCLUDED.delivery_pct_avg_20,
       delivery_pct_delta_20=EXCLUDED.delivery_pct_delta_20,clv=EXCLUDED.clv,obv=EXCLUDED.obv,
       obv_change_20=EXCLUDED.obv_change_20,cmf_20=EXCLUDED.cmf_20,atr_pct_14=EXCLUDED.atr_pct_14,
       return_5d=EXCLUDED.return_5d,return_20d=EXCLUDED.return_20d,
       relative_strength_20d=EXCLUDED.relative_strength_20d,accumulation_score=EXCLUDED.accumulation_score,
       distribution_score=EXCLUDED.distribution_score,data_quality_score=EXCLUDED.data_quality_score,
       signal=EXCLUDED.signal,reasons=EXCLUDED.reasons,strategy_version=EXCLUDED.strategy_version,
       calculated_at=now()"""
      with conn,conn.cursor() as cur: execute_values(cur,sql,out,page_size=1000)
      return len(out)
    finally: conn.close()

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--date");a=p.parse_args()
    print(f"Calculated {run(a.date)} swing feature rows")
