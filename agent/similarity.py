"""Contrôle anti-doublon : MinHash sur des groupes de 5 mots, sans dépendance externe."""
import hashlib
import re
import random

NUM_PERM = 128
PRIME = (1 << 61) - 1
_rng = random.Random(20261011)
_A = [_rng.randrange(1, PRIME) for _ in range(NUM_PERM)]
_B = [_rng.randrange(0, PRIME) for _ in range(NUM_PERM)]
SHINGLE = 5


def words(text):
    return re.findall(r"[a-zàâäçéèêëîïôöùûüÿœ0-9]+", text.lower())


def shingles(text):
    w = words(text)
    if len(w) < SHINGLE:
        return {" ".join(w)} if w else set()
    return {" ".join(w[i:i + SHINGLE]) for i in range(len(w) - SHINGLE + 1)}


def signature(text):
    sh = shingles(text)
    if not sh:
        return [0] * NUM_PERM
    hashes = [int.from_bytes(hashlib.blake2b(s.encode("utf8"), digest_size=8).digest(), "big") for s in sh]
    return [min((a * h + b) % PRIME for h in hashes) for a, b in zip(_A, _B)]


def jaccard(sig1, sig2):
    return sum(1 for x, y in zip(sig1, sig2) if x == y) / NUM_PERM


def most_similar(sig, index):
    """index : dict chemin -> signature. Retourne (chemin, score) du plus proche."""
    best = (None, 0.0)
    for path, other in index.items():
        score = jaccard(sig, other)
        if score > best[1]:
            best = (path, score)
    return best
