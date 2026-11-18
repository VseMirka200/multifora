import pytest

from core.pdf_engine.lexer import tokenize


def test_pdf_tokens_and_escaped_strings():
    tokens = list(tokenize(b"% comment\n<< /A#20B [(a(b)\\n\\051) <4869F>] /N -12.5 >>"))
    assert [(t.kind, t.value) for t in tokens] == [
        ("delimiter", b"<<"), ("name", b"A B"), ("delimiter", b"["),
        ("string", b"a(b)\n)"), ("string", b"Hi\xf0"), ("delimiter", b"]"),
        ("name", b"N"), ("word", b"-12.5"), ("delimiter", b">>"),
    ]
    assert tokens[0].offset == 10


@pytest.mark.parametrize("data", [b"(unclosed", b"<123", b"<zz>", b"/bad#xx"])
def test_rejects_invalid_tokens(data):
    with pytest.raises(ValueError):
        list(tokenize(data))
