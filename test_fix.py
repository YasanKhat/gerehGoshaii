#!/usr/bin/env python3
# تست رفع خطای invalid argument
import os, sys, json
print("=== تست 1: کلید کوتاه (باید پیام واضح بدهد نه invalid argument) ===")
os.system("python3 decrypt_tool.py decrypt ./extracted_proper/IPj3XA== short 2>&1 | tail -n 20")

print("\n=== تست 2: کلید 32 کاراکتری اشتباه (باید بگوید wrong key) ===")
os.system("python3 decrypt_tool.py decrypt ./extracted_proper/IPj3XA== ABCDEFGHIJKLMNOPQRSTUVWXYZ123456 /tmp/test_out 2>&1 | tail -n 20")

print("\n=== تست 3: پک رمز نشده (باید کپی کند) ===")
os.system("rm -rf /tmp/test_unencrypted && python3 decrypt_tool.py decrypt ./extracted_proper/WUAM6g== dummykeydummykeydummykey12 /tmp/test_unencrypted 2>&1 | tail -n 20")
os.system("ls /tmp/test_unencrypted/ | head -20")

print("\n=== تست 4: تحلیل همه پک‌ها ===")
os.system("python3 decrypt_tool.py analyze ./extracted_proper 2>&1 | tail -n 40")
