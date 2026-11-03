"""`gupi`: a minimal command line for reviewing and resolving claims (standard library only).

    gupi --database NAME ingest conversation.json --create   # offline rule extractor, no API calls
    gupi queue                                              # hypotheses awaiting review, with conflicts
    gupi show CLAIM                                         # evidence, status, history
    gupi accept CLAIM [CLAIM ...] --by NAME [--reason TEXT]  # also: reject, retract
    gupi conflicts                                          # among believed claims
    gupi identities [--suggest]                             # suggested identities (never merged until accepted)
    gupi corrections                                        # suggested supersessions (newer replaces older)
    gupi supersede OLD NEW --by NAME [--reason TEXT]
    gupi unsupersede SUPERSESSION --by NAME [--reason TEXT]

Claim ids may be shortened to any unique prefix of the part after "claim:". Every decision needs --by.
The database defaults to $GUPI_DATABASE, then "gupi".
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

from typedb.driver import TransactionType

from gupi import review, typeql
from gupi.memory import Memory
from gupi.typedb.connection import transaction


class CliError(Exception):
    pass


def _labels(memory):
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        return {d["id"]: d["label"] or d["id"] for d in typeql.documents(
            tx, 'match $x isa referent; fetch { "id": $x.gupi-id, "label": $x.label };')}


def _resolve(memory, text):
    return memory.find_claim(text)


def _short(cid):
    return cid.split(":", 1)[1][:10]


def _describe(c, labels):
    roles = ", ".join(f"{r}={'/'.join(labels.get(x, x) for x in refs)}" for r, refs in c.roles.items())
    values = "".join(f" {k}={v!r}" for k, v in c.values.items() if k != "reason")
    return f"{'NOT ' if c.polarity == 'negative' else ''}{c.type}({roles}){values}"


def _period(c):
    v = c.valid

    def side(a, b):
        if a is None and b is None:
            return "?"
        if a == b or b is None:
            return f"{a.date()}" if a else f"<{b.date()}"
        return f"{a.date() if a else '?'}..{b.date()}"
    end = "now (as of " + str(v.to_earliest.date()) + ")" if c.valid_to_basis == "ongoing-at-observation" else side(v.to_earliest, v.to_latest)
    return f"from {side(v.from_earliest, v.from_latest)} to {end}"


def cmd_queue(memory, args, out):
    labels = _labels(memory)
    items = memory.review_queue(claim_type=args.type, limit=args.limit)
    if not items:
        print("Nothing awaiting review.", file=out)
    for i in items:
        c = i.claim
        quote = c.evidence[0].quote if c.evidence else ""
        print(f"{_short(c.id)}  {_describe(c, labels)}  [{c.basis or 'stated'}"
              + (f", confidence {c.confidence:.2f}" if c.confidence is not None else "") + "]", file=out)
        print(f"            {_period(c)}  “{quote}”", file=out)
        for x in i.conflicts:
            print(f"            ! {x.kind}: {x.reason}", file=out)
        if i.alternatives:
            print(f"            alternatives: {', '.join(_short(a) for a in i.alternatives)}", file=out)


def cmd_show(memory, args, out):
    c = _resolve(memory, args.claim)
    labels = _labels(memory)
    now = memory.clock()
    print(f"{c.id}\n  {_describe(c, labels)}\n  {_period(c)}\n  status now: {c.status_at(now).value}"
          + ("  (provisional generic statement)" if c.provisional else ""), file=out)
    for e in c.evidence:
        print(f"  evidence: {e.source_id}, said {e.observed_at.date() if e.observed_at else '?'}: “{e.quote}”", file=out)
    for s in c.supersessions:
        print(f"  supersession {s.id}: replaced by {_short(s.replacement)} "
              f"({'in force' if s.in_force_at(now) else 'withdrawn'})", file=out)
    print("  history:", file=out)
    for ev in review.history(c):
        print(f"    {ev.at:%Y-%m-%d %H:%M}  {ev.detail}", file=out)


def cmd_decide(memory, args, out):
    targets = [_resolve(memory, x) for x in args.claims]
    memory.review_many([(c.id, args.verdict) for c in targets], args.by, args.reason)
    for c in targets:
        print(f"{args.verdict}: {_short(c.id)}", file=out)


def cmd_conflicts(memory, args, out):
    from gupi import conflicts as k
    kinds = (k.CONTRADICTION, k.DIFFERING, k.CORROBORATION, k.SEPARATE) if args.all else (k.CONTRADICTION, k.DIFFERING)
    found = memory.conflicts(include=kinds)
    if not found:
        print("No conflicts among believed claims.", file=out)
    for x in found:
        print(f"{x.kind}: {' vs '.join(_short(i) for i in x.claim_ids)}  {x.reason}", file=out)


def cmd_identities(memory, args, out):
    if args.suggest:
        print(f"{len(memory.suggest_identities())} new suggestion(s) recorded as hypotheses.", file=out)
    labels = _labels(memory)
    now = memory.clock()
    for c in memory.identity_claims():
        a, b = c.roles["same"]
        print(f"{_short(c.id)}  {labels.get(a, a)} = {labels.get(b, b)}  [{c.status_at(now).value}]  "
              f"{c.values.get('reason', '')}", file=out)


def cmd_corrections(memory, args, out):
    found = memory.suggest_supersessions()
    if not found:
        print("No suggested corrections.", file=out)
    for s in found:
        print(f"supersede {_short(s['old'])} with {_short(s['new'])}: {s['reason']}", file=out)


def cmd_supersede(memory, args, out):
    old, new = _resolve(memory, args.old), _resolve(memory, args.new)
    sid = memory.supersede(old.id, new.id, reason=args.reason, decided_by=args.by)
    print(f"{_short(old.id)} superseded by {_short(new.id)} ({sid})", file=out)


def cmd_unsupersede(memory, args, out):
    result = memory.withdraw_supersession(args.supersession, args.by, args.reason)
    print("withdrawn" if result else "already withdrawn", file=out)


def cmd_ingest(memory, args, out):
    from gupi.extraction.pipeline import extract
    from gupi.extraction.rules import RuleExtractor
    from gupi.records import Batch, Context, Observation, Source
    conv = json.loads(open(args.file, encoding="utf-8").read())
    source = Source(f"src:{conv.get('source', 'conversation')}", "conversation")
    context = Context(f"conv:{conv['id']}", "conversation")
    obs = [Observation(source.id, m["key"], m["text"],
                       datetime.fromisoformat(m["at"].replace("Z", "+00:00")).astimezone(timezone.utc), context.id)
           for m in conv["messages"]]
    memory.ingest(Batch((source,), tuple(obs), contexts=(context,)))
    result = extract(memory, RuleExtractor(), obs)
    print(f"{len(obs)} message(s); {len(result.claims)} claim(s) extracted as hypotheses by the offline rule "
          f"extractor; {len(result.skipped)} already extracted; {len(result.rejected)} rejected.", file=out)


def build_parser():
    p = argparse.ArgumentParser(prog="gupi", description="Review and resolve GUPI claims.")
    p.add_argument("--database", default=os.environ.get("GUPI_DATABASE", "gupi"))
    sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("queue", help="hypotheses awaiting review")
    q.add_argument("--type")
    q.add_argument("--limit", type=int)
    s = sub.add_parser("show", help="one claim in full")
    s.add_argument("claim")
    for verdict, name in (("accepted", "accept"), ("rejected", "reject"), ("retracted", "retract")):
        d = sub.add_parser(name, help=f"record that claims are {verdict}")
        d.add_argument("claims", nargs="+")
        d.add_argument("--by", required=True)
        d.add_argument("--reason")
        d.set_defaults(verdict=verdict, command="decide")
    c = sub.add_parser("conflicts", help="conflicts among believed claims")
    c.add_argument("--all", action="store_true", help="also corroboration and separate periods")
    i = sub.add_parser("identities", help="identity suggestions and their status")
    i.add_argument("--suggest", action="store_true", help="look for new suggestions first")
    sub.add_parser("corrections", help="suggested supersessions")
    su = sub.add_parser("supersede", help="record that NEW replaces OLD")
    su.add_argument("old")
    su.add_argument("new")
    su.add_argument("--by", required=True)
    su.add_argument("--reason")
    un = sub.add_parser("unsupersede", help="withdraw a supersession")
    un.add_argument("supersession")
    un.add_argument("--by", required=True)
    un.add_argument("--reason")
    g = sub.add_parser("ingest", help="ingest a conversation file with the offline rule extractor")
    g.add_argument("file")
    g.add_argument("--create", action="store_true", help="create the database if it does not exist")
    return p


COMMANDS = {"queue": cmd_queue, "show": cmd_show, "decide": cmd_decide, "conflicts": cmd_conflicts,
            "identities": cmd_identities, "corrections": cmd_corrections, "supersede": cmd_supersede,
            "unsupersede": cmd_unsupersede, "ingest": cmd_ingest}


def main(argv=None, out=None, driver=None, clock=None):
    out = out or sys.stdout
    args = build_parser().parse_args(argv)
    try:
        memory = Memory.open(args.database, packs=("core", "people"), driver=driver,
                             create=getattr(args, "create", False), clock=clock)
        COMMANDS[args.command](memory, args, out)
    except (CliError, KeyError, LookupError, ValueError, RuntimeError) as e:
        print(f"gupi: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
