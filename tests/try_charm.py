#!/usr/bin/env python3

from charm.toolbox.pairinggroup import PairingGroup, G1, ZR, pair
import time

def main():
    print("--- Charm-Crypto Environment Test ---")

    # 1. 初始化配对群
    # SS512 是一个 Type-F 对称配对 (symmetric pairing)
    # 这是安装中最需要测试的部分
    print("Step 1: Initializing PairingGroup('SS512')...")
    try:
        start_time = time.time()
        group = PairingGroup('SS512')
        end_time = time.time()
        print(f"✅ SUCCESS: PairingGroup initialized in {end_time - start_time:.4f} seconds.")
    except Exception as e:
        print(f"❌ FAILURE: Could not initialize PairingGroup.")
        print(f"Error details: {e}")
        print("\nTroubleshooting:")
        print("1. Did you run 'pip install charm-crypto'?")
        print("2. Is the PBC library (libpbc.so) and GMP (libgmp.so) installed?")
        print("3. Is 'LD_LIBRARY_PATH' set correctly (if you installed from source)?")
        return

    # 2. 生成随机元素
    print("\nStep 2: Generating random elements...")
    try:
        # g 是 G1 中的一个生成元
        g = group.random(G1)
        # a, b 是 ZR (整数环) 中的随机指数
        a = group.random(ZR)
        b = group.random(ZR)
        print("✅ SUCCESS: Random elements g, a, b generated.")
    except Exception as e:
        print(f"❌ FAILURE: Could not generate random elements.")
        print(f"Error details: {e}")
        return

    # 3. 测试双线性属性
    # 我们将验证 e(g^a, g^b) == e(g, g)^(a*b)
    print("\nStep 3: Testing the bilinear property...")

    # 计算左侧: e(g^a, g^b)
    left_side = pair(g ** a, g ** b)
    print(f"  Computed LHS: e(g^a, g^b)")

    # 计算右侧: e(g, g)^(a*b)
    right_side = pair(g, g) ** (a * b)
    print(f"  Computed RHS: e(g, g)^(a*b)")

    # 4. 验证结果
    print("\n--- FINAL RESULT ---")
    if left_side == right_side:
        print("✅✅✅ TEST PASSED! ✅✅✅")
        print("The bilinear property holds. Your charm-crypto environment is working correctly.")
    else:
        print("❌❌❌ TEST FAILED! ❌❌❌")
        print("The bilinear property does not hold. There is an issue with your installation.")

if __name__ == "__main__":
    main()