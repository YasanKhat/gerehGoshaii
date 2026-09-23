# راه حل کامل - گره گشایی

## مشکل شما

شما فایل `resource.rar` را دارید که شامل پک‌های Bedrock است و با ابزار
https://github.com/iteplenky/bedrock-pack-tools
سعی کردید باز کنید اما خطای `invalid argument` گرفتید.

## تحلیل ما

### 1. استخراج RAR

فایل `resource.rar` از نوع RAR5 است. ابزارهای Python معمولی (rarfile) بدون `unrar` نمی‌توانند فایل‌های فشرده (compress_type 51) را باز کنند و به جای آن فایل‌های صفر می‌سازند.

ما `unrar` را از سورس کامپایل کردیم:
```bash
git clone https://github.com/pmachapman/unrar.git
cd unrar
make
./unrar x resource.rar ./extracted_proper/
```

نتیجه: 11 پک در `./extracted_proper/`:
- 9 پک رمز شده (با contents.json دارای magic FC B9 CF 9B)
- 1 پک سالم و رمز نشده (WUAM6g== - Backblings)
- 1 پک خراب (Bx1RGQ== - همه فایل‌ها صفر)

### 2. نوع رمزنگاری

- AES-256-CFB8
- کلید اصلی: 32 کاراکتر alphanumeric
- IV: 16 بایت اول کلید
- هدر contents.json: 256 بایت (version + magic FCB9CF9B + $ + UUID)
- هر فایل کلید جداگانه 32 کاراکتری دارد

### 3. علت invalid argument

**دلیل اصلی**: طول کلید اشتباه

در Go:
```go
if len(packKey) != 32 {
    return fmt.Errorf("%w: got %d characters", errPackBadKeyLen, len(packKey))
}
```

اگر کلید شما مثلا 8 کاراکتر باشد، این خطا می‌دهد. در ویندوز گاهی به صورت `invalid argument` نمایش داده می‌شود.

**دلیل دوم**: کلید اشتباه باعث رمزگشایی خراب contents.json می‌شود که شامل مسیرهای نامعتبر با null byte یا کاراکترهای <>:"|?* است. وقتی Go سعی می‌کند `os.MkdirAll` کند، سیستم عامل `invalid argument` می‌دهد.

**دلیل سوم**: دادن فایل RAR به جای پوشه

### 4. رفع

ما `decrypt_tool.py` را نوشتیم که:

1. طول کلید را با پیام فارسی واضح چک می‌کند
2. مسیرها را از نظر null byte, کاراکتر نامعتبر, zip-slip, نام رزرو شده ویندوز بررسی می‌کند
3. به جای کرش، هشدار می‌دهد و ادامه می‌دهد
4. پک‌های رمز نشده را بدون نیاز به کلید کپی می‌کند

## استفاده

### تحلیل

```bash
python decrypt_tool.py analyze ./extracted_proper
```

### رمزگشایی (اگر کلید دارید)

```bash
python decrypt_tool.py decrypt ./extracted_proper/IPj3XA== YOUR32CHARKEY ./decrypted/IPj3XA==
```

### رمزگشایی همه با keys.json

```bash
# اول کلیدها را از سرور بگیرید
bedrock-pack-tools keys play.apexgaming.ir:19132
# یا
bedrock-pack-tools download --decrypt play.apexgaming.ir:19132

# بعد
python decrypt_tool.py decrypt-all keys.json ./extracted_proper ./decrypted
```

## چگونه کلیدها را از سرور ApexMine بگیریم؟

سرور شما احتمالا ApexMine است:
- `play.apexgaming.ir:19132`
- `5.57.32.77:19132`

مراحل:

1. دانلود bedrock-pack-tools از https://github.com/iteplenky/bedrock-pack-tools/releases
2. `bedrock-pack-tools login` - با اکانت مایکروسافت لاگین کنید
3. `bedrock-pack-tools download --decrypt play.apexgaming.ir:19132`
4. خروجی شامل `keys.json` و پوشه `decrypted/` است

اگر باز هم invalid argument گرفتید:
- از ابزار Python ما استفاده کنید
- لاگ کامل را بفرستید
- مطمئن شوید کلید 32 کاراکتر است

## فایل‌های این ریپو

- `resource.rar`: اصلی
- `unrar_binary`: ابزار استخراج RAR (کامپایل شده)
- `extracted_proper/`: استخراج درست
- `decrypt_tool.py`: ابزار رفع شده
- `analysis_report.json`: گزارش تحلیل
- `README_FA.md`: توضیح کامل فارسی
- `fix_invalid_argument.md`: توضیح دقیق رفع خطا
- `SOLUTION.md`: این فایل

## نتیجه

- خطای شما به خاطر طول کلید اشتباه یا کلید اشتباه است
- با ابزار Python ما پیام واضح می‌گیرید
- برای باز کردن 9 پک رمز شده، باید کلیدها را از سرور بگیرید
- پک WUAM6g== همین الان قابل استفاده است
- پک Bx1RGQ== خراب است

## تست

```bash
# باید بگوید طول کلید اشتباه است (نه invalid argument)
python decrypt_tool.py decrypt ./extracted_proper/IPj3XA== short

# باید بگوید wrong key
python decrypt_tool.py decrypt ./extracted_proper/IPj3XA== ABCDEFGHIJKLMNOPQRSTUVWXYZ123456 /tmp/out

# باید کپی کند (چون رمز نشده)
python decrypt_tool.py decrypt ./extracted_proper/WUAM6g== any /tmp/out2
```

---
ساخته شده برای YasanKhat - 2026-09-23
