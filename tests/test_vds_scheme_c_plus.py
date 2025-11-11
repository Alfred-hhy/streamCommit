"""
End-to-End Integration Tests for VDS Scheme C+
===============================================

This module tests the complete VDS (Verifiable Data Streaming) scheme with:
- Data Owner (DO): Creates and signs batches, manages revocation
- Storage Server (SS): Stores secrets and generates proofs
- Verifier (DC/DA): Verifies proofs

Test Coverage:
--------------
1. Happy Path - DC (Data Consumer interactive query)
2. Happy Path - DA (Data Auditor non-interactive audit)
3. Rollback Attack Test (revocation security)
4. Binding Failure Test (signature security)
5. Tamper Failure Test (VC security)
6. Time Proofs Test (TODO: requires range proof implementation)

Security Properties Tested:
----------------------------
- Signature binding prevents mix-and-match attacks
- Accumulator prevents rollback attacks
- VC proofs prevent data tampering
"""

import pytest
from charm.toolbox.pairinggroup import ZR
from vc_smallness import setup, keygen_crs
from vds_owner import DataOwner
from vds_server import StorageServer
from vds_verifier import Verifier


class TestVDSSchemeC:
    """Test suite for VDS Scheme C+ (with accumulator-based revocation)."""
    
    @pytest.fixture
    def setup_system(self):
        """
        Setup the complete VDS system.
        
        Returns
        -------
        dict
            System components: crs, group, DO, SS, Verifier
        """
        # Setup pairing group and CRS
        params = setup('MNT224')
        group = params['group']
        n = 8  # Vector size
        crs = keygen_crs(n=n, group=group)
        
        # Create Data Owner
        do = DataOwner(crs, group)
        
        # Create Storage Server (with initial accumulator keys from DO)
        initial_server_keys = do.get_initial_server_keys()
        ss = StorageServer(crs, initial_server_keys)
        
        # Create Verifier (with initial global_pk from DO)
        initial_global_pk = do.get_global_pk()
        verifier = Verifier(crs, initial_global_pk, group)
        
        return {
            'crs': crs,
            'group': group,
            'do': do,
            'ss': ss,
            'verifier': verifier,
            'n': n
        }
    
    def test_1_happy_path_dc(self, setup_system):
        """
        Test 1: Happy Path - Data Consumer (DC) Query.
        
        Workflow:
        1. DO creates batch_A
        2. SS stores batch_A
        3. DC requests sum (t = [1,1,...,1])
        4. SS generates proof
        5. Verifier verifies -> PASS
        """
        sys = setup_system
        do = sys['do']
        ss = sys['ss']
        verifier = sys['verifier']
        group = sys['group']
        n = sys['n']
        
        # Step 1: DO creates batch_A
        m_vector = [group.init(ZR, i + 10) for i in range(n)]  # [10, 11, 12, ..., 17]
        t_vector = [group.init(ZR, i + 1) for i in range(n)]   # [1, 2, 3, ..., 8]
        
        batch_id, public_header, secrets_for_ss = do.create_batch(m_vector, t_vector)
        
        # Step 2: SS stores batch_A
        ss.store_batch(batch_id, public_header, secrets_for_ss)
        
        # Step 3: DC requests sum (t_challenge = [1,1,...,1])
        t_challenge = [group.init(ZR, 1) for _ in range(n)]
        
        # Step 4: SS generates proof
        f_current = do.get_global_pk()["f_current"]
        x_result, pi_audit, pi_non = ss.generate_dc_data_proof(batch_id, t_challenge, f_current)
        
        # Step 5: Verifier verifies
        is_valid = verifier.verify_dc_query(public_header, t_challenge, x_result, pi_audit, pi_non)
        
        assert is_valid, "Test 1 failed: DC query verification should pass"
        print("✅ Test 1 passed: DC query verification successful")
    
    def test_2_happy_path_da(self, setup_system):
        """
        Test 2: Happy Path - Data Auditor (DA) Audit.
        
        Workflow:
        1. DO creates batch_A
        2. SS stores batch_A
        3. DA requests audit
        4. SS generates NIZK proof (with Fiat-Shamir challenge)
        5. Verifier verifies -> PASS
        """
        sys = setup_system
        do = sys['do']
        ss = sys['ss']
        verifier = sys['verifier']
        group = sys['group']
        n = sys['n']
        
        # Step 1: DO creates batch_A
        m_vector = [group.init(ZR, i + 20) for i in range(n)]  # [20, 21, 22, ..., 27]
        t_vector = [group.init(ZR, i + 1) for i in range(n)]   # [1, 2, 3, ..., 8]
        
        batch_id, public_header, secrets_for_ss = do.create_batch(m_vector, t_vector)
        
        # Step 2: SS stores batch_A
        ss.store_batch(batch_id, public_header, secrets_for_ss)
        
        # Step 3 & 4: DA requests audit, SS generates NIZK proof
        f_current = do.get_global_pk()["f_current"]
        x_result_random, pi_audit_zk, t_challenge_zk, pi_non = ss.generate_da_audit_proof(batch_id, f_current)
        
        # Step 5: Verifier verifies
        is_valid = verifier.verify_da_audit(public_header, n, x_result_random, pi_audit_zk, t_challenge_zk, pi_non)
        
        assert is_valid, "Test 2 failed: DA audit verification should pass"
        print("✅ Test 2 passed: DA audit verification successful")
    
    def test_3_rollback_attack(self, setup_system):
        """
        Test 3: Rollback Attack Prevention.
        
        Workflow:
        1. DO creates batch_A
        2. SS stores batch_A
        3. DC queries batch_A -> PASS
        4. DO revokes batch_A (updates f and global_pk)
        5. SS and Verifier update their keys
        6. DC queries batch_A again -> FAIL (revoked)
        """
        sys = setup_system
        do = sys['do']
        ss = sys['ss']
        verifier = sys['verifier']
        group = sys['group']
        n = sys['n']
        
        # Step 1 & 2: DO creates and SS stores batch_A
        m_vector = [group.init(ZR, i + 30) for i in range(n)]
        t_vector = [group.init(ZR, i + 1) for i in range(n)]
        batch_id, public_header, secrets_for_ss = do.create_batch(m_vector, t_vector)
        ss.store_batch(batch_id, public_header, secrets_for_ss)
        
        # Step 3: DC queries batch_A (should pass)
        t_challenge = [group.init(ZR, 1) for _ in range(n)]
        f_current_before = do.get_global_pk()["f_current"]
        x_result, pi_audit, pi_non = ss.generate_dc_data_proof(batch_id, t_challenge, f_current_before)
        is_valid_before = verifier.verify_dc_query(public_header, t_challenge, x_result, pi_audit, pi_non)
        assert is_valid_before, "Batch should be valid before revocation"
        
        # Step 4: DO revokes batch_A
        sigma_to_revoke = public_header["sigma"]
        g_s_q_new, new_global_pk, sigma_bytes = do.revoke_batch(sigma_to_revoke)

        # Step 5: SS and Verifier update
        ss.add_server_key(g_s_q_new)
        ss.add_revoked_item(sigma_bytes)  # Add to blacklist
        verifier.update_global_pk(new_global_pk)
        
        # Step 6: DC queries batch_A again (should fail - revoked)
        f_current_after = new_global_pk["f_current"]
        x_result_2, pi_audit_2, pi_non_2 = ss.generate_dc_data_proof(batch_id, t_challenge, f_current_after)
        is_valid_after = verifier.verify_dc_query(public_header, t_challenge, x_result_2, pi_audit_2, pi_non_2)
        
        assert not is_valid_after, "Test 3 failed: Revoked batch should fail verification"
        print("✅ Test 3 passed: Rollback attack prevented")
    
    def test_4_binding_failure(self, setup_system):
        """
        Test 4: Signature Binding Failure (Mix-and-Match Attack).
        
        Workflow:
        1. DO creates batch_1 and batch_2
        2. Attacker tries to mix C_data_1 with C_time_2 and sigma_1
        3. Verification should fail (signature doesn't match)
        """
        sys = setup_system
        do = sys['do']
        verifier = sys['verifier']
        group = sys['group']
        n = sys['n']
        
        # Step 1: DO creates two batches
        m1 = [group.init(ZR, i + 40) for i in range(n)]
        t1 = [group.init(ZR, i + 1) for i in range(n)]
        batch_id_1, header_1, secrets_1 = do.create_batch(m1, t1)
        
        m2 = [group.init(ZR, i + 50) for i in range(n)]
        t2 = [group.init(ZR, i + 2) for i in range(n)]
        batch_id_2, header_2, secrets_2 = do.create_batch(m2, t2)
        
        # Step 2: Attacker creates mixed header
        mixed_header = {
            "C_data": header_1["C_data"],   # From batch_1
            "C_time": header_2["C_time"],   # From batch_2
            "sigma": header_1["sigma"]      # From batch_1
        }
        
        # Step 3: Try to verify (should fail)
        # We need a dummy pi_non (doesn't matter, signature check comes first)
        dummy_pi_non = (group.init(ZR, 1), group.init(ZR, 0))
        is_valid, _ = verifier._verify_precheck(mixed_header, dummy_pi_non)
        
        assert not is_valid, "Test 4 failed: Mixed header should fail signature verification"
        print("✅ Test 4 passed: Mix-and-match attack prevented")
    
    def test_5_tamper_failure(self, setup_system):
        """
        Test 5: Data Tampering Detection.
        
        Workflow:
        1. DO creates batch_1 with m = [10, 20, 30, ...]
        2. SS maliciously modifies m' = [10, 20, 31, ...]
        3. SS generates proof with m'
        4. Verification should fail (proof doesn't match commitment)
        """
        sys = setup_system
        do = sys['do']
        ss = sys['ss']
        verifier = sys['verifier']
        group = sys['group']
        n = sys['n']
        
        # Step 1: DO creates batch_1
        m_original = [group.init(ZR, (i + 1) * 10) for i in range(n)]  # [10, 20, 30, ..., 80]
        t_vector = [group.init(ZR, i + 1) for i in range(n)]
        batch_id, public_header, secrets_for_ss = do.create_batch(m_original, t_vector)
        
        # Step 2: SS stores batch (but will tamper later)
        ss.store_batch(batch_id, public_header, secrets_for_ss)
        
        # Step 3: SS maliciously modifies the data
        m_tampered = m_original.copy()
        m_tampered[2] = group.init(ZR, 31)  # Change 30 to 31
        
        # Manually modify SS's storage (simulating malicious SS)
        ss.storage[batch_id][1]["m"] = m_tampered
        
        # Step 4: DC queries with t = [1,1,...,1]
        t_challenge = [group.init(ZR, 1) for _ in range(n)]
        f_current = do.get_global_pk()["f_current"]
        
        # SS generates proof with tampered data
        x_result, pi_audit, pi_non = ss.generate_dc_data_proof(batch_id, t_challenge, f_current)
        
        # Step 5: Verification should fail
        is_valid = verifier.verify_dc_query(public_header, t_challenge, x_result, pi_audit, pi_non)
        
        assert not is_valid, "Test 5 failed: Tampered data should fail verification"
        print("✅ Test 5 passed: Data tampering detected")

    def test_6_time_proofs(self, setup_system):
        """
        Test 6: Time Range Proofs.

        Workflow:
        1. DO creates t_vector = [10, 20, 30] with l=8 bits
        2. SS generates single time proof for index=2 (value=20)
        3. Verifier verifies single time proof -> PASS
        4. (Optional) SS generates batch time proof
        5. (Optional) Verifier verifies batch time proof -> PASS
        """
        from vc_smallness.proofs import prove_range_proof
        from vc_smallness.verify import verify_range_proof

        sys = setup_system
        group = sys['group']
        crs = sys['crs']

        # Step 1: Create time vector
        t_vector = [10, 20, 30]
        l = 8  # 8-bit timestamps (max value 255)

        # Step 2: Generate single time proof for index=2 (value=20)
        t_value = group.init(ZR, t_vector[1])  # index=2 -> value=20
        proof = prove_range_proof(t_value, l, crs)

        # Step 3: Verify single time proof
        is_valid = verify_range_proof(proof, l, crs)

        assert is_valid, "Test 6 failed: Single time proof should pass"
        print("✅ Test 6 passed: Time range proof verification successful")

        # Test all values in t_vector
        for idx, t_val in enumerate(t_vector):
            t_zr = group.init(ZR, t_val)
            proof_i = prove_range_proof(t_zr, l, crs)
            is_valid_i = verify_range_proof(proof_i, l, crs)
            assert is_valid_i, f"Time proof for t[{idx}]={t_val} should pass"
            print(f"  ✓ Time proof for t[{idx}]={t_val} verified")

