
import os

files_to_check = [
    r"sample_data/02_内部環境データ/月次推移表.csv",
    r"sample_data/02_内部環境データ/借入金返済予定表.csv"
]

for fpath in files_to_check:
    full_path = os.path.join(r"c:\Users\watar\OneDrive\デスクトップ\Consulting OS", fpath)
    if os.path.exists(full_path):
        with open(full_path, "rb") as f:
            head = f.read(3)
            print(f"File: {os.path.basename(fpath)}")
            print(f"  Head bytes: {head}")
            if head == b'\xef\xbb\xbf':
                print(f"  Result: BOM FOUND (utf-8-sig)")
            else:
                print(f"  Result: NO BOM (likely utf-8 or other)")
    else:
        print(f"File not found: {fpath}")
