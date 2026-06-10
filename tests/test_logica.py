import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.frontend.interfata import hash_password, verify_password


def test_hashing_parola():
    parola_clara = "ParolaGrea123!"
    hash_generat = hash_password(parola_clara)

    # Parola corectă trebuie să fie acceptată
    assert verify_password(parola_clara, hash_generat) is True

    # Parola greșită trebuie să fie respinsă
    assert verify_password("parola_gresita", hash_generat) is False
