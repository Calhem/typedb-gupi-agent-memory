import pytest

from gupi.embedding import ExactCosine, SimilaritySearch, cosine, decode, encode


def test_float32_round_trip():
    assert decode(encode([0.5, -1.25, 3.0])) == [0.5, -1.25, 3.0]


def test_exact_cosine_ranks_and_breaks_ties_by_id():
    search: SimilaritySearch = ExactCosine()
    candidates = [("b", [1.0, 0.0]), ("a", [1.0, 0.0]), ("c", [0.0, 1.0])]
    assert [cid for cid, _ in search.search([1.0, 0.1], candidates, k=2)] == ["a", "b"]


def test_a_replacement_implementation_fits_the_interface():
    class Fake:
        def search(self, query, candidates, k):
            return [(cid, 1.0) for cid, _ in list(candidates)[:k]]

    search: SimilaritySearch = Fake()
    assert search.search([1.0], [("x", [1.0])], k=1) == [("x", 1.0)]


def test_bad_vectors_are_rejected():
    with pytest.raises(ValueError):
        cosine([1.0], [1.0, 2.0])
    with pytest.raises(ValueError):
        cosine([0.0, 0.0], [1.0, 0.0])
