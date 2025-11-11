# Implementation Notes

This document provides detailed notes on the implementation of the vector commitment scheme with proofs of smallness.

## Design Principles

### 1. Formula Fidelity

**Principle**: Implement formulas EXACTLY as written in the paper, with NO algebraic rewrites.

**Rationale**: 
- Ensures correctness by direct correspondence to the paper
- Makes verification easier (each function maps to one equation)
- Prevents subtle bugs from algebraic manipulations
- Facilitates auditing and review

**Example**:
```python
# Division equation (5): [e(...)] / [e(...)] = e(π_eq, ĝ)
# Implemented as: LHS_num * (LHS_den)^{-1} = RHS
lhs = gt_div(lhs_num, lhs_den, group)  # numerator * denominator^{-1}
rhs = pair(pi_eq, g_hat)
return gt_eq(lhs, rhs, group)
```

### 2. Index Conventions

**Paper Convention**: 1-based indexing
- Vectors: m = (m_1, m_2, ..., m_n)
- CRS elements: g_1, g_2, ..., g_{2n} (excluding g_{n+1})
- Ranges: i ∈ [n] means i ∈ {1, 2, ..., n}

**Python Convention**: 0-based indexing
- Lists: `m[0], m[1], ..., m[n-1]`
- Conversion: `m[i-1]` in code corresponds to m_i in paper

**CRS Dictionaries**: Use 1-based keys to match paper
```python
g_list = {1: g^α, 2: g^{α^2}, ..., n: g^{α^n}, n+2: g^{α^{n+2}}, ...}
# Note: g_{n+1} is EXCLUDED as per the paper
```

### 3. Reverse Indexing

Many formulas use reverse indexing patterns:
- g_{n+1-i}: Accessed as `g_list[n+1-i]`
- g_{n+1-i+j}: Accessed as `g_list[n+1-i+j]`

**Example from commit_Cy** (Equation 2):
```python
# C_y = g^{γ_y} · ∏_{j=1}^{n} g_{n+1-j}^{y_j x_j}
for j in range(1, n + 1):
    idx = n + 1 - j  # Reverse indexing
    C_y *= g_list[idx] ** (y[j-1] * x[j-1])
```

### 4. Division Equations

**Rule**: Division equations are ONLY implemented as `numerator * denominator^{-1}` in GT.

**Never** rewrite division equations algebraically. For example:
```python
# CORRECT:
lhs = gt_div(lhs_num, lhs_den, group)

# WRONG (algebraic rewrite):
# lhs = pair(g1_modified, g2)  # Don't move denominator terms
```

## Key Implementation Details

### CRS Generation (crs.py)

**Formula**: 
- g_i = g^{α^i} for i ∈ [2n] \ {n+1}
- ĝ_i = ĝ^{α^i} for i ∈ [n]

**Critical Detail**: Index n+1 is EXCLUDED from g_list

```python
def keygen_crs(n, group, alpha=None, g=None, g_hat=None):
    # Generate g_i for i in [2n] \ {n+1}
    g_list = {}
    for i in range(1, 2*n + 1):
        if i == n + 1:
            continue  # SKIP n+1
        g_list[i] = g ** (alpha ** i)
```

### Commitments (commit.py)

**C (Equation 1 context)**:
```python
# C = g^γ · ∏_{j=1}^{n} g_j^{m_j}
C = g ** gamma
for j in range(1, n + 1):
    C *= g_list[j] ** m[j-1]
```

**Ĉ (Equation 4 context)**:
```python
# Ĉ = ĝ^γ · ∏_{j=1}^{n} ĝ_j^{x_j}
C_hat = g_hat ** gamma
for j in range(1, n + 1):
    C_hat *= g_hat_list[j] ** x[j-1]
```

**C_y (Equation 2)** - Hadamard with reverse indexing:
```python
# C_y = g^{γ_y} · ∏_{j=1}^{n} g_{n+1-j}^{y_j x_j}
C_y = g ** gamma_y
for j in range(1, n + 1):
    idx = n + 1 - j  # Reverse!
    C_y *= g_list[idx] ** (y[j-1] * x[j-1])
```

**V̂ (Integer commitment)**:
```python
# V̂ = ĝ^r · ĝ_1^x
V_hat = g_hat ** r
V_hat *= g_hat_list[1] ** x_scalar
```

### Proofs (proofs.py)

**π_i (Point opening)** - Equation context from (1):
```python
# π_i = g_{n+1-i}^γ · ∏_{j∈[n], j≠i} g_{n+1-i+j}^{m_j}
pi_i = g_list[n+1-i] ** gamma
for j in range(1, n + 1):
    if j == i:
        continue
    idx = n + 1 - i + j
    pi_i *= g_list[idx] ** m[j-1]
```

**π_eq (Equation 12)** - Division form:
```python
# [e(∏ g_{n+1-i}^{t_i y_i}, Ĉ)] / [e(C_y, ∏ ĝ_i^{t_i})] = e(π_eq, ĝ)
# Rearranged: π_eq = [∏ g_{n+1-i}^{t_i y_i} · C_y^{-1}]^{γ} · [product of other terms]
```

**π_y (Equation 14)** - Orthogonality proof:
```python
# π_y = g^{γ γ_y} · (∏ g_{n+1-j}^{γ y_j(x_j-1)})
#       · ∏_{i=1}^{n} (g_{i}^{γ_y} · ∏_{j≠i} g_{n+1-j+i}^{y_j(x_j-1)})^{x_i}
```

**π_x (Range proof)**:
```python
# π_x = (∏_{i=1}^{ℓ} π_i^{2^{i-1}}) · g_n^{-r}
pi_x = group.init(G1, 1)
for i in range(1, ell + 1):
    weight = 2 ** (i - 1)
    pi_x *= bit_proofs[i-1] ** group.init(ZR, weight)
pi_x *= g_list[n] ** (-r)
```

### Verification (verify.py)

**Equation (1)** - Aggregated inner product:
```python
# e(C, ∏ ĝ_{n+1-i}^{t_i}) = e(∏ π_i^{t_i}, ĝ) · e(g_1, ĝ_n)^{∑ m_i t_i}
```

**Equation (5)** - Key division equation:
```python
# [e(∏ g_{n+1-i}^{t_i y_i}, Ĉ)] / [e(C_y, ∏ ĝ_i^{t_i})] = e(π_eq, ĝ)
lhs_num = pair(g_prod, C_hat)
lhs_den = pair(C_y, g_hat_prod)
lhs = gt_div(lhs_num, lhs_den, group)
rhs = pair(pi_eq, g_hat)
return gt_eq(lhs, rhs, group)
```

**Equation (7)** - Orthogonality check:
```python
# e(C_y · ∏ g_{n+1-j}^{-y_j}, Ĉ) = e(π_y, ĝ)
g_term = C_y
for j in range(1, n + 1):
    g_term *= g_list[n+1-j] ** (-y[j-1])
lhs = pair(g_term, C_hat)
rhs = pair(pi_y, g_hat)
return gt_eq(lhs, rhs, group)
```

**Equation (9)** - Range proof verification:
```python
# [e(∏ g_{n+1-i}^{2^{i-1}}, Ĉ)] / [e(g_n, V̂)] = e(π_x, ĝ)
# Note: ℓ is the number of bits, NOT the full vector length n
```

### Fiat-Shamir Oracles (fs_oracles.py)

**Domain Separation**: Each oracle uses a unique prefix
- H_t: prefix `b"HT"` - generates challenge weights t_i
- H_agg: prefix `b"HAGG"` - generates aggregation challenges δ_eq, δ_y
- H_s: prefix `b"HS"` - generates challenges s_i for π_v

**Serialization**: Uses charm-crypto's `objectToBytes` for group elements

```python
def H_t(C, C_hat, C_y, n, group, ctx_bytes=b""):
    prefix = b"HT"
    input_data = _serialize_for_hash(group, prefix, C, C_hat, C_y, ctx_bytes)
    hash_output = group.hash(input_data, ZR)
    # Expand to n challenges using domain separation
    return [group.hash(input_data + i.to_bytes(4, 'big'), ZR) for i in range(n)]
```

## Common Pitfalls and Solutions

### Pitfall 1: Index Off-by-One Errors

**Problem**: Mixing 0-based and 1-based indexing

**Solution**: Always use explicit conversions
```python
# Paper: m_i where i ∈ [n]
# Code: m[i-1] where i in range(1, n+1)
for i in range(1, n + 1):
    value = m[i-1]  # Explicit i-1
```

### Pitfall 2: Missing n+1 Exclusion

**Problem**: Including g_{n+1} in CRS

**Solution**: Explicit check in keygen_crs
```python
for i in range(1, 2*n + 1):
    if i == n + 1:
        continue  # MUST skip
```

### Pitfall 3: Wrong ℓ in Equation (9)

**Problem**: Using full vector length n instead of bit length ℓ

**Solution**: Pass ℓ as explicit parameter
```python
def verify_9(C_hat, V_hat, pi_x, ell, crs):  # ell, not x_bits
    for i in range(1, ell + 1):  # Only first ℓ bits
        ...
```

### Pitfall 4: Orthogonality Condition

**Problem**: Equation (7) fails with random x and binary y

**Explanation**: ∑ y_i x_i (x_i - 1) = 0 requires:
- EITHER y_i = 0 for all i
- OR x_i ∈ {0, 1} for all i where y_i = 1

**Solution**: Use binary x and y in tests
```python
x = [group.init(ZR, 0) if i % 3 == 0 else group.init(ZR, 1) for i in range(n)]
y = [group.init(ZR, 0) if i % 2 == 0 else group.init(ZR, 1) for i in range(n)]
```

## Testing Strategy

### Test Coverage

Each equation has:
1. **Positive test**: Correct proof verifies successfully
2. **Negative test**: Tampered proof/commitment fails verification

### Test Equations

- **(1)**: Aggregated inner product (base PointProofs)
- **(3)**: Per-coordinate C_y verification
- **(4)**: Per-coordinate Ĉ verification
- **(5)**: Division equation combining (3) and (4)
- **(7)**: Orthogonality check (binary enforcement)
- **(9)**: Range proof with integer commitment
- **(16)**: Aggregated proof verification
- **(20)**: Only-first-coordinate-nonzero proof

### Test Fixtures

```python
@pytest.fixture
def small_crs():
    """Small CRS for fast testing (n=8)"""
    params = setup('MNT224')
    group = params['group']
    crs = keygen_crs(n=8, group=group)
    return crs
```

## Performance Considerations

### Bottlenecks

1. **Pairing computations**: Most expensive operations
2. **Multi-exponentiations**: O(n) group operations
3. **CRS generation**: O(n) exponentiations

### Optimizations

1. **Batch pairings**: Use `pair_prod` for multiple pairings
2. **Multi-exponentiation**: Implemented in `multiexp_g1` and `multiexp_g2`
3. **Precomputation**: CRS can be generated once and reused

### Scalability

- **n ≤ 100**: Fast (< 1 second per operation)
- **n ≤ 1000**: Acceptable (< 10 seconds per operation)
- **n > 1000**: Slow (consider batching or parallelization)

## Debugging Tips

### Enable Verbose Logging

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Intermediate Values

```python
# In verification functions
print(f"LHS: {lhs}")
print(f"RHS: {rhs}")
print(f"Equal: {gt_eq(lhs, rhs, group)}")
```

### Verify CRS Structure

```python
from vc_smallness.crs import validate_crs
validate_crs(crs)  # Raises ValueError if invalid
```

### Test with Small n

```python
# Use n=2 or n=4 for manual verification
crs = keygen_crs(n=2, group=group)
```

## Future Improvements

1. **Batch verification**: Verify multiple proofs simultaneously
2. **Preprocessing**: Precompute common pairings
3. **Parallelization**: Parallelize multi-exponentiations
4. **Constant-time operations**: Protect against timing attacks
5. **Hardware acceleration**: Use GPU for pairing computations

## References

- Paper: "Vector Commitments with Proofs of Smallness (Short)"
- Charm-crypto documentation: https://jhuisi.github.io/charm/
- Type-3 pairings: https://eprint.iacr.org/2010/526

