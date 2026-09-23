# گره گشایی - تحلیل و رمزگشایی پک‌های Bedrock

## خلاصه

فایل `resource.rar` شامل 11 پک منابع (Resource Pack) ماینکرفت Bedrock است که از کش بازی استخراج شده‌اند:

- **مسیر اصلی**: `C:/Users/pasargad/AppData/Local/Temp/opticraft21/packcache/resource/` (از روی `upgrade_report.log`)
- **سرور احتمالی**: ApexMine - `play.apexgaming.ir:19132` یا `5.57.32.77:19132` (سرور ایرانی)

### وضعیت پک‌ها

| نام پوشه | نام واقعی | UUID | وضعیت |
|----------|-----------|------|--------|
| `Bx1RGQ==` | نامشخص | نامشخص | **خراب - همه فایل‌ها صفر** |
| `IPj3XA==` | Guns | f5e139e6-62cf-4c46-ae37-c295a7296f36 | رمز شده |
| `MDUVrw==` | HiveUI | 9b4f2c1e-7d6a-4a83-b5e1-2f8c6d0a9e47 | رمز شده |
| `WRqMFA==` | SkyBlockItems | 332b3547-92b0-431b-924a-ba0be3574660 | رمز شده |
| `WUAM6g==` | CloudyGames Backblings | 288f3563-c40d-4879-8ce7-4cb067985854 | **رمز نشده - قابل استفاده** |
| `f9fjhw==` | AdvancedItems | 3f2d9c8a-7b6a-4e5e-9f3a-1c6d2a8e4b91 | رمز شده |
| `l6cvYQ==` | Bedwars Generators | cf449055-ebaf-48b1-8e94-a64ac814a14a | رمز شده |
| `lYvyDA==` | ApexMine Textures | 4d9a7c2e-1b6f-4e83-9a5d-8c0f2e6b1a47 | رمز شده |
| `qnJIVA==` | Lobby | 00267c6d-01d3-44af-8d09-899a4efed1f7 | رمز شده |
| `skUvkw==` | DefaultUI | 1c7e5b4a-9d2f-4f83-a6e1-0b8d3c2a5f94 | رمز شده |
| `xp5EaQ==` | Entities | 3f7a9e2c-6c4b-4e8f-9a2a-1c9b8a7d5e41 | رمز شده |

**نتیجه**: 9 پک رمز شده، 1 پک سالم، 1 پک خراب.

## نوع رمزنگاری

ماینکرفت Bedrock از **AES-256-CFB8** استفاده می‌کند:

- **کلید اصلی (Master Key)**: 32 کاراکتر، شامل حروف انگلیسی (کوچک/بزرگ) و اعداد (62 حالت)
- **IV**: 16 بایت اول کلید اصلی
- **هدر contents.json**: 256 بایت
  - 4 بایت نسخه (0)
  - 4 بایت magic: `FC B9 CF 9B`
  - 8 بایت padding
  - 1 بایت `$` (0x24)
  - 36 بایت UUID پک
  - 203 بایت صفر
- **محتوا**: بعد از 256 بایت، JSON رمز شده با کلید اصلی
- **فایل‌ها**: هر فایل کلید 32 کاراکتری جداگانه دارد که در contents.json ذخیره شده

این همان چیزی است که ابزار [bedrock-pack-tools](https://github.com/iteplenky/bedrock-pack-tools) پیاده‌سازی کرده.

## خطای invalid argument

شما گفتید ابزار را دانلود کردید و کار می‌کند اما خطای `invalid argument` می‌دهد. این خطا 3 دلیل اصلی دارد:

### 1. طول کلید اشتباه (شایع‌ترین)

```go
// در Go:
if len(packKey) != 32 {
    return nil, fmt.Errorf("%w: got %d characters", errPackBadKeyLen, len(packKey))
}
```

اگر کلید را کمتر یا بیشتر از 32 کاراکتر وارد کنید، این خطا رخ می‌دهد. در ویندوز گاهی به صورت `invalid argument` نمایش داده می‌شود.

**راه حل**: کلید باید **دقیقا 32 کاراکتر** و فقط شامل `a-zA-Z0-9` باشد.

```bash
# اشتباه
bedrock-pack-tools decrypt ./IPj3XA== shortkey
# درست
bedrock-pack-tools decrypt ./IPj3XA== ABCDEFGHIJKLMNOPQRSTUVWXYZ123456 ./out
```

### 2. مسیر فایل نامعتبر (به خاطر کلید اشتباه)

اگر کلید اشتباه باشد، `contents.json` به صورت متن نامفهوم رمزگشایی می‌شود که شامل مسیرهای خراب با کاراکترهای نامعتبر (مثل null byte `\x00` یا `<>:"|?*`) است. وقتی ابزار سعی می‌کند فایلی با این نام بسازد، سیستم عامل خطای `invalid argument` می‌دهد.

**راه حل در ابزار ما**: ما این مسیرها را قبل از ساخت فایل بررسی می‌کنیم و رد می‌کنیم:

```python
if '\x00' in entry_path:
    raise ValueError(f"invalid path contains null byte")
if any(c in entry_path for c in '<>:"|?*'):
    raise ValueError(f"path contains invalid characters")
# جلوگیری از خروج از پوشه (zip-slip)
if not dst_path.startswith(clean_base):
    raise ValueError(f"path escapes base dir")
```

### 3. دادن فایل به جای پوشه

اگر به جای پوشه پک، فایل `resource.rar` را به ابزار بدهید:

```bash
bedrock-pack-tools decrypt resource.rar mykey
```

ابزار سعی می‌کند `resource.rar/contents.json` را بخواند که نامعتبر است.

**راه حل**: اول RAR را استخراج کنید، بعد پوشه را بدهید:

```bash
unrar x resource.rar ./packs/
bedrock-pack-tools decrypt ./packs/IPj3XA== YOURKEY
```

## ابزار رفع شده (Python)

ما یک ابزار Python نوشتیم که مشکل `invalid argument` را برطرف می‌کند:

### نصب

```bash
pip install pycryptodome
```

### تحلیل پک‌ها

```bash
python decrypt_tool.py analyze ./extracted_proper
```

### رمزگشایی یک پک (اگر کلید را دارید)

```bash
python decrypt_tool.py decrypt ./extracted_proper/IPj3XA== YOUR32CHARKEYHERE1234567890ABC ./decrypted/IPj3XA==
```

### رمزگشایی همه با keys.json

اگر از سرور کلیدها را گرفته‌اید (`keys.json`):

```bash
python decrypt_tool.py decrypt-all keys.json ./extracted_proper ./decrypted
```

### ویژگی‌های رفع شده

1. بررسی دقیق طول کلید (32) با پیام فارسی واضح
2. جلوگیری از مسیرهای نامعتبر و null byte
3. جلوگیری از zip-slip (خروج از پوشه)
4. جلوگیری از نام‌های رزرو شده ویندوز (CON, PRN, ...)
5. مدیریت خطای کلید اشتباه بدون کرش
6. پشتیبانی از پک‌های رمز نشده (مثل WUAM6g==)

## چگونه کلیدها را به دست آوریم؟

بدون کلید، رمزگشایی **غیرممکن** است (AES-256 امن است). باید کلید را از سرور بگیرید:

### روش 1: با bedrock-pack-tools (پیشنهادی)

```bash
# دانلود ابزار
# از https://github.com/iteplenky/bedrock-pack-tools/releases

# لاگین با اکانت مایکروسافت (یک بار)
bedrock-pack-tools login
# یک کد نشان می‌دهد، آن را در مرورگر وارد کنید

# دانلود و رمزگشایی مستقیم از سرور ApexMine
bedrock-pack-tools download --decrypt play.apexgaming.ir:19132
# یا
bedrock-pack-tools download --decrypt 5.57.32.77:19132

# خروجی: پوشه‌ای با پک‌های رمزگشایی شده و keys.json
```

### روش 2: فقط کلیدها

```bash
bedrock-pack-tools keys play.apexgaming.ir:19132
# خروجی: keys.json
```

بعد با ابزار ما:

```bash
python decrypt_tool.py decrypt-all keys.json ./extracted_proper ./decrypted
```

### روش 3: اگر به سرور دسترسی ندارید

متأسفانه بدون دسترسی به سرور یا داشتن keys.json، نمی‌توان پک‌ها را باز کرد. این به خاطر امنیت AES-256 است.

## استخراج RAR

فایل `resource.rar` از نوع RAR5 است و با ابزارهای معمولی Python باز نمی‌شود. ما `unrar` را از سورس کامپایل کردیم:

```bash
./unrar_binary x resource.rar ./extracted_proper/
```

یا با Python:

```python
import subprocess
subprocess.run(["./unrar_binary", "x", "resource.rar", "./extracted_proper/"])
```

## فایل‌های موجود در این ریپو

- `resource.rar`: فایل اصلی
- `unrar_binary`: ابزار استخراج RAR (کامپایل شده از https://github.com/pmachapman/unrar)
- `extracted_proper/`: پک‌های استخراج شده به درستی
- `decrypt_tool.py`: ابزار رمزگشایی رفع شده
- `analysis_report.json`: گزارش تحلیل پک‌ها
- `README_FA.md`: این فایل

## تست

```bash
# تحلیل
python decrypt_tool.py analyze ./extracted_proper

# تست خطای طول کلید (باید پیام واضح بدهد)
python decrypt_tool.py decrypt ./extracted_proper/IPj3XA== shortkey

# تست کلید اشتباه (باید بگوید wrong key نه invalid argument)
python decrypt_tool.py decrypt ./extracted_proper/IPj3XA== ABCDEFGHIJKLMNOPQRSTUVWXYZ123456 /tmp/out
```

## نتیجه‌گیری

- خطای `invalid argument` شما به خاطر **طول کلید اشتباه** یا **کلید اشتباه که باعث مسیر نامعتبر می‌شود** است.
- ابزار Python ما این را با پیام فارسی واضح و مدیریت خطا برطرف می‌کند.
- برای رمزگشایی واقعی، باید کلیدها را از سرور ApexMine بگیرید.
- پک `WUAM6g==` (Backblings) همین الان قابل استفاده است چون رمز نشده.
- پک `Bx1RGQ==` خراب است (همه صفر) و قابل بازیابی نیست.

## تماس

اگر کلیدها را از سرور گرفتید و باز هم مشکل داشتید، فایل `keys.json` و لاگ خطا را بفرستید تا بررسی کنیم.

---
ساخته شده برای حل مشکل YasanKhat - گره گشایی
