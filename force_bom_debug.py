
import os
import glob
import binascii

BASE_DIR = r"c:\Users\watar\OneDrive\デスクトップ\Consulting OS\sample_data"

def force_bom_debug():
    print(f"Scanning {BASE_DIR} for CSV files...")
    csv_files = glob.glob(os.path.join(BASE_DIR, "**/*.csv"), recursive=True)
    
    count = 0
    for fpath in csv_files:
        try:
            with open(fpath, "rb") as f:
                content = f.read()
            
            head = content[:3]
            hex_head = binascii.hexlify(head).decode()
            
            print(f"Checking: {os.path.basename(fpath)}")
            print(f"  Head: {hex_head}")
            
            if content.startswith(b'\xef\xbb\xbf'):
                print("  -> Has BOM. Skipping.")
            else:
                with open(fpath, "wb") as f:
                    f.write(b'\xef\xbb\xbf' + content)
                print("  -> NO BOM. [FORCED BOM]")
                count += 1
        except Exception as e:
            print(f"Error processing {os.path.basename(fpath)}: {e}")

    print(f"Total files updated: {count}")

if __name__ == "__main__":
    force_bom_debug()
