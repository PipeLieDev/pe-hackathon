from app.utils import generate_short_code


def test_generate_short_code_default_length():
    code = generate_short_code()
    assert len(code) == 6
    assert code.isalnum()


def test_generate_short_code_custom_length():
    code = generate_short_code(length=10)
    assert len(code) == 10
    assert code.isalnum()


def test_generate_short_code_uniqueness():
    codes = {generate_short_code() for _ in range(100)}
    assert len(codes) > 90
