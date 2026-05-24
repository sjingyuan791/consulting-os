
import os
import shutil

SOURCE_DIR = r"c:\Users\watar\OneDrive\デスクトップ\Consulting OS\sample_data"
TARGET_DIR = r"c:\Users\watar\OneDrive\デスクトップ\Consulting OS\sample_data\02_内部環境データ"

# Map English Filename -> Japanese Filename
MAPPING = {
    "budget_actual_sample.csv": "予算実績管理表.csv",
    "cashflow_forecast_sample.csv": "資金繰り予定表.csv",
    "customers_sample.csv": "得意先台帳.csv",
    "employees_sample.csv": "従業員名簿.csv",
    "financials_sample.csv": "財務３表サマリ.csv",
    "fixed_assets_sample.csv": "固定資産台帳.csv",
    "interview_notes.txt": "社長インタビュー等の議事録.txt",
    "loans_sample.csv": "借入金返済予定表.csv",
    "monthly_data_sample.csv": "月次推移表.csv",
    "products_inventory_sample.csv": "商品在庫マスタ.csv",
    "sales_detail_sample.csv": "売上明細データ.csv",
    "segment_pnl_sample.csv": "部門別損益計算書.csv",
    "suppliers_sample.csv": "仕入先台帳.csv"
}

def process_files():
    print(f"Processing files from {SOURCE_DIR} to {TARGET_DIR}...")
    
    if not os.path.exists(TARGET_DIR):
        os.makedirs(TARGET_DIR)
        
    count = 0
    # 1. Check Source Dir (sample_data root)
    for eng, jpn in MAPPING.items():
        src = os.path.join(SOURCE_DIR, eng)
        dst = os.path.join(TARGET_DIR, jpn)
        
        if os.path.exists(src):
            try:
                # Move and Rename
                shutil.move(src, dst)
                print(f"[MOVED] {eng} -> {jpn}")
                count += 1
            except Exception as e:
                print(f"Error moving {eng}: {e}")
                
    # 2. Check Target Dir (in case English files are already inside)
    for eng, jpn in MAPPING.items():
        src_in_target = os.path.join(TARGET_DIR, eng)
        dst = os.path.join(TARGET_DIR, jpn)
        
        if os.path.exists(src_in_target):
             try:
                if os.path.exists(dst):
                    print(f"Skipping {eng} (Target {jpn} already exists)")
                else:
                    os.rename(src_in_target, dst)
                    print(f"[RENAMED] {eng} -> {jpn}")
                    count += 1
             except Exception as e:
                 print(f"Error renaming inside target {eng}: {e}")

    print(f"Total processed: {count}")

if __name__ == "__main__":
    process_files()
