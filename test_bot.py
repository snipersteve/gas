#!/usr/bin/env python3
"""
简单测试BSC API功能
"""

from bsc_api import BSCBalanceChecker
from config import LOW_BALANCE_THRESHOLD

def test_api():
    """测试BSC API"""
    print("🔄 Testing BSC API...")
    
    checker = BSCBalanceChecker()
    
    # 测试地址验证
    test_address = "0xb5d85cbf7cb3ee0d56b3bb207d5fc4b82f43f511"
    invalid_address = "invalid_address"
    
    print(f"✅ Valid address test: {checker.is_valid_address(test_address)}")
    print(f"❌ Invalid address test: {checker.is_valid_address(invalid_address)}")
    
    # 测试余额查询
    try:
        balance = checker.get_bnb_balance(test_address)
        print(f"💰 Balance for {test_address[:10]}...{test_address[-8:]}: {balance:.6f} BNB")
        
        is_low, _ = checker.check_low_balance(test_address, LOW_BALANCE_THRESHOLD)
        status = "🔴 Low" if is_low else "✅ OK"
        print(f"📊 Balance status: {status} (threshold: {LOW_BALANCE_THRESHOLD} BNB)")
        
    except Exception as e:
        print(f"❌ Error querying balance: {str(e)}")

if __name__ == "__main__":
    test_api()