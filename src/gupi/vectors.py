"""Persistent embeddings of observations in TypeDB, and exact similarity search over a scope (ADR 0002, 0008).

`store` embeds observations in the given contexts that have no embedding for the embedder's model yet, and
writes them in batches (one query per batch via `given` rows). `search` reads only the vectors in scope and
ranks them with a SimilaritySearch (NumpyCosine when NumPy is available, otherwise ExactCosine).
"""

from typedb.driver import TransactionType

from gupi import embedding, ids, typeql
from gupi.typedb.connection import transaction

SCOPE = "match $c isa context, has gupi-id == $cid; containment (context: $c, member: $o); $o isa observation, has gupi-id $oid;"


def default_search():
    try:
        import numpy  # noqa: F401
        return embedding.NumpyCosine()
    except ImportError:
        return embedding.ExactCosine()


def missing(tx, context_ids, model):
    docs = typeql.documents_for(tx, SCOPE + """
        not { embedding-of (vector: $e, target: $o); $e has embedding-model == $m; };
        fetch { "id": $oid, "text": $o.content };""", [{"cid": c, "m": model} for c in sorted(set(context_ids))])
    return sorted({d["id"]: d["text"] for d in docs}.items())


def store(memory, embedder, context_ids, batch=256, progress=None):
    """Embed and store what is missing in these contexts. Returns how many embeddings were written.

    `progress(done, total)` is called after each batch, if given."""
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        todo = missing(tx, context_ids, embedder.model)
    written = 0
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        vectors = embedder.embed([text for _, text in chunk])
        rows = [{"oid": oid, "eid": ids.stable_id("embedding", embedder.model, oid), "v": embedding.encode(v),
                 "m": embedder.model, "d": len(v)} for (oid, _), v in zip(chunk, vectors)]
        with transaction(memory.driver, memory.database, TransactionType.WRITE) as tx:
            typeql.run_rows(tx, """match $o isa observation, has gupi-id == $oid;
                insert $e isa embedding, has gupi-id == $eid, has embedding-vector == $v, has embedding-model == $m,
                       has embedding-dim == $d; embedding-of (vector: $e, target: $o);""", rows)
        written += len(rows)
        if progress:
            progress(written, len(todo))
    return written


def vectors_in(tx, context_ids, model):
    rows = typeql.rows_for(tx, SCOPE + " embedding-of (vector: $e, target: $o); $e has embedding-model == $m, "
                                       "has embedding-vector $v;", [{"cid": c, "m": model} for c in sorted(set(context_ids))])
    return {r.get("oid").get_string(): embedding.decode(r.get("v").get_string()) for r in rows}


def search(memory, embedder, text, context_ids, k=10, similarity=None):
    """The k observations in scope most similar to `text`: [(observation id, cosine)]."""
    with transaction(memory.driver, memory.database, TransactionType.READ) as tx:
        candidates = vectors_in(tx, context_ids, embedder.model)
    (query,) = embedder.embed([text])
    return (similarity or default_search()).search(query, sorted(candidates.items()), k)
