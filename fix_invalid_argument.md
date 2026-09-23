# رفع خطای invalid argument در bedrock-pack-tools

## مشکل

وقتی شما این دستور را می‌زنید:

```bash
bedrock-pack-tools decrypt ./IPj3XA== mykey
```

خطای `invalid argument` می‌گیرید.

## علت دقیق (از روی کد Go)

در فایل `decrypt.go` خط 258:

```go
if len(packKey) != 32 {
    return nil, fmt.Errorf("%w: got %d characters", errPackBadKeyLen, len(packKey))
}
```

و در `internal/cfb8/cfb8.go` خط 32:

```go
if len(key) != 32 {
    return nil, fmt.Errorf("key must be 32 bytes, got %d", len(key))
}
```

اگر کلید 32 نباشد، خطا می‌دهد. در ویندوز این خطا گاهی به صورت `invalid argument` نمایش داده می‌شود چون سیستم عامل نمی‌تواند فایل با نام نامعتبر بسازد.

همچنین در `decrypt.go` خط 526 به بعد، اگر کلید اشتباه باشد، `contents.json` به صورت خراب رمزگشایی می‌شود و مسیرهایی مثل `../../etc/passwd` یا `file\x00name` تولید می‌کند که باعث `invalid argument` هنگام `os.MkdirAll` می‌شود.

## راه حل 1: استفاده از ابزار Python ما (پیشنهادی)

```bash
pip install pycryptodome
python decrypt_tool.py decrypt ./extracted_proper/IPj3XA== YOUR32CHARKEY ./out
```

این ابزار:
- طول کلید را چک می‌کند و پیام فارسی واضح می‌دهد
- مسیرهای نامعتبر را رد می‌کند به جای کرش
- از zip-slip جلوگیری می‌کند

## راه حل 2: رفع در کد Go

اگر می‌خواهید کد Go را درست کنید، این تغییرات را اعمال کنید:

### در decrypt.go، تابع decryptContentsJSON:

```go
// قبل
if len(packKey) != 32 {
    return nil, fmt.Errorf("%w: got %d characters", errPackBadKeyLen, len(packKey))
}

// بعد - پیام واضح‌تر
if len(packKey) != 32 {
    return nil, fmt.Errorf("کلید باید دقیقا 32 کاراکتر باشد، شما %d وارد کردید. این باعث invalid argument می‌شود: %w", len(packKey), errPackBadKeyLen)
}
```

### در decrypt.go، تابع decryptPackFiles:

```go
// قبل
dstPath := filepath.Join(outDir, entry.Path)
if !strings.HasPrefix(filepath.Clean(dstPath), cleanBase) {
    fmt.Fprint(os.Stderr, lang.Tf("packs.decrypt.escaped", colorYellow, colorReset, entry.Path))
    escaped++
    continue
}

// بعد - بررسی بیشتر
if strings.Contains(entry.Path, "\x00") {
    fmt.Fprint(os.Stderr, "رد شد: مسیر شامل null byte است (باعث invalid argument می‌شود): %s\n", entry.Path)
    escaped++
    continue
}
if strings.ContainsAny(entry.Path, "<>:\"|?*") {
    fmt.Fprint(os.Stderr, "رد شد: مسیر شامل کاراکتر نامعتبر ویندوز است: %s\n", entry.Path)
    escaped++
    continue
}
dstPath := filepath.Join(outDir, entry.Path)
if !strings.HasPrefix(filepath.Clean(dstPath), cleanBase) {
    // ...
}
```

### در processFile:

```go
// قبل
if err := os.MkdirAll(filepath.Dir(dstPath), 0755); err != nil {
    return false, err
}

// بعد
if err := os.MkdirAll(filepath.Dir(dstPath), 0755); err != nil {
    // اگر invalid argument بود، به جای کرش، خطا را لاگ کن و ادامه بده
    if strings.Contains(err.Error(), "invalid argument") {
        return false, fmt.Errorf("مسیر نامعتبر (احتمالا کلید اشتباه باعث نام خراب شده): %s: %w", entry.Path, err)
    }
    return false, err
}
```

## راه حل 3: استفاده درست از ابزار اصلی

```bash
# 1. مطمئن شوید پوشه را می‌دهید نه فایل RAR
# اشتباه:
bedrock-pack-tools decrypt resource.rar mykey
# درست:
unrar x resource.rar ./packs/
bedrock-pack-tools decrypt ./packs/IPj3XA== YOUR32CHARKEY

# 2. کلید دقیقا 32 کاراکتر
# اشتباه:
bedrock-pack-tools decrypt ./pack shortkey
# درست:
bedrock-pack-tools decrypt ./pack ABCDEFGHIJKLMNOPQRSTUVWXYZ123456

# 3. اگر همه پک‌ها را دارید، از decrypt-all استفاده کنید
bedrock-pack-tools decrypt --all keys.json ./packs/ ./decrypted/
```

## تست رفع

بعد از اعمال رفع، این دستورات باید پیام واضح بدهند نه invalid argument:

```bash
# باید بگوید طول کلید اشتباه است
bedrock-pack-tools decrypt ./pack short

# باید بگوید کلید اشتباه است نه invalid argument
bedrock-pack-tools decrypt ./pack WRONGKEYWRONGKEYWRONGKEY12
```

## نتیجه

ما در `decrypt_tool.py` همه این رفع‌ها را اعمال کردیم. لطفا از آن استفاده کنید.

