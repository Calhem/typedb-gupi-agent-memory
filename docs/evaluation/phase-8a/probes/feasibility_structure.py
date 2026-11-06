"""Dev only, aggregates only. Fixed variants, chosen before running."""
import json, math, re, statistics
from collections import defaultdict
from gupi.benchmarks import locomo, longmemeval
from gupi.search import tokens, K1, B
def bm25(words,bags,n):
    cand={i:b for i,b in bags.items() if any(w in " ".join(b) for w in words)}
    df={w:sum(1 for b in cand.values() if w in b) for w in words}
    avg=sum(map(len,cand.values()))/len(cand) if cand else 1
    s=[]
    for i,b in cand.items():
        v=sum(math.log(1+(n-df[w]+.5)/(df[w]+.5))*f*(K1+1)/(f+K1*(1-B+B*len(b)/avg)) for w in words if (f:=b.count(w)))
        if v>0:s.append((-v,i))
    return [i for _,i in sorted(s)]
def neighbours(i,order,pos,sess):
    out=[]
    for d in (1,-1):
        p=pos[i]+d
        if 0<=p<len(order) and sess[order[p]]==sess[i]: out.append(order[p])
    return out
def windowed(kw,order,pos,sess,keep,k=50):
    """keep the top `keep` keyword hits in place, then each hit followed by its next/previous turn."""
    out=list(kw[:keep])
    for x in kw:
        for y in ([x] if x not in out else [])+neighbours(x,order,pos,sess):
            if y not in out: out.append(y)
    return out[:k]
R=[]
def rec(ds,q,cat,sysn,r,gold,unit="turn"):
    if gold: R.append(dict(ds=ds,q=q,cat=cat,sys=sysn,unit=unit,r5=len(set(r[:5])&gold)/len(gold),r10=len(set(r[:10])&gold)/len(gold)))
# LoCoMo
gs=defaultdict(list)
for s in locomo.load("dev"):
    sid=s["sample_id"];conv=s["conversation"];speakers=(conv["speaker_a"],conv["speaker_b"]);turns={};order=[];sess={};auth={}
    for i,when,ts in locomo.sessions(s):
        for t in ts:
            k=t["dia_id"];turns[k]=locomo.turn_text(t);order.append(k);sess[k]=i;auth[k]=t["speaker"]
    bags={k:tokens(v) for k,v in turns.items()};n=len(turns);pos={k:p for p,k in enumerate(order)}
    for qn,qa in enumerate(s["qa"]):
        gold={e.strip() for e in (qa.get("evidence") or []) if e.strip() in turns}
        if not gold: continue
        cat=locomo.CATEGORIES[qa["category"]];kw=bm25(sorted(set(tokens(qa["question"]))),bags,n)[:50]
        named=[x for x in speakers if re.search(rf"\b{x}\b",qa["question"])]
        rec("locomo",f"{sid}:{qn}",cat,"keyword",kw,gold)
        rec("locomo",f"{sid}:{qn}",cat,"window-keep3",windowed(kw,order,pos,sess,3),gold)
        rec("locomo",f"{sid}:{qn}",cat,"window-keep5",windowed(kw,order,pos,sess,5),gold)
        if len(named)==1:
            a=[i for i in kw if auth[i]==named[0]]+[i for i in kw if auth[i]!=named[0]]
            rec("locomo",f"{sid}:{qn}",cat,"author-first",a,gold)
        else: a=kw; rec("locomo",f"{sid}:{qn}",cat,"author-first",kw,gold)
        il=[]
        for x,y in zip(windowed(kw,order,pos,sess,3),a+kw[len(a):]):
            for z in (y,x):
                if z not in il: il.append(z)
        rec("locomo",f"{sid}:{qn}",cat,"interleave",il,gold)
        gs[cat].append(dict(sessions=len({sess[g] for g in gold}),in_seed_session=len([g for g in gold if sess[g] in {sess[x] for x in kw[:5]}])/len(gold),
             by_named=(sum(auth[g]==named[0] for g in gold)/len(gold) if len(named)==1 else None),gap=min((abs(pos[g]-pos[x]) for g in gold for x in kw[:5]),default=None)))
print("LoCoMo gold structure")
for c,v in gs.items():
    b=[x['by_named'] for x in v if x['by_named'] is not None]
    print(f" {c:12} n={len(v)} sessions-per-q {statistics.mean(x['sessions'] for x in v):.2f} gold-in-a-seed-session {statistics.mean(x['in_seed_session'] for x in v):.3f} gold-authored-by-named-speaker {statistics.mean(b) if b else 0:.3f} (q with one named {len(b)}/{len(v)})")
# LongMemEval dev
items=longmemeval.load("dev")
print("lme dev questions",len(items))
for q in items:
    gold=set();order=[];sess={};bags={};goldsess=set()
    for sid,date,ts in zip(q["haystack_session_ids"],q["haystack_dates"],q["haystack_sessions"]):
        cid=longmemeval.context_id(sid,date,ts)
        for i,t in enumerate(ts):
            k=f"{cid}:{i}";order.append(k);sess[k]=cid;bags[k]=tokens(t["content"])
            if t.get("has_answer"): gold.add(k)
        if sid in q["answer_session_ids"]: goldsess.add(cid)
    pos={k:p for p,k in enumerate(order)}
    kw=bm25(sorted(set(tokens(q["question"]))),bags,len(order))[:50]
    cat=q["question_type"]+("/abs" if q["question_id"].endswith("_abs") else "")
    for name,r in (("keyword",kw),("window-keep5",windowed(kw,order,pos,sess,5))):
        rec("lme",q["question_id"],cat,name,r,gold)
        rs=list(dict.fromkeys(sess[i] for i in r)); rec("lme",q["question_id"],cat,name,rs,goldsess,"session")
def table(ds,unit):
    sel=[r for r in R if r["ds"]==ds and r["unit"]==unit]; cats=sorted({r["cat"] for r in sel}); syss=sorted({r["sys"] for r in sel})
    for c in cats+["ALL"]:
        line=f"{ds} {unit} {c:28}"
        for s in syss:
            x=[r for r in sel if r["sys"]==s and (c=="ALL" or r["cat"]==c)]
            line+=f"| {s[:12]:12} n={len(x):3} R5 {statistics.mean(r['r5'] for r in x):.3f} R10 {statistics.mean(r['r10'] for r in x):.3f} "
        print(line)
table("locomo","turn");table("lme","turn");table("lme","session")
