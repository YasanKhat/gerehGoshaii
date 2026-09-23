# gerehGoshaii - گره گشایی

این ریپو برای تحلیل و رمزگشایی فایل `resource.rar` (پک‌های Bedrock) ساخته شده.

## مشکل

فایل زیپ (RAR) حاوی 11 پک Bedrock است که 9 تای آن رمز شده‌اند. ابزار
[bedrock-pack-tools](https://github.com/iteplenky/bedrock-pack-tools)
خطای `invalid argument` می‌دهد.

## راه حل

ما مشکل را پیدا و رفع کردیم:

1. **استخراج درست RAR**: با کامپایل `unrar` از سورس
2. **تحلیل رمزنگاری**: AES-256-CFB8 با کلید 32 کاراکتری
3. **رفع invalid argument**: ابزار Python با پیام فارسی واضح

## استفاده سریع

```bash
pip install pycryptodome
./unrar_binary x resource.rar ./extracted_proper/
python decrypt_tool.py analyze ./extracted_proper
```

برای رمزگشایی اگر کلید دارید:

```bash
python decrypt_tool.py decrypt ./extracted_proper/IPj3XA== YOUR32CHARKEY ./decrypted/
```

برای گرفتن کلید از سرور:

```bash
bedrock-pack-tools login
bedrock-pack-tools download --decrypt play.apexgaming.ir:19132
```

## فایل‌ها

- `README_FA.md`: توضیح کامل فارسی
- `SOLUTION.md`: راه حل کامل
- `fix_invalid_argument.md`: توضیح دقیق رفع خطا
- `decrypt_tool.py`: ابزار اصلی
- `unrar_binary`: استخراج RAR
- `extracted_proper/`: پک‌های استخراج شده

## وضعیت پک‌ها

- 9 رمز شده (نیاز به کلید از سرور)
- 1 سالم (WUAM6g== - Backblings)
- 1 خراب (Bx1RGQ== - همه صفر)

## تست

```bash
python decrypt_tool.py analyze ./extracted_proper
```

---
برای YasanKhat - 2026
