"""The CQL2 JSON encoder keeps the negation of NOT LIKE, NOT IN, and NOT BETWEEN.

The CQL2 text parser reads ``a NOT LIKE b`` as ``Like(..., not_=True)``, and the same for
``NOT IN`` and ``NOT BETWEEN``. CQL2 JSON has no negated forms of these operators, so the
encoder must wrap them in ``{"op": "not"}``, as ``NOT (a LIKE b)`` is encoded; without it, a
filter selects the very items it should leave out.
"""

import json

import pytest

from pygeofilter import ast
from pygeofilter.backends.cql2_json import to_cql2
from pygeofilter.parsers.cql2_json import parse as json_parse
from pygeofilter.parsers.cql2_text import parse as text_parse


def encoded(text):
    return json.loads(to_cql2(text_parse(text)))


@pytest.mark.parametrize(
    "negated, grouped",
    [
        ("attr NOT LIKE 'some%'", "NOT (attr LIKE 'some%')"),
        ("attr NOT IN ('a', 'b')", "NOT (attr IN ('a', 'b'))"),
        ("attr NOT BETWEEN 2 AND 5", "NOT (attr BETWEEN 2 AND 5)"),
        ("CASEI(attr) NOT LIKE CASEI('some%')", "NOT (CASEI(attr) LIKE CASEI('some%'))"),
    ],
)
def test_a_negated_predicate_is_encoded_as_not(negated, grouped):
    assert encoded(negated)["op"] == "not"
    assert encoded(negated) == encoded(grouped)


def test_not_like_is_encoded_with_its_pattern():
    assert encoded("attr NOT LIKE 'some%'") == {
        "op": "not",
        "args": [{"op": "like", "args": [{"property": "attr"}, "some%"]}],
    }


@pytest.mark.parametrize(
    "text",
    ["attr LIKE 'some%'", "attr IN ('a', 'b')", "attr BETWEEN 2 AND 5"],
)
def test_a_plain_predicate_is_not_negated(text):
    assert encoded(text)["op"] != "not"


@pytest.mark.parametrize(
    "text",
    ["attr NOT LIKE 'some%'", "attr NOT IN ('a', 'b')", "attr NOT BETWEEN 2 AND 5"],
)
def test_the_encoding_reads_back_as_a_negation(text):
    # CQL2 JSON read back gives Not(predicate), the same filter as the text.
    read_back = json_parse(to_cql2(text_parse(text)))
    assert isinstance(read_back, ast.Not)
    assert not read_back.sub_node.not_
