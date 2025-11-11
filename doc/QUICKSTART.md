# Quick Start Guide

Get started with Vector Commitments with Proofs of Smallness in 5 minutes!

## Installation

```bash
# Install charm-crypto (if not already installed)
pip install charm-crypto

# Navigate to the project directory
cd try1028

# Run tests to verify installation
python -m pytest tests/test_formulas.py -v
```

## Basic Usage

### 1. Setup and CRS Generation

```python
from vc_smallness import setup, keygen_crs
from charm.toolbox.pairinggroup import ZR

# Initialize pairing group (MNT224 curve)
params = setup('MNT224')
group = params['group']

# Generate Common Reference String for vectors of length n=16
crs = keygen_crs(n=16, group=group)
print(f"CRS generated for n={crs['n']}")
```

### 2. Simple Commitment and Opening

```python
from vc_smallness.commit import commit_G
from vc_smallness.proofs import prove_point_open
from vc_smallness.verify import verify_1

# Create a message vector
m = [group.random(ZR) for _ in range(16)]
gamma = group.random(ZR)

# Commit to the message
C = commit_G(m, gamma, crs)
print("Commitment created!")

# Open at position i=5
i = 5
pi_5 = prove_point_open(C, m, gamma, i, crs)
print(f"Opening proof for position {i} generated!")

# Verify the opening (using aggregated verification with single position)
t = [group.init(ZR, 0)] * 16
t[i-1] = group.init(ZR, 1)  # Weight 1 at position i
pis = [prove_point_open(C, m, gamma, j, crs) for j in range(1, 17)]

assert verify_1(C, pis, t, m, crs)
print("✅ Verification successful!")
```

### 3. Range Proof Example

```python
from vc_smallness.commit import commit_Ghat, commit_V, bits_to_scalar, scalar_to_bits
from vc_smallness.proofs import prove_point_open, prove_x
from vc_smallness.verify import verify_9

# Setup
params = setup('MNT224')
group = params['group']
crs = keygen_crs(n=16, group=group)

# Prove that a value is in range [0, 2^8 - 1] (8 bits)
value = 42
ell = 8

# Convert to bits
x_bits_int = scalar_to_bits(value, ell)
x_bits = [group.init(ZR, b) for b in x_bits_int]
x_scalar = bits_to_scalar(x_bits_int, group)

# Pad to length n
x_bits_padded = x_bits + [group.init(ZR, 0)] * (16 - ell)

# Create commitments
gamma = group.random(ZR)
r = group.random(ZR)
C_hat = commit_Ghat(x_bits_padded, gamma, crs)
V_hat = commit_V(x_scalar, r, crs)

# Generate proofs
bit_proofs = [prove_point_open(C_hat, x_bits_padded, gamma, i, crs) 
              for i in range(1, ell + 1)]
pi_x = prove_x(bit_proofs, r, crs)

# Verify
assert verify_9(C_hat, V_hat, pi_x, ell, crs)
print(f"✅ Range proof for value {value} verified!")
```

### 4. Binary Vector Proof

```python
from vc_smallness.commit import commit_Ghat, commit_Cy
from vc_smallness.proofs import prove_y
from vc_smallness.verify import verify_7

# Setup
params = setup('MNT224')
group = params['group']
crs = keygen_crs(n=8, group=group)

# Create binary vectors (both x and y must be binary for orthogonality)
x = [group.init(ZR, 1), group.init(ZR, 0), group.init(ZR, 1), group.init(ZR, 1),
     group.init(ZR, 0), group.init(ZR, 1), group.init(ZR, 0), group.init(ZR, 0)]
y = [group.init(ZR, 0), group.init(ZR, 1), group.init(ZR, 1), group.init(ZR, 0),
     group.init(ZR, 1), group.init(ZR, 0), group.init(ZR, 1), group.init(ZR, 1)]

gamma = group.random(ZR)
gamma_y = group.random(ZR)

# Commit
C_hat = commit_Ghat(x, gamma, crs)
C_y = commit_Cy(y, x, gamma_y, crs)

# Generate orthogonality proof (proves y is binary)
pi_y = prove_y(x, y, gamma, gamma_y, crs)

# Verify
assert verify_7(C_hat, C_y, pi_y, y, crs)
print("✅ Binary vector proof verified!")
```

### 5. Aggregated Proof

```python
from vc_smallness.commit import commit_Ghat, commit_Cy
from vc_smallness.proofs import prove_eq, prove_y, aggregate_pi
from vc_smallness.fs_oracles import H_agg
from vc_smallness.verify import verify_16

# Setup
params = setup('MNT224')
group = params['group']
crs = keygen_crs(n=8, group=group)

# Binary vectors
x = [group.init(ZR, i % 2) for i in range(8)]
y = [group.init(ZR, (i+1) % 2) for i in range(8)]

gamma = group.random(ZR)
gamma_y = group.random(ZR)

# Commit
C_hat = commit_Ghat(x, gamma, crs)
C_y = commit_Cy(y, x, gamma_y, crs)

# Generate challenge weights
t = [group.random(ZR) for _ in range(8)]

# Generate individual proofs
pi_eq = prove_eq(t, y, x, gamma, gamma_y, crs)
pi_y = prove_y(x, y, gamma, gamma_y, crs)

# Generate aggregation challenges
delta_eq, delta_y = H_agg(C_hat, C_hat, C_y, group)

# Aggregate proofs
pi = aggregate_pi(pi_eq, pi_y, delta_eq, delta_y, crs)

# Verify aggregated proof
assert verify_16(C_hat, C_y, pi, delta_eq, delta_y, t, y, crs)
print("✅ Aggregated proof verified!")
```

## Running Tests

```bash
# Run all tests
python -m pytest tests/test_formulas.py -v

# Run specific test
python -m pytest tests/test_formulas.py::test_eq_1_positive -v

# Run with detailed output
python -m pytest tests/test_formulas.py -v --tb=short

# Run quietly
python -m pytest tests/test_formulas.py -q
```

## Common Patterns

### Creating Random Vectors

```python
# Random scalar vector
m = [group.random(ZR) for _ in range(n)]

# Binary vector
x = [group.init(ZR, 0) if i % 2 == 0 else group.init(ZR, 1) for i in range(n)]

# Specific values
y = [group.init(ZR, val) for val in [1, 0, 1, 1, 0, 0, 1, 0]]
```

### Working with Bits

```python
from vc_smallness.commit import bits_to_scalar, scalar_to_bits

# Convert integer to bits
value = 42
ell = 8
bits = scalar_to_bits(value, ell)  # [0, 1, 0, 1, 0, 1, 0, 0]

# Convert bits to integer
scalar = bits_to_scalar(bits, group)
assert int(scalar) == value
```

### Checking Verification

```python
# All verification functions return bool
result = verify_1(C, pis, t, m, crs)
if result:
    print("✅ Verification passed!")
else:
    print("❌ Verification failed!")
```

## Troubleshooting

### Import Error

```python
# If you get "ModuleNotFoundError: No module named 'vc_smallness'"
# Make sure you're in the try1028 directory
import sys
sys.path.insert(0, '/path/to/try1028')
```

### Charm-crypto Installation Issues

```bash
# If pip install fails, try installing from source:
git clone https://github.com/JHUISI/charm.git
cd charm
./configure.sh
make install
```

### Curve Not Supported

```python
# If MNT224 is not available, the system will automatically fall back to BN254 or SS512
params = setup('MNT224')  # Will try BN254, then SS512 if MNT224 fails
```

### Test Failures

```bash
# If tests fail, check charm-crypto installation:
python -c "from charm.toolbox.pairinggroup import PairingGroup; print('OK')"

# Check if MNT224 is available:
python -c "from charm.toolbox.pairinggroup import PairingGroup; g = PairingGroup('MNT224'); print('MNT224 OK')"
```

## Next Steps

1. **Read the README**: Comprehensive guide with more examples
2. **Check IMPLEMENTATION_NOTES**: Detailed implementation details
3. **Review SECURITY_NOTES**: Important security considerations
4. **Explore the code**: All functions have detailed docstrings

## API Reference

### Main Functions

- `setup(curve_name)` - Initialize pairing group
- `keygen_crs(n, group)` - Generate CRS for vectors of length n
- `commit_G(m, gamma, crs)` - Commit to vector m in G1
- `commit_Ghat(x, gamma, crs)` - Commit to vector x in G2
- `commit_Cy(y, x, gamma_y, crs)` - Hadamard commitment
- `commit_V(x_scalar, r, crs)` - Integer commitment
- `prove_point_open(C, m, gamma, i, crs)` - Point opening proof
- `prove_eq(t, y, x, gamma, gamma_y, crs)` - Equality proof
- `prove_y(x, y, gamma, gamma_y, crs)` - Orthogonality proof
- `prove_x(bit_proofs, r, crs)` - Range proof
- `verify_1(C, pis, t, m, crs)` - Verify equation (1)
- `verify_5(C_hat, C_y, t, y, pi_eq, crs)` - Verify equation (5)
- `verify_7(C_hat, C_y, pi_y, y, crs)` - Verify equation (7)
- `verify_9(C_hat, V_hat, pi_x, ell, crs)` - Verify equation (9)
- `verify_16(C_hat, C_y, pi, delta_eq, delta_y, t, y, crs)` - Verify equation (16)

## Support

For questions or issues:
1. Check the documentation files (README.md, IMPLEMENTATION_NOTES.md)
2. Review the test files for usage examples
3. Refer to the paper for mathematical details

## License

Research and educational use only. See LICENSE file for details.

---

**Happy Coding! 🚀**

