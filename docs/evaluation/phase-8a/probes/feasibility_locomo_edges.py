"""Dev-only feasibility. Aggregates only; no dataset text is printed."""
import json, math, re, statistics, sys
from collections import Counter, defaultdict
from gupi.benchmarks import locomo
from gupi.search import tokens, K1, B
CAP=re.compile(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})*\b")
samples=locomo.load("dev")
def bm25(words,bags,n_docs):
    cand={i:b for i,b in bags.items() if any(w in " ".join(b) for w in words)}
    df={w:sum(1 for b in cand.values() if w in b) for w in words}
    avg=sum(map(len,cand.values()))/len(cand) if cand else 1
    s=[]
    for i,b in cand.items():
        v=sum(math.log(1+(n_docs-df[w]+.5)/(df[w]+.5))*f*(K1+1)/(f+K1*(1-B+B*len(b)/avg)) for w in words if (f:=b.count(w)))
        if v>0: s.append((-v,i))
    return s
COMMON=set("""The This That These Those What When Where Why How Who Yes Yeah Wow Thanks Thank Hey Hi Hello Sure Sorry Great Nice Good Cool Awesome
Oh Well Also And But Not Its It's You I'm My We They She His Her Their Our Your Have Has Had Did Does Can Could Would Should Will Just Really Totally So Keep Let Glad Love Haha Absolutely Definitely
Monday Tuesday Wednesday Thursday Friday Saturday Sunday January February March April May June July August September October November December""".split())
def ents(text):
    out=set()
    for m in CAP.finditer(text):
        w=m.group()
        if w in COMMON: continue
        # sentence-initial single words are not names unless seen mid-sentence elsewhere (decided below)
        start=m.start(); pre=text[:start].rstrip()
        out.add((w, start==0 or pre[-1:] in ".!?"))
    return out
rows=[];reach=defaultdict(list)
def rrf(lists,k=60):
    s=defaultdict(float)
    for l in lists:
        for r,i in enumerate(l,1): s[i]+=1/(k+r)
    return [i for i,_ in sorted(s.items(),key=lambda x:(-x[1],x[0]))]
ents_seen=Counter()
for s in samples:
    sid=s["sample_id"]; conv=s["conversation"]; speakers={conv["speaker_a"],conv["speaker_b"]}
    turns={};order=[];
    for i,when,ts in locomo.sessions(s):
        for j,t in enumerate(ts):
            k=t["dia_id"]; turns[k]=locomo.turn_text(t); order.append((k,i,j))
    bags={k:tokens(v) for k,v in turns.items()}; n=len(turns)
    pos={k:p for p,(k,_,_) in enumerate(order)}; sess={k:i for k,i,_ in order}
    mid=Counter(); 
    raw={k:ents(v) for k,v in turns.items()}
    for k,es in raw.items():
        for w,init in es:
            if not init: mid[w]+=1
    te={}
    for k,es in raw.items():
        te[k]={w for w,init in es if (not init or mid[w]>0)}
    inv=defaultdict(set)
    for k,es in te.items():
        for w in es: inv[w].add(k)
    # hub cap: fixed before any run: an entity in >2% of turns (min 5) gives no bridge; speakers never bridge
    cap=max(5,int(.02*n))
    bridge={w:v for w,v in inv.items() if len(v)<=cap and len(v)>1 and w not in speakers}
    ents_seen["turns"]+=n; ents_seen["turns_with_entity"]+=sum(1 for k in te if te[k]-speakers); ents_seen["bridges"]+=len(bridge); ents_seen["convs"]+=1
    tf=Counter(w for b in bags.values() for w in set(b))
    for qn,qa in enumerate(s["qa"]):
        gold={e.strip() for e in (qa.get("evidence") or []) if e.strip() in turns}
        if not gold: continue
        cat=locomo.CATEGORIES[qa["category"]]; words=sorted(set(tokens(qa["question"])))
        kw=[i for _,i in sorted(bm25(words,bags,n))][:50]
        seeds=kw[:5]
        # adjacency
        adj=[]
        for x in seeds:
            for d in (-1,1):
                p=pos[x]+d
                if 0<=p<len(order) and sess[order[p][0]]==sess[x]: adj.append(order[p][0])
        # entity bridge (1 hop): seed -> entity -> turns; plus entities named in the question
        ent_score=defaultdict(float)
        qents={w for w in bridge if re.search(rf"\b{re.escape(w)}\b",qa["question"])}
        for x in seeds:
            for w in te[x]:
                if w in bridge:
                    for y in bridge[w]:
                        if y!=x: ent_score[y]+=1/len(bridge[w])
        for w in qents:
            for y in bridge[w]: ent_score[y]+=1/len(bridge[w])
        ent=[i for i,_ in sorted(ent_score.items(),key=lambda x:(-x[1],x[0]))]
        # text-only control: pseudo-relevance feedback: rare terms from seeds, BM25 again (no graph)
        seedterms=Counter(w for x in seeds for w in set(bags[x]) if w not in words)
        rare=[w for w,_ in sorted(seedterms.items(),key=lambda x:(tf[x[0]],x[0])) if 2<=tf[w]<=cap][:10]
        prf=[i for _,i in sorted(bm25(rare,bags,n))][:50] if rare else []
        ranks={"keyword":kw,"adjacency":rrf([kw,list(dict.fromkeys(adj))]),"entity":rrf([kw,ent]),
               "entity+adjacency":rrf([kw,ent,list(dict.fromkeys(adj))]),"prf-control":rrf([kw,prf])}
        for name,r in ranks.items():
            rows.append(dict(q=f"{sid}:{qn}",cat=cat,sys=name,r5=len(set(r[:5])&gold)/len(gold),r10=len(set(r[:10])&gold)/len(gold),full5=gold<=set(r[:5]),full10=gold<=set(r[:10])))
        reach[cat].append(dict(kw50=len(set(kw)&gold)/len(gold),
            hop=len((set(seeds)|set(ent_score))&gold)/len(gold),adj=len((set(seeds)|set(adj))&gold)/len(gold),
            gold_ent=sum(1 for g in gold if te[g]&set(bridge))/len(gold),nogo=sum(1 for g in gold if not set(bags[g])&set(words))/len(gold),ngold=len(gold),exp=len(ent_score)))
print(dict(ents_seen))
cats=sorted({r["cat"] for r in rows})
systems=["keyword","prf-control","adjacency","entity","entity+adjacency"]
for c in cats+["ALL"]:
    sel=[r for r in rows if c=="ALL" or r["cat"]==c]
    n=len(sel)//len(systems)
    line=f"{c:12} n={n:3} "
    for s in systems:
        x=[r for r in sel if r["sys"]==s]
        line+=f"| {s[:9]:9} R5 {statistics.mean(r['r5'] for r in x):.3f} R10 {statistics.mean(r['r10'] for r in x):.3f} "
    print(line)
print("path complete (all gold in top k), multi-hop:")
sel=[r for r in rows if r["cat"]=="multi-hop"]
for s in systems:
    x=[r for r in sel if r["sys"]==s]; print(" ",s,round(statistics.mean(r['full5'] for r in x),3),round(statistics.mean(r['full10'] for r in x),3))
base={r["q"]:r for r in rows if r["sys"]=="keyword"}
for s in systems[1:]:
    for c in ("multi-hop","single-hop","temporal","adversarial"):
        x=[r for r in rows if r["sys"]==s and r["cat"]==c]
        w=sum(r["r10"]>base[r["q"]]["r10"] for r in x);l=sum(r["r10"]<base[r["q"]]["r10"] for r in x)
        print(f"  paired R@10 {s:17}{c:12} better {w} worse {l} of {len(x)}")
print("reachability (mean per question)")
for c,v in reach.items():
    print(f" {c:12} n={len(v)} gold/q {statistics.mean(x['ngold'] for x in v):.2f} kw50 {statistics.mean(x['kw50'] for x in v):.3f} seeds+1hop-entity {statistics.mean(x['hop'] for x in v):.3f} seeds+adj {statistics.mean(x['adj'] for x in v):.3f} gold-with-bridge-entity {statistics.mean(x['gold_ent'] for x in v):.3f} gold-no-question-word {statistics.mean(x['nogo'] for x in v):.3f} expansions {statistics.mean(x['exp'] for x in v):.1f}")
