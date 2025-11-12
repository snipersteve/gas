#!/usr/bin/env python3
"""测试USDT和USDC余额查询功能"""

from bsc_api import BSCBalanceChecker

def test_token_balances():
    checker = BSCBalanceChecker()

    # 测试地址（一个有USDT/USDC余额的地址）
    test_address = "0x4582710c09c3fbab6c4806a2d2bc0665a13b7e95"

    print(f"测试地址: {test_address}")
    print("=" * 60)

    try:
        # 获取所有余额
        balances = checker.get_all_balances(test_address)

        print(f"💰 BNB:  {balances['BNB']:.6f}")
        print(f"💵 USDT: {balances['USDT']:.2f}")
        print(f"💵 USDC: {balances['USDC']:.2f}")
        print()
        print("✅ 测试成功！")

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")

if __name__ == "__main__":
    test_token_balances()
