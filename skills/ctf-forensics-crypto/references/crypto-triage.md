# Crypto Triage

## Attack-Condition Routing

| Signal | First Checks |
|---|---|
| RSA `e=3`, small message | low exponent / no padding |
| RSA same `n`, multiple `e` | common modulus |
| RSA close primes | Fermat factorization |
| RSA shared prime across moduli | GCD sweep |
| RSA partial key bits | Coppersmith/lattice if bounds fit |
| Reused nonce in stream/CTR/GCM | xor/known plaintext/tag failure |
| Reused ECDSA nonce | private key recovery |
| MT/random outputs | seed/state recovery |
| Hash starts with `0e` | PHP loose comparison / magic hash |
| Padding oracle | confirm oracle, then script bounded queries |
| Classical cipher | frequency, known plaintext, crib, transposition |
| Custom cipher | identify linearity, reversibility, small state, invariant |

## Required Notes

Before scripting, write:

- primitive
- all parameters
- suspected weakness
- mathematical condition
- expected solver output
- verification method

## Verification

Do at least one:

- decrypt and match flag format
- re-encrypt and match ciphertext
- run binary/server validation
- independently check recovered key against given samples
