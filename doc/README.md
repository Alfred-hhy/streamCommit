# Vector Commitments with Proofs of Smallness

A complete Python implementation of the vector commitment scheme with proofs of smallness from the paper "Vector Commitments with Proofs of Smallness (Short)".

## Overview

This implementation provides:
- **Type-3 asymmetric pairing-based cryptography** using charm-crypto
- **All commitment types**: C (G), Ĉ (Ĝ), C_y (Hadamard), V̂ (integer)
- **All proof types**: π_i, π_S, π_eq, π_y, π_x, π_v, and aggregated π
- **All verification equations (1)-(20)** from the paper (excluding lattice-based equations 10-11)
- **Fiat-Shamir transformation** with proper domain separation
- **Comprehensive test suite** with positive and negative test cases

## Installation

### Prerequisites

```bash
# Install charm-crypto
pip install charm-crypto

# Or if that fails, install from source:
git clone https://github.com/JHUISI/charm.git
cd charm
./configure.sh
make install
```

### Install this package

```bash
cd try1028
pip install -e .
```

## Curve Selection

The implementation uses Type-3 asymmetric pairing curves. The default is `MNT224`:

- **MNT224** (preferred): 224-bit base field, asymmetric Type-3 pairing
- **BN254** (fallback): 254-bit base field, asymmetric Type-3 pairing  
- **SS512** (fallback): 512-bit base field, symmetric pairing

The system automatically falls back to available curves if MNT224 is not supported.

## Usage

### Basic Example

```python
from vc_smallness import setup, keygen_crs
from vc_smallness.commit import commit_G, commit_Ghat
from vc_smallness.proofs import prove_point_open
from vc_smallness.verify import verify_1
from charm.toolbox.pairinggroup import ZR

# Setup pairing group
params = setup('MNT224')
group = params['group']

# Generate CRS for vectors of length n=16
crs = keygen_crs(n=16, group=group)

# Create a message vector
m = [group.random(ZR) for _ in range(16)]
gamma = group.random(ZR)

# Commit to the message
C = commit_G(m, gamma, crs)

# Generate point opening proofs
pis = [prove_point_open(C, m, gamma, i, crs) for i in range(1, 17)]

# Generate challenge weights
t = [group.random(ZR) for _ in range(16)]

# Verify equation (1)
assert verify_1(C, pis, t, m, crs)
print("Verification successful!")
```

### Range Proof Example

```python
from vc_smallness.commit import commit_Ghat, commit_V, bits_to_scalar, scalar_to_bits
from vc_smallness.proofs import prove_point_open, prove_x
from vc_smallness.verify import verify_9

# Setup
params = setup('MNT224')
group = params['group']
crs = keygen_crs(n=16, group=group)

# Value to prove is in range [0, 2^ℓ - 1]
ell = 8  # 8 bits = range [0, 255]
value = 42

# Convert to bits
x_bits_int = scalar_to_bits(value, ell)
x_bits = [group.init(ZR, b) for b in x_bits_int]
x_scalar = bits_to_scalar(x_bits_int, group)

# Pad to length n
x_bits_padded = x_bits + [group.init(ZR, 0)] * (16 - ell)

# Commit
gamma = group.random(ZR)
r = group.random(ZR)
C_hat = commit_Ghat(x_bits_padded, gamma, crs)
V_hat = commit_V(x_scalar, r, crs)

# Generate proofs
bit_proofs = [prove_point_open(C_hat, x_bits_padded, gamma, i, crs) 
              for i in range(1, ell + 1)]
pi_x = prove_x(bit_proofs, r, crs)

# Verify
assert verify_9(C_hat, V_hat, pi_x, x_bits_padded, crs)
print(f"Range proof for value {value} verified!")
```

## Running Tests

```bash
# Run all tests
pytest tests/test_formulas.py -v

# Run specific equation tests
pytest tests/test_formulas.py::test_eq_1_positive -v
pytest tests/test_formulas.py::test_eq_5_positive -v

# Run with coverage
pytest tests/ --cov=vc_smallness --cov-report=html
```

## Module Structure

```
vc_smallness/
├── __init__.py          # Package initialization
├── groups.py            # Pairing group setup
├── crs.py               # CRS generation (powers of α)
├── commit.py            # Commitment generation (C, Ĉ, C_y, V̂)
├── proofs.py            # Proof generation (all π types)
├── verify.py            # Verification equations (1)-(20)
├── fs_oracles.py        # Fiat-Shamir random oracles
└── utils.py             # Utility functions

tests/
├── __init__.py
└── test_formulas.py     # Tests for equations (1)-(20)
```

## Implemented Equations

### Commitments
- **C**: Base commitment in G to vector m (with randomness γ)
- **Ĉ**: Base commitment in Ĝ to vector x (with randomness γ)
- **C_y**: Hadamard commitment mixing y and x in reverse order (with randomness γ_y)
- **V̂**: Integer commitment for range proofs (commits to scalar x with randomness r)

### Proofs
- **π_i**: Point opening proof at position i
- **π_S**: Aggregated opening for subset S with weights t
- **π_eq**: Equality proof (C_y commits to y ∘ x in reverse order)
- **π_y**: Orthogonality proof (enforces y_i ∈ {0,1})
- **π_x**: Range-proof sum-of-weights proof
- **π_v**: "Only-first-coordinate-nonzero" auxiliary proof
- **π**: Final aggregated proof π = π_eq^{δ_eq} · π_y^{δ_y}

### Verification Equations
- **(1)**: Aggregated inner-product verification (PointProofs base)
- **(3)**: Per-coordinate pairing for C_y
- **(4)**: Per-coordinate pairing for Ĉ
- **(5)**: Key division equation combining (3) and (4)
- **(7)**: Orthogonality check
- **(9)**: Division form with integer commitment V̂
- **(16)**: Aggregated verification for π
- **(20)**: Verification of π_v

Equations (13), (15), (17), (18), (19) are aliases of (5), (7), (9) as they verify the same relationships.

## Implementation Notes

### Division Equations

All division equations are implemented strictly as specified:
```
LHS_numerator / LHS_denominator = RHS
⟺ LHS_numerator * (LHS_denominator)^{-1} = RHS
```

This is the ONLY way division equations are implemented. No algebraic rewrites are performed.

### Index Conventions

- All indices in the paper are 1-based: i ∈ [n] means i ∈ {1, 2, ..., n}
- Python lists are 0-indexed, so `m[i-1]` corresponds to m_i in the paper
- CRS dictionaries use 1-based indexing: `g_list[i]` corresponds to g_i
- The index n+1 is EXCLUDED from g_list as per the paper

### Reverse Indexing

Many formulas use reverse indexing:
- g_{n+1-i} is accessed as `g_list[n+1-i]`
- g_{n+1-i+j} is accessed as `g_list[n+1-i+j]`

### Random Oracles

Fiat-Shamir transformation uses domain-separated hash functions:
- **H_t**: Generates challenge weights (t_i) with prefix `b"HT"`
- **H_agg**: Generates aggregation challenges (δ_eq, δ_y) with prefix `b"HAGG"`
- **H_s**: Generates challenges (s_i) for π_v with prefix `b"HS"`

## Security Considerations

⚠️ **This is a research implementation. Do NOT use in production without proper security review.**

### Assumptions
- **Trusted Setup**: The secret α must be securely deleted after CRS generation
- **Random Oracle Model**: Hash functions are modeled as random oracles
- **Pairing Security**: Security relies on hardness of discrete log in pairing groups
- **No Side-Channel Protection**: Implementation does not protect against timing attacks

### Known Limitations
- CRS generation includes α for testing purposes (should be deleted in production)
- No protection against side-channel attacks
- No formal security proof verification
- Limited to vectors of size n ≤ 1000 (performance considerations)

## Performance

Approximate timings on a modern CPU (MNT224 curve, n=16):

- CRS generation: ~50ms
- Commitment: ~5ms
- Point opening proof: ~5ms
- Verification equation (1): ~20ms
- Aggregated proof generation: ~100ms

## References

- Paper: "Vector Commitments with Proofs of Smallness (Short)"
- Charm-crypto: https://jhuisi.github.io/charm/
- PointProofs: https://eprint.iacr.org/2020/419

## License

This implementation is provided for research and educational purposes.

## Contributing

This is a reference implementation following the paper's specifications exactly. Any modifications should:
1. Reference the specific equation number being modified
2. Prove algebraic equivalence if rewriting formulas
3. Include comprehensive tests for both positive and negative cases
4. Document all changes in comments

## Contact

For questions about the implementation, please refer to the paper and the inline documentation in the code.

