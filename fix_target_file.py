
import os

target_file = r"c:\Users\watar\OneDrive\デスクトップ\Consulting OS\sample_data\02_内部環境データ\月次推移表.csv"

if os.path.exists(target_file):
    print(f"Target found: {target_file}")
    with open(target_file, "rb") as f:
        content = f.read()
    
    print(f"Head before: {content[:3]}")
    
    if content.startswith(b'\xef\xbb\xbf'):
        print("Already has BOM.")
    else:
        new_content = b'\xef\xbb\xbf' + content
        with open(target_file, "wb") as f:
            f.write(new_content)
        print("Written BOM to file.")
else:
    print(f"Target NOT found: {target_file}")
