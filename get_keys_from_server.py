#!/usr/bin/env python3
"""
این اسکریپت سعی می‌کند کلیدها را از سرور بگیرد
نیاز به Xbox Live auth دارد - برای سادگی فقط راهنما می‌دهد
برای پیاده‌سازی کامل باید از کتابخانه‌های Bedrock Protocol استفاده کرد
"""

print("""
برای گرفتن کلید از سرور ApexMine:

روش 1 - با ابزار اصلی Go (ساده‌ترین):
----------------------------------------
1. از https://github.com/iteplenky/bedrock-pack-tools/releases آخرین نسخه را دانلود کنید
2. در ویندوز: فایل zip را باز کنید
3. در PowerShell:
   .\\bedrock-pack-tools.exe login
   # یک لینک و کد نشان می‌دهد، در مرورگر وارد شوید

4. بعد:
   .\\bedrock-pack-tools.exe download --decrypt play.apexgaming.ir:19132
   یا
   .\\bedrock-pack-tools.exe download --decrypt 5.57.32.77:19132

5. خروجی در پوشه play.apexgaming.ir/ خواهد بود:
   - packs/ : پک‌های اصلی
   - decrypted/ : پک‌های رمزگشایی شده
   - keys.json : کلیدها

روش 2 - فقط کلیدها:
-------------------
   .\\bedrock-pack-tools.exe keys play.apexgaming.ir:19132
   # خروجی keys.json

بعد با ابزار ما:
   python decrypt_tool.py decrypt-all keys.json ./extracted_proper ./decrypted

اگر خطای invalid argument گرفتید:
------------------------------------
- مطمئن شوید کلید دقیقا 32 کاراکتر است
- از ابزار Python ما استفاده کنید که پیام واضح می‌دهد
- لاگ کامل را بفرستید

""")
