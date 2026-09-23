#!/usr/bin/env python3
print("="*60)
print("گره گشایی - نمایش رفع خطای invalid argument")
print("="*60)

print("\n1. تحلیل پک‌ها:")
print("-"*60)
import os, json, subprocess
result = subprocess.run(["python3", "decrypt_tool.py", "analyze", "./extracted_proper"], capture_output=True, text=True)
print(result.stdout[:2000])

print("\n2. تست خطای طول کلید (این همان invalid argument شماست):")
print("-"*60)
result = subprocess.run(["python3", "decrypt_tool.py", "decrypt", "./extracted_proper/IPj3XA==", "short"], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)

print("\n3. تست پک رمز نشده (باید کار کند):")
print("-"*60)
import shutil
if os.path.exists("/tmp/demo_out"):
    shutil.rmtree("/tmp/demo_out")
result = subprocess.run(["python3", "decrypt_tool.py", "decrypt", "./extracted_proper/WUAM6g==", "anykey", "/tmp/demo_out"], capture_output=True, text=True)
print(result.stdout)
print(f"فایل‌های خروجی: {os.listdir('/tmp/demo_out')[:5]}")

print("\n4. خلاصه:")
print("-"*60)
print("""
✓ ابزار Python ما خطای invalid argument را با پیام فارسی واضح جایگزین کرد
✓ علت اصلی: طول کلید باید 32 باشد
✓ علت دوم: کلید اشتباه باعث مسیر نامعتبر می‌شود
✓ راه حل: از decrypt_tool.py استفاده کنید
✓ برای 9 پک رمز شده باید کلید از سرور بگیرید:
  bedrock-pack-tools download --decrypt play.apexgaming.ir:19132

پک WUAM6g== (Backblings) همین الان قابل استفاده است!
پک Bx1RGQ== خراب است (همه صفر)
""")

