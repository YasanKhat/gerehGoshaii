#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
گره گشایی - ابزار رمزگشایی پک‌های Bedrock
این ابزار مشکل invalid argument در bedrock-pack-tools را برطرف می‌کند

بر اساس کد Go از https://github.com/iteplenky/bedrock-pack-tools
پیاده‌سازی AES-256-CFB8 با IV = 16 بایت اول کلید

نویسنده: برای حل مشکل کاربر YasanKhat
"""

import os
import sys
import json
import base64
import pathlib
import argparse
from typing import List, Dict, Tuple

try:
    from Crypto.Cipher import AES
except ImportError:
    print("خطا: کتابخانه pycryptodome نصب نیست")
    print("نصب: pip install pycryptodome")
    sys.exit(1)

# --- ثابت‌ها ---
CONTENTS_HEADER_SIZE = 256
CONTENTS_MAGIC = bytes([0xFC, 0xB9, 0xCF, 0x9B])
CONTENTS_JSON = "contents.json"
MANIFEST_JSON = "manifest.json"
PACK_ICON = "pack_icon.png"

# --- توابع رمزنگاری (همانند Go internal/cfb8) ---
def cfb8_decrypt(data: bytes, key: bytes) -> bytes:
    """
    AES-256-CFB8 decryption
    key باید دقیقا 32 بایت باشد
    IV = 16 بایت اول کلید
    """
    if len(key) != 32:
        raise ValueError(f"key must be 32 bytes, got {len(key)}")
    iv = key[:16]
    cipher = AES.new(key, AES.MODE_ECB)
    prev = bytearray(iv)
    out = bytearray(len(data))
    for i in range(len(data)):
        enc = cipher.encrypt(bytes(prev))
        out[i] = data[i] ^ enc[0]
        # در حالت decrypt، بایت ورودی (ciphertext) وارد feedback می‌شود
        prev = prev[1:] + bytes([data[i]])
    return bytes(out)

def cfb8_encrypt(data: bytes, key: bytes) -> bytes:
    if len(key) != 32:
        raise ValueError(f"key must be 32 bytes, got {len(key)}")
    iv = key[:16]
    cipher = AES.new(key, AES.MODE_ECB)
    prev = bytearray(iv)
    out = bytearray(len(data))
    for i in range(len(data)):
        enc = cipher.encrypt(bytes(prev))
        out[i] = data[i] ^ enc[0]
        prev = prev[1:] + bytes([out[i]])
    return bytes(out)

def decrypt_contents_json(data: bytes, pack_key: str) -> Dict:
    """
    رمزگشایی contents.json
    فرمت: 256 بایت هدر + بقیه رمز شده با کلید اصلی
    هدر: [version:4][magic:4][padding:8][0x24:1][uuid:36][zeros:203]
    """
    if len(pack_key) != 32:
        raise ValueError(f"pack: key length must be 32 - got {len(pack_key)} characters (این همان خطای invalid argument شماست!)")

    if len(data) < CONTENTS_HEADER_SIZE:
        raise ValueError(f"pack: contents.json truncated - {len(data)} bytes")

    # بررسی هدر
    header = data[:CONTENTS_HEADER_SIZE]
    if header[4:8] != CONTENTS_MAGIC:
        # اگر همه صفر باشد، فایل خراب است (مثل Bx1RGQ==)
        if all(b == 0 for b in header):
            raise ValueError(f"pack: contents.json is all zeros - file corrupted (پک Bx1RGQ== خراب است)")
        # اگر magic نباشد، شاید فایل رمز نیست؟
        print(f"هشدار: magic نادرست {header[4:8].hex()} - شاید فایل رمز نشده باشد")

    encrypted = data[CONTENTS_HEADER_SIZE:]
    try:
        plaintext = cfb8_decrypt(encrypted, pack_key.encode())
    except Exception as e:
        raise ValueError(f"pack: decryption failed (likely wrong key) - {e}")

    # حذف padding انتهایی (null, space, newline)
    plaintext = plaintext.rstrip(b"\x00 \n\r\t")

    try:
        contents = json.loads(plaintext.decode('utf-8'))
        return contents
    except Exception as e:
        preview = plaintext[:100].decode('utf-8', errors='ignore')
        raise ValueError(f'pack: decryption failed (likely wrong key) - parse failed (first 100 bytes: "{preview}"): {e}')

def sanitize_path(base_dir: str, entry_path: str) -> str:
    """
    جلوگیری از zip-slip و invalid argument
    - جلوگیری از خروج از base_dir با .. 
    - جلوگیری از کاراکترهای نامعتبر
    - جلوگیری از null byte
    """
    # جلوگیری از null byte که باعث invalid argument می‌شود
    if '\x00' in entry_path:
        raise ValueError(f"invalid path contains null byte: {entry_path!r}")

    # جلوگیری از مسیرهای مطلق
    if os.path.isabs(entry_path):
        raise ValueError(f"absolute path not allowed: {entry_path}")

    # نرمال‌سازی مسیر
    # در ویندوز، کاراکترهای <>:"|?* نامعتبر هستند
    invalid_chars = set('<>:"|?*\x00')
    if any(c in entry_path for c in invalid_chars):
        raise ValueError(f"path contains invalid characters: {entry_path}")

    # جلوگیری از .. که از پوشه خارج می‌شود
    # این همان محافظی است که در Go وجود دارد
    clean_base = os.path.abspath(base_dir) + os.sep
    dst_path = os.path.abspath(os.path.join(base_dir, entry_path))
    if not dst_path.startswith(clean_base):
        raise ValueError(f"path escapes base dir (zip-slip): {entry_path}")

    # جلوگیری از نام‌های رزرو شده ویندوز
    reserved = {"CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
                "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9"}
    parts = entry_path.split('/')
    for part in parts:
        name_without_ext = os.path.splitext(part)[0].upper()
        if name_without_ext in reserved:
            raise ValueError(f"reserved Windows name: {entry_path}")

    return dst_path

def decrypt_pack(pack_dir: str, pack_key: str, out_dir: str) -> Dict[str, int]:
    """
    رمزگشایی یک پک
    این تابع مشکل invalid argument را برطرف می‌کند
    """
    print(f"\n=== رمزگشایی پک: {pack_dir} ===")
    print(f"کلید: {pack_key}")
    print(f"خروجی: {out_dir}")

    contents_path = os.path.join(pack_dir, CONTENTS_JSON)
    if not os.path.exists(contents_path):
        # شاید پک رمز نشده باشد (مثل WUAM6g==)
        manifest_path = os.path.join(pack_dir, MANIFEST_JSON)
        if os.path.exists(manifest_path):
            print(f"هشدار: {CONTENTS_JSON} وجود ندارد - شاید پک رمز نشده باشد (مثل WUAM6g==)")
            # کپی ساده - برای پک رمز نشده کلید لازم نیست
            os.makedirs(out_dir, exist_ok=True)
            import shutil
            shutil.copytree(pack_dir, out_dir, dirs_exist_ok=True)
            return {"decrypted": 0, "copied": 1, "errors": 0, "note": "unencrypted pack copied"}
        else:
            raise FileNotFoundError(f"no contents.json at {contents_path} - این پوشه پک نیست")

    # حالا که می‌دانیم contents.json وجود دارد، کلید باید 32 باشد
    if len(pack_key) != 32:
        print(f"خطا: طول کلید باید 32 باشد، الان {len(pack_key)} است")
        print("این همان خطای invalid argument شماست!")
        print("راه حل: کلید را دقیقا 32 کاراکتر وارد کنید (حروف و اعداد انگلیسی)")
        raise ValueError(f"key length must be 32, got {len(pack_key)}")

    with open(contents_path, 'rb') as f:
        contents_data = f.read()

    try:
        contents = decrypt_contents_json(contents_data, pack_key)
    except Exception as e:
        print(f"خطا در رمزگشایی contents.json: {e}")
        raise

    os.makedirs(out_dir, exist_ok=True)

    # ذخیره contents.json رمزگشایی شده
    with open(os.path.join(out_dir, CONTENTS_JSON), 'w', encoding='utf-8') as f:
        json.dump(contents, f, indent=2, ensure_ascii=False)

    stats = {"decrypted": 0, "copied": 1, "errors": 0}

    # کپی manifest.json و pack_icon.png اگر وجود دارند (این‌ها رمز نمی‌شوند)
    for name in [MANIFEST_JSON, PACK_ICON]:
        src = os.path.join(pack_dir, name)
        dst = os.path.join(out_dir, name)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                import shutil
                shutil.copy2(src, dst)
            except Exception as e:
                print(f"خطا در کپی {name}: {e}")
                stats["errors"] += 1

    # رمزگشایی فایل‌ها
    entries = contents.get("content", [])
    print(f"تعداد فایل‌ها در contents.json: {len(entries)}")

    for entry in entries:
        path = entry.get("path", "")
        key = entry.get("key", "")

        if path == CONTENTS_JSON:
            continue

        try:
            dst_path = sanitize_path(out_dir, path)
        except ValueError as e:
            print(f"هشدار: مسیر نامعتبر رد شد (این باعث invalid argument می‌شد): {path} - {e}")
            stats["errors"] += 1
            continue

        src_path = os.path.join(pack_dir, path)

        # اگر پوشه باشد
        if not os.path.exists(src_path):
            # شاید مسیر فقط یک پوشه باشد (key خالی)
            if key == "":
                try:
                    os.makedirs(dst_path, exist_ok=True)
                except Exception as e:
                    print(f"خطا در ساخت پوشه {path}: {e}")
                    stats["errors"] += 1
                continue
            else:
                print(f"هشدار: فایل مبدا وجود ندارد: {path}")
                stats["errors"] += 1
                continue

        # اگر پوشه باشد
        if os.path.isdir(src_path):
            try:
                os.makedirs(dst_path, exist_ok=True)
            except Exception as e:
                print(f"خطا در ساخت پوشه {path}: {e}")
                stats["errors"] += 1
            continue

        try:
            os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        except Exception as e:
            print(f"خطا در ساخت پوشه والد برای {path}: {e} - این می‌تواند invalid argument باشد اگر مسیر نامعتبر باشد")
            stats["errors"] += 1
            continue

        try:
            with open(src_path, 'rb') as f:
                raw = f.read()

            # اگر key خالی یا manifest.json باشد، کپی ساده
            if key == "" or path == MANIFEST_JSON:
                with open(dst_path, 'wb') as out:
                    out.write(raw)
                stats["copied"] += 1
            else:
                # رمزگشایی
                if len(key) != 32:
                    print(f"هشدار: کلید فایل {path} طول نامعتبر دارد ({len(key)}) - کپی به عنوان باینری")
                    with open(dst_path, 'wb') as out:
                        out.write(raw)
                    stats["copied"] += 1
                    continue

                try:
                    dec = cfb8_decrypt(raw, key.encode())
                    with open(dst_path, 'wb') as out:
                        out.write(dec)
                    stats["decrypted"] += 1
                except Exception as e:
                    print(f"خطا در رمزگشایی {path}: {e}")
                    stats["errors"] += 1
        except Exception as e:
            print(f"خطا در پردازش {path}: {e}")
            stats["errors"] += 1

    print(f"تمام شد: {stats['decrypted']} رمزگشایی، {stats['copied']} کپی، {stats['errors']} خطا")
    return stats

def decrypt_all(keys_file: str, packs_dir: str, out_base: str):
    """
    رمزگشایی همه پک‌ها با استفاده از keys.json
    فرمت keys.json:
    {
      "uuid": {"key": "32char...", "name": "...", "version": "..."},
      ...
    }
    """
    print(f"خواندن کلیدها از {keys_file}")
    with open(keys_file, 'r', encoding='utf-8') as f:
        keys = json.load(f)

    print(f"تعداد کلیدها: {len(keys)}")
    print(f"پوشه پک‌ها: {packs_dir}")
    print(f"خروجی: {out_base}")

    os.makedirs(out_base, exist_ok=True)

    entries = os.listdir(packs_dir)
    jobs = []

    for entry_name in entries:
        pack_dir = os.path.join(packs_dir, entry_name)
        if not os.path.isdir(pack_dir):
            continue

        # خواندن UUID از manifest.json
        manifest_path = os.path.join(pack_dir, MANIFEST_JSON)
        if not os.path.exists(manifest_path):
            print(f"رد شد {entry_name}: manifest.json ندارد")
            continue

        try:
            with open(manifest_path, 'r', encoding='utf-8') as mf:
                manifest = json.load(mf)
                uuid = manifest.get('header', {}).get('uuid', '')
                if not uuid:
                    print(f"هشدار {entry_name}: UUID ندارد")
                    continue
        except Exception as e:
            print(f"هشدار {entry_name}: manifest خراب - {e}")
            continue

        key_info = keys.get(uuid)
        if not key_info:
            print(f"رد شد {entry_name} (UUID {uuid}): کلید در keys.json نیست")
            continue

        key = key_info.get('key', '') if isinstance(key_info, dict) else key_info
        if not key:
            print(f"رد شد {entry_name}: کلید خالی")
            continue

        out_dir = os.path.join(out_base, entry_name)
        jobs.append((entry_name, pack_dir, key, out_dir, uuid))

    if not jobs:
        print("هیچ پکی برای رمزگشایی پیدا نشد!")
        return

    print(f"\n{len(jobs)} پک برای رمزگشایی آماده است")

    succeeded = 0
    for name, pack_dir, key, out_dir, uuid in jobs:
        try:
            print(f"\n--- در حال رمزگشایی {name} (UUID {uuid}) ---")
            stats = decrypt_pack(pack_dir, key, out_dir)
            print(f"✓ موفق: {name} - {stats}")
            succeeded += 1
        except Exception as e:
            print(f"✗ خطا در {name}: {e}")

    print(f"\nتمام شد: {succeeded}/{len(jobs)} پک با موفقیت رمزگشایی شد")
    print(f"خروجی در: {os.path.abspath(out_base)}")

def main():
    parser = argparse.ArgumentParser(description="ابزار رمزگشایی پک‌های Bedrock - رفع خطای invalid argument")
    subparsers = parser.add_subparsers(dest='command', help='دستور')

    # decrypt single
    p1 = subparsers.add_parser('decrypt', help='رمزگشایی یک پک')
    p1.add_argument('pack_dir', help='پوشه پک (مثلا IPj3XA==)')
    p1.add_argument('key', help='کلید 32 کاراکتری')
    p1.add_argument('out_dir', nargs='?', help='پوشه خروجی (اختیاری)')

    # decrypt all
    p2 = subparsers.add_parser('decrypt-all', help='رمزگشایی همه پک‌ها با keys.json')
    p2.add_argument('keys_file', help='فایل keys.json')
    p2.add_argument('packs_dir', help='پوشه حاوی پک‌ها')
    p2.add_argument('out_dir', nargs='?', help='پوشه خروجی')

    # analyze
    p3 = subparsers.add_parser('analyze', help='تحلیل پک‌ها')
    p3.add_argument('packs_dir', help='پوشه حاوی پک‌ها')

    args = parser.parse_args()

    if args.command == 'decrypt':
        out_dir = args.out_dir
        if not out_dir:
            out_dir = args.pack_dir.rstrip('/\\') + "_decrypted"
        try:
            decrypt_pack(args.pack_dir, args.key, out_dir)
        except Exception as e:
            print(f"\nخطا: {e}")
            print("\nراهنمای رفع خطای invalid argument:")
            print("1. مطمئن شوید کلید دقیقا 32 کاراکتر است")
            print("2. کلید باید فقط شامل حروف و اعداد انگلیسی باشد")
            print("3. مسیر پک باید پوشه باشد نه فایل")
            print("4. اگر کلید اشتباه باشد، رمزگشایی شکست می‌خورد")
            sys.exit(1)

    elif args.command == 'decrypt-all':
        out_dir = args.out_dir
        if not out_dir:
            out_dir = args.packs_dir.rstrip('/\\') + "_decrypted"
        decrypt_all(args.keys_file, args.packs_dir, out_dir)

    elif args.command == 'analyze':
        base = args.packs_dir
        print(f"تحلیل پک‌ها در {base}")
        for top in sorted(os.listdir(base)):
            pack_path = os.path.join(base, top)
            if not os.path.isdir(pack_path):
                continue
            print(f"\n=== {top} ===")
            cj = os.path.join(pack_path, CONTENTS_JSON)
            mj = os.path.join(pack_path, MANIFEST_JSON)
            if os.path.exists(cj):
                size = os.path.getsize(cj)
                with open(cj, 'rb') as f:
                    data = f.read(20)
                    is_zero = all(b == 0 for b in data)
                    print(f"  contents.json: size={size}, zero={is_zero}, magic={data[4:8].hex() if len(data)>=8 else 'short'}")
            else:
                print(f"  contents.json: وجود ندارد (پک رمز نشده)")

            if os.path.exists(mj):
                size = os.path.getsize(mj)
                with open(mj, 'rb') as f:
                    d = f.read(20)
                    is_zero = all(b == 0 for b in d)
                    print(f"  manifest.json: size={size}, zero={is_zero}")
                    if not is_zero:
                        try:
                            j = json.loads(open(mj, 'r', encoding='utf-8').read())
                            print(f"    name={j.get('header',{}).get('name')}, uuid={j.get('header',{}).get('uuid')}")
                        except:
                            print(f"    parse fail")
            else:
                print(f"  manifest.json: وجود ندارد")

            # بررسی فایل‌های نمونه
            encrypted_count = 0
            total = 0
            for root, dirs, files in os.walk(pack_path):
                for file in files:
                    if file in [CONTENTS_JSON, MANIFEST_JSON, PACK_ICON]:
                        continue
                    total += 1
                    fp = os.path.join(root, file)
                    try:
                        with open(fp, 'rb') as fh:
                            header = fh.read(8)
                            if header.startswith(b'\x89PNG'):
                                pass
                            else:
                                # سعی در تشخیص JSON
                                try:
                                    txt = open(fp, 'r', encoding='utf-8').read(100)
                                    json.loads(txt)
                                except:
                                    encrypted_count += 1
                    except:
                        pass
            print(f"  فایل‌های رمز شده (تقریبی): {encrypted_count}/{total}")

    else:
        parser.print_help()
        print("\nمثال‌ها:")
        print("  python decrypt_tool.py analyze ./extracted_proper")
        print("  python decrypt_tool.py decrypt ./extracted_proper/IPj3XA== YOUR32CHARKEYHERE1234567890ABC ./decrypted/IPj3XA==")
        print("  python decrypt_tool.py decrypt-all keys.json ./extracted_proper ./decrypted")

if __name__ == "__main__":
    main()
