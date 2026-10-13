#!/usr/bin/env python3
"""
project_revenue.py  —  Cohort revenue projection engine for play_data.monthly_rev_diff.

Reads 5 reference/state CSVs produced by the SQL pulls in the skill (all live-computed),
plus an OPTIONAL spend_plan.csv, and writes projection_by_month.csv + projection_yearly.csv.

Method (faithful reimplementation of the "Ratios/Playground" sheet):
  rev is INCREMENTAL revenue per diff-month; it lands in calendar month = install_month + diff.
  spend is the cohort's acquisition spend (constant across diff rows -> take once per cohort).
  - Actual months pass through unchanged (ground truth).
  - Immature cohorts: complete diff (k+1..12) via a blended trend/seasonal step-ratio
    (trend weight slides 1.00 -> 0.45 across diffs 1..12), then extend the long tail (13..cap).
  - Mature cohorts: extend the long tail only.
  - Future cohorts (from a spend plan or growth assumption): M12 = spend x assumed M12 ROAS,
    spread by the seasonal 0..12 profile, then the tail.
  - cap = 120 months for cohorts installed >= 2024-01, else 90 (sheet's hardcoded caps).

Usage:
  python3 project_revenue.py --dir ./ [--horizon-end 2030-12] [--growth 1.08]
                             [--future-roas auto|1.15] [--spend-plan spend_plan.csv]
                             [--asof YYYY-MM]   # optional: treat this as the data edge (backcast)
"""
import argparse, csv, os
from statistics import median

def parse_ym(s):
    y,m=s.split("-")[:2]; return int(y),int(m)
def ym_idx(y,m): return y*12+(m-1)
def idx_ym(i): return (i//12, i%12+1)
def key(i): y,m=idx_ym(i); return f"{y:04d}-{m:02d}"

def load(d,name):
    rows=[]
    with open(os.path.join(d,name),newline="") as f:
        for r in csv.DictReader(f): rows.append(r)
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--dir",default=".")
    ap.add_argument("--horizon-end",default="2030-12")
    ap.add_argument("--growth",type=float,default=1.08,help="YoY spend growth for future months w/o a plan")
    ap.add_argument("--future-roas",default="auto",help="'auto' (median recent M12 ROAS) or a number")
    ap.add_argument("--spend-plan",default=None,help="CSV install_month,spend for future months")
    a=ap.parse_args(); D=a.dir

    # --- reference profiles (all live-computed) ---
    SEASONAL={}
    for r in load(D,"seasonal.csv"):
        SEASONAL.setdefault(int(r["cal_month"]),{})[int(r["diff"])]=float(r["share"])
    SEAS={m:[SEASONAL[m][d] for d in range(13)] for m in SEASONAL}
    TAIL={int(r["diff"]):float(r["tail_share"]) for r in load(D,"tail.csv")}
    tmax=max(TAIL); tlast=TAIL[tmax]
    def tail_share(x): return 0.0 if x<13 else TAIL.get(x,tlast)
    TREND={int(r["diff"]):float(r["median_ratio"]) for r in load(D,"trend.csv")}

    COH=[(r["install_month"][:7],float(r["spend"]),int(r["max_obs_diff"]),float(r["m12_rev_obs"]))
         for r in load(D,"cohorts.csv")]
    ACTUAL={r["return_month"][:7]:float(r["rev"]) for r in load(D,"actuals.csv")}

    # data edge = latest month with actual revenue (backcast simply by building the CSVs as-of)
    LAST=max(max(ACTUAL), max(c[0] for c in COH))
    LY,LM=parse_ym(LAST); LAST_IDX=ym_idx(LY,LM)
    HY,HM=parse_ym(a.horizon_end); HORIZON=ym_idx(HY,HM)

    # future M12 ROAS assumption
    recent=[(s,mo) for (ins,s,k,mo) in COH if k>=10 and s>0][-12:]
    FUT_ROAS=median([mo/s for s,mo in recent]) if a.future_roas=="auto" else float(a.future_roas)

    def cohort_future(install,spend,k,m12obs,future_roas=None):
        y,m=parse_ym(install); cal=m; ii=ym_idx(y,m)
        cap=120 if ii>=ym_idx(2024,1) else 90
        seas=SEAS[cal]; out=[]
        if future_roas is not None:                     # brand-new cohort
            m12=spend*future_roas
            for d in range(13):
                ri=ii+d
                if LAST_IDX<ri<=HORIZON: out.append((ri,m12*seas[d]))
            for d in range(13,cap+1):
                ri=ii+d
                if LAST_IDX<ri<=HORIZON: out.append((ri,m12*tail_share(d)))
            return out
        if k<12:                                        # immature: complete 12 then tail
            seas_cum=sum(seas[0:k+1]); m12_est=m12obs/seas_cum
            inc_prev=m12_est*seas[k]; proj12=0.0
            for d in range(k+1,13):
                sr=seas[d]/seas[d-1]; tr=TREND[d]; w=1-0.55*(d-1)/11
                inc=inc_prev*(w*tr+(1-w)*sr); inc_prev=inc; proj12+=inc
                ri=ii+d
                if LAST_IDX<ri<=HORIZON: out.append((ri,inc))
            m12=m12obs+proj12
        else:
            m12=m12obs
        for d in range(max(k+1,13),cap+1):
            ri=ii+d
            if LAST_IDX<ri<=HORIZON: out.append((ri,m12*tail_share(d)))
        return out

    proj=dict(ACTUAL)
    for ins,s,k,mo in COH:
        for ri,inc in cohort_future(ins,s,k,mo):
            proj[key(ri)]=proj.get(key(ri),0.0)+inc

    # future cohorts
    plan={}
    if a.spend_plan:
        pth=a.spend_plan if os.path.isabs(a.spend_plan) else os.path.join(D,a.spend_plan)
        with open(pth,newline="") as f:
            for r in csv.DictReader(f): plan[r["install_month"][:7]]=float(r["spend"])
    SPEND={ins:s for ins,s,k,mo in COH}
    fut_spend={}
    i=LAST_IDX+1
    while i<=HORIZON:
        ky=key(i)
        if ky in plan:
            s=plan[ky]
        else:
            py,pm=idx_ym(i); prev=f"{py-1:04d}-{pm:02d}"
            base=SPEND.get(prev) or fut_spend.get(prev)
            s=base*a.growth if base else 0.0
        fut_spend[ky]=s
        for ri,inc in cohort_future(ky,s,-1,0.0,future_roas=FUT_ROAS):
            proj[key(ri)]=proj.get(key(ri),0.0)+inc
        i+=1

    # rollups
    def yr(d):
        o={}
        for k,v in d.items(): o[int(k[:4])]=o.get(int(k[:4]),0.0)+v
        return o
    ysp={}
    for ins,s,k,mo in COH: ysp[int(ins[:4])]=ysp.get(int(ins[:4]),0.0)+s
    for k,s in fut_spend.items(): ysp[int(k[:4])]=ysp.get(int(k[:4]),0.0)+s
    pr=yr(proj); ar=yr(ACTUAL)

    with open(os.path.join(D,"projection_by_month.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["return_month","projected_rev","actual_rev","is_actual"])
        for k in sorted(proj):
            w.writerow([k,round(proj[k],2),round(ACTUAL.get(k,0),2),int(k in ACTUAL and k<=LAST)])
    with open(os.path.join(D,"projection_yearly.csv"),"w",newline="") as f:
        w=csv.writer(f); w.writerow(["year","projected_rev","spend","roas","actual_rev"])
        for y in sorted(pr):
            s=ysp.get(y,0)
            w.writerow([y,round(pr[y],2),round(s,2),round(pr[y]/s,4) if s else "",round(ar.get(y,0),2)])

    print(f"Data edge: {LAST} | horizon: {a.horizon_end} | future M12 ROAS: {FUT_ROAS:.3f} | spend growth: {a.growth}")
    print(f"{'YEAR':6}{'ProjRev$M':>12}{'Spend$M':>10}{'ROAS':>7}")
    for y in sorted(pr):
        s=ysp.get(y,0)
        print(f"{y:<6}{pr[y]/1e6:>12.1f}{s/1e6:>10.1f}{(pr[y]/s if s else 0):>7.2f}")
    print("-> projection_by_month.csv, projection_yearly.csv")

if __name__=="__main__":
    main()
