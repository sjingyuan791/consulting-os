
import os
import pandas as pd
import glob

BASE_DIR = r"c:\Users\watar\OneDrive\デスクトップ\Consulting OS\sample_data"

def fix_encoding_recursive():
    print(f"Scanning {BASE_DIR} for CSV files...")
    csv_files = glob.glob(os.path.join(BASE_DIR, "**/*.csv"), recursive=True)
    
    count = 0
    for fpath in csv_files:
        print(f"Checking: {os.path.basename(fpath)}")
        
        # 1. Read with various encodings
        df = None
        detected_enc = None
        
        encodings_to_try = ["utf-8-sig", "utf-8", "cp932", "shift_jis", "euc-jp"]
        
        for enc in encodings_to_try:
            try:
                df = pd.read_csv(fpath, encoding=enc)
                # Heuristic check: if japanese chars decode correctly
                # We can't easily check validity without language detection, 
                # but if it reads without error, it's a candidate.
                # However, Shift-JIS bytes read as UTF-8 might fail, 
                # but UTF-8 bytes read as Shift-JIS often SUCCEED but produce garbage.
                
                # If we read as Shift-JIS and it was actually UTF-8, we get garbage.
                # If we read as UTF-8 and it was actually Shift-JIS, we usually get UnicodeDecodeError.
                
                # Strategy: Prioritize UTF-8. 
                # If it's valid UTF-8, assume it is UTF-8 (unless it's extremely short coincidental bytes).
                # Almost all modern text is UTF-8.
                detected_enc = enc
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                print(f"  Error reading as {enc}: {e}")
                
        if df is not None:
             try:
                # 2. Write back as utf-8-sig
                df.to_csv(fpath, index=False, encoding="utf-8-sig")
                print(f"  [FIXED] Saved as utf-8-sig (detected: {detected_enc})")
                count += 1
             except Exception as e:
                 print(f"  Error writing {fpath}: {e}")
        else:
            print(f"  [FAIL] Could not decode file with standard encodings.")

    print(f"Total files processed: {count}")

if __name__ == "__main__":
    fix_encoding_recursive()
