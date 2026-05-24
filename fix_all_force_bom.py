
import os
import glob
import time

BASE_DIR = r"c:\Users\watar\OneDrive\デスクトップ\Consulting OS\sample_data\02_内部環境データ"

def fix_all_force_bom():
    print(f"Scanning {BASE_DIR}...")
    csv_files = glob.glob(os.path.join(BASE_DIR, "*.csv"))
    
    locked_files = []
    fixed_files = []
    skipped_files = []
    
    for fpath in csv_files:
        dbname = os.path.basename(fpath)
        try:
            # Read
            with open(fpath, "rb") as f:
                content = f.read()
            
            if content.startswith(b'\xef\xbb\xbf'):
                print(f"[SKIP] Already has BOM: {dbname}")
                skipped_files.append(dbname)
                continue
            
            # Write
            try:
                with open(fpath, "wb") as f:
                    f.write(b'\xef\xbb\xbf' + content)
                print(f"[FIXED] Added BOM: {dbname}")
                fixed_files.append(dbname)
            except PermissionError:
                print(f"[LOCKED] Permission denied: {dbname}")
                locked_files.append(dbname)
                
        except Exception as e:
            print(f"[ERROR] {dbname}: {e}")
            
    print("-" * 30)
    print(f"Total Found: {len(csv_files)}")
    print(f"Fixed: {len(fixed_files)}")
    print(f"Skipped: {len(skipped_files)}")
    print(f"Locked: {len(locked_files)}")
    
    if locked_files:
        print("\n!!! LOCKED FILES (Please close Excel) !!!")
        for f in locked_files:
            print(f"- {f}")
            
if __name__ == "__main__":
    fix_all_force_bom()
