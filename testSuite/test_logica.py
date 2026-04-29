import pytest
from interfata import hash_password, verify_password


def test_hashing_parola():
    parola_clara = "ParolaGrea123!"
    hash_generat = hash_password(parola_clara)

    # Parola corectă trebuie să fie acceptată
    assert verify_password(parola_clara, hash_generat) is True

    # Parola greșită trebuie să fie respinsă
    assert verify_password("parola_gresita", hash_generat) is False
