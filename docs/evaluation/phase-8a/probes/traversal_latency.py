import json, random, statistics, time, uuid
from datetime import datetime, timedelta, timezone
from gupi.memory import Memory
from gupi.records import Batch, Claim, Context, Evidence, Mention, Observation, Referent, Source
from gupi.temporal import ValidTime
from gupi.typedb.connection import connect, transaction
from gupi import typeql, retrieval
from typedb.driver import TransactionType
U=lambda y,m=1:datetime(y,m,1,tzinfo=timezone.utc)
class Clock:
    now=datetime(2025,1,1,tzinfo=timezone.utc)
    def __call__(self): return self.now
random.seed(7)
d=connect(); db="gupi-probe-"+uuid.uuid4().hex[:8]; c=Clock()
m=Memory.open(db,packs=("core","people"),driver=d,create=True,clock=c)
NP,NO=1500,100
people=[Referent(f"p:{i}","person",f"Person {i}") for i in range(NP)]
orgs=[Referent(f"o:{i}","organization",f"Org {i}") for i in range(NO)]
src=Source("src:s","synthetic"); ctx=Context("ctx:s","conversation")
try:
  t0=time.perf_counter()
  m.ingest(Batch((src,),(),tuple(people+orgs),contexts=(ctx,)))
  claims=[];obs=[];ments=[]
  def add(typ,roles,valid,text,values=None,names=()):
    o=Observation("src:s",f"k{len(obs)}",text,c.now,"ctx:s",None); obs.append(o)
    for r,n in names:
      i=text.index(n); ments.append(Mention(o.id,i,i+len(n),n,r,None,"probe"))
    claims.append(Claim(typ,roles,(Evidence(o.id,0,len(text)),),valid,values or {},method="probe",basis="explicit",commitment="certain",attribution_mode="direct"))
  for i,p in enumerate(people):
    # org 0 is a hub: a third of everyone worked there
    o=orgs[0] if i%3==0 else orgs[random.randrange(1,NO)]
    y=random.randrange(2015,2022)
    add("employment",{"employee":p.id,"employer":o.id},ValidTime(U(y),U(y),U(y+2),U(y+2)),f"{p.label} worked at {o.label} from {y} to {y+2}.",names=((p.id,p.label),(o.id,o.label)))
    if i%2==0:
      o2=orgs[random.randrange(1,NO)]; 
      add("employment",{"employee":p.id,"employer":o2.id},ValidTime(U(y+3),U(y+3,2),None,None),f"{p.label} joined {o2.label} in {y+3}.",names=((p.id,p.label),(o2.id,o2.label)))
    if i>0 and i%5==0:
      q=people[random.randrange(0,i)]
      add("reporting",{"report":p.id,"manager":q.id},ValidTime(U(y),U(y),None,None),f"{p.label} reports to {q.label}.",names=((p.id,p.label),(q.id,q.label)))
  for i in range(NO):
    j=(i+1)%NO
    add("statement",{"subject":orgs[i].id,"object":orgs[j].id},ValidTime(U(2020),U(2021),None,None),f"{orgs[i].label} acquired {orgs[j].label}.",{"predicate-text":"acquired"},names=((orgs[i].id,orgs[i].label),(orgs[j].id,orgs[j].label)))
  for s in range(0,len(obs),400):
    m.ingest(Batch(observations=tuple(obs[s:s+400])))
  c.now+=timedelta(minutes=1)
  for s in range(0,len(ments),400):
    m.ingest(Batch(mentions=tuple(ments[s:s+400])))
  c.now+=timedelta(minutes=1)
  ids_=[]
  for s in range(0,len(claims),400):
    m.ingest(Batch(claims=tuple(claims[s:s+400])))
  c.now+=timedelta(minutes=1)
  for s in range(0,len(claims),300):
    m.review_many([(x.id,"accepted") for x in claims[s:s+300]],"probe")
  c.now+=timedelta(minutes=1)
  print("built",len(obs),"obs",len(ments),"mentions",len(claims),"claims in",round(time.perf_counter()-t0,1),"s")
  t=c.now
  def bench(name,fn,n=20,args=None):
    ts=[];out=None
    with transaction(d,db,TransactionType.READ) as tx:
      for k in range(n):
        a=args[k%len(args)] if args else None
        t0=time.perf_counter(); out=fn(tx,a); ts.append(time.perf_counter()-t0)
    ts.sort(); print(f"{name:42} median {ts[len(ts)//2]*1000:7.1f} ms  p95 {ts[int(len(ts)*.95)]*1000:7.1f} ms  rows(last) {out}")
  HOP1="""match $a has gupi-id == $id; $c isa claim, links ($a), has gupi-id $cid; $c links ($n); not { $n is $a; }; $n has gupi-id $nid;
          let $b in believed_claim($c,$t); select $cid,$nid; limit 200;"""
  HOP2="""match $a has gupi-id == $id;
     $c1 isa claim, links ($a), has gupi-id $cid1; $c1 links ($n); not { $n is $a; };
     $c2 isa claim, links ($n), has gupi-id $cid2; not { $c2 is $c1; }; $c2 links ($m); not { $m is $n; }; not { $m is $a; };
     $m has gupi-id $mid; let $b1 in believed_claim($c1,$t); let $b2 in believed_claim($c2,$t);
     select $cid1,$cid2,$mid; limit %d;"""
  HOP2T="""match $a has gupi-id == $id;
     $c1 isa claim, links ($a), has gupi-id $cid1; $c1 links ($n); not { $n is $a; };
     $c2 isa claim, links ($n), has gupi-id $cid2; not { $c2 is $c1; }; $c2 links ($m); not { $m is $n; }; not { $m is $a; };
     not { $c1 has valid-to-latest $e1; $c2 has valid-from-earliest $s2; $e1 <= $s2; };
     not { $c2 has valid-to-latest $e2; $c1 has valid-from-earliest $s1; $e2 <= $s1; };
     $m has gupi-id $mid; let $b1 in believed_claim($c1,$t); let $b2 in believed_claim($c2,$t);
     select $cid1,$cid2,$mid; limit %d;"""
  ids_ord=[f"p:{i}" for i in range(1,NP) if i%3 and i%7==0][:40]
  ids_hub=[f"p:{i}" for i in range(3,NP,3)][:40]
  bench("1-hop, ordinary person",lambda tx,a:len(typeql.concept_rows(tx,HOP1,{"id":a,"t":t})),args=ids_ord)
  bench("1-hop, hub organisation (limit 200)",lambda tx,a:len(typeql.concept_rows(tx,HOP1,{"id":a,"t":t})),args=["o:0"])
  bench("2-hop, ordinary person (limit 200)",lambda tx,a:len(typeql.concept_rows(tx,HOP2%200,{"id":a,"t":t})),args=ids_ord)
  bench("2-hop, through the hub (limit 200)",lambda tx,a:len(typeql.concept_rows(tx,HOP2%200,{"id":a,"t":t})),args=ids_hub)
  bench("2-hop, through hub, no belief-free limit 2000",lambda tx,a:len(typeql.concept_rows(tx,HOP2%2000,{"id":a,"t":t})),n=8,args=ids_hub)
  bench("2-hop + temporal exclusion, ordinary",lambda tx,a:len(typeql.concept_rows(tx,HOP2T%200,{"id":a,"t":t})),args=ids_ord)
  bench("2-hop + temporal exclusion, hub (limit 200)",lambda tx,a:len(typeql.concept_rows(tx,HOP2T%200,{"id":a,"t":t})),args=ids_hub)
  some=[x.id for x in claims[:50]]
  bench("claims_by_ids full views, 50 claims",lambda tx,a:len(retrieval.claims_by_ids(tx,some)),n=8)
  obsid=[o.id for o in obs[:40]]
  SEED="""match $o has gupi-id == $id; evidence (supported: $c, support: $o); $c links ($n); $n has gupi-id $nid; $c has gupi-id $cid;
          let $b in believed_claim($c,$t); select $cid,$nid; limit 50;"""
  bench("seed observation to claims and players",lambda tx,a:len(typeql.concept_rows(tx,SEED,{"id":a,"t":t})),args=obsid)
  MENT="""match $o has gupi-id == $id; mentioning (container: $o, mention: $m); reference (mention: $m, referent: $x);
          reference (mention: $m2, referent: $x); mentioning (container: $o2, mention: $m2); not { $o2 is $o; }; $o2 has gupi-id $oid;
          select $oid; limit 200;"""
  bench("observation-mention-referent-observation",lambda tx,a:len(typeql.concept_rows(tx,MENT,{"id":a})),args=obsid)
finally:
  d.databases.get(db).delete()
