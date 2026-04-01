"""Tests pour scripts/run_loop.py"""

import pytest
from scripts.run_loop import split_eval_set


class TestSplitEvalSet:
    def test_sizes(self, eval_set: list[dict]) -> None:
        train, test = split_eval_set(eval_set, holdout=0.4)
        assert len(train) + len(test) == len(eval_set)

    def test_no_duplicates(self, eval_set: list[dict]) -> None:
        train, test = split_eval_set(eval_set, holdout=0.4)
        all_queries = [e["query"] for e in train + test]
        assert len(set(all_queries)) == len(all_queries)

    def test_stratified(self, eval_set: list[dict]) -> None:
        train, test = split_eval_set(eval_set, holdout=0.4)
        # Les deux sets doivent contenir des triggers ET des no-triggers
        assert any(e["should_trigger"] for e in train)
        assert any(not e["should_trigger"] for e in train)
        assert any(e["should_trigger"] for e in test)
        assert any(not e["should_trigger"] for e in test)

    def test_reproducible(self, eval_set: list[dict]) -> None:
        t1, v1 = split_eval_set(eval_set, seed=42)
        t2, v2 = split_eval_set(eval_set, seed=42)
        assert t1 == t2
        assert v1 == v2

    def test_different_seeds(self, eval_set: list[dict]) -> None:
        t1, _ = split_eval_set(eval_set, seed=42)
        t2, _ = split_eval_set(eval_set, seed=99)
        # Avec des graines différentes, les splits doivent être différents
        assert t1 != t2

    def test_holdout_respected(self, eval_set: list[dict]) -> None:
        _, test = split_eval_set(eval_set, holdout=0.4)
        # Environ 40% en test (avec au moins 1 par groupe)
        assert 3 <= len(test) <= 6

    def test_single_item_each_side(self) -> None:
        minimal = [
            {"query": "a", "should_trigger": True},
            {"query": "b", "should_trigger": False},
        ]
        train, test = split_eval_set(minimal, holdout=0.5)
        assert len(train) + len(test) == 2
