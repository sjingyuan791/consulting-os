"""
OCR Processor for Consulting OS.
Extracts financial data from PDF/images with manual correction support.

決算書OCR取込モジュール:
- PDF/画像からのテキスト抽出
- 勘定科目の自動認識・マッピング
- 手動修正用のデータ構造
- CSV出力
"""
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from dataclasses import dataclass
from enum import Enum
import re
import csv
import io


# ==========================================
# データモデル
# ==========================================

class OCRStatus(str, Enum):
    """OCR処理状態"""
    PENDING = "pending"
    EXTRACTED = "extracted"
    MAPPED = "mapped"
    VERIFIED = "verified"
    ERROR = "error"


class ExtractedCell(BaseModel):
    """抽出されたセル"""
    row: int
    col: int
    text: str
    confidence: float = Field(default=0.0, description="OCR信頼度 0-1")
    is_number: bool = False
    numeric_value: Optional[float] = None


class ExtractedTable(BaseModel):
    """抽出されたテーブル"""
    page: int = 1
    table_type: str = ""  # "BS", "PL", "CF"
    cells: List[ExtractedCell] = []
    rows: int = 0
    cols: int = 0


class AccountMapping(BaseModel):
    """勘定科目マッピング"""
    extracted_name: str  # OCRで読み取った名前
    mapped_code: str = ""  # 標準勘定科目コード
    mapped_name: str = ""  # 標準勘定科目名
    confidence: float = 0.0  # マッピング信頼度
    is_verified: bool = False  # ユーザー確認済み
    value: Optional[float] = None


class OCRExtraction(BaseModel):
    """OCR抽出結果"""
    filename: str
    status: OCRStatus = OCRStatus.PENDING
    tables: List[ExtractedTable] = []
    mappings: List[AccountMapping] = []
    errors: List[str] = []
    warnings: List[str] = []


# ==========================================
# 標準勘定科目マッピング辞書
# ==========================================

ACCOUNT_MAPPINGS = {
    # 資産の部 - 流動資産
    "現金": ("cash", "現金及び預金"),
    "現金及び預金": ("cash", "現金及び預金"),
    "預金": ("cash", "現金及び預金"),
    "受取手形": ("notes_receivable", "受取手形"),
    "売掛金": ("receivables", "売掛金"),
    "売上債権": ("receivables", "売掛金"),
    "有価証券": ("securities", "有価証券"),
    "商品": ("inventory_goods", "商品"),
    "製品": ("inventory_products", "製品"),
    "原材料": ("inventory_materials", "原材料"),
    "仕掛品": ("inventory_wip", "仕掛品"),
    "貯蔵品": ("inventory_supplies", "貯蔵品"),
    "前払費用": ("prepaid_expenses", "前払費用"),
    "短期貸付金": ("short_term_loans", "短期貸付金"),
    "未収入金": ("accrued_revenue", "未収入金"),
    "貸倒引当金": ("allowance_doubtful", "貸倒引当金"),
    "流動資産合計": ("current_assets", "流動資産合計"),
    
    # 資産の部 - 固定資産
    "建物": ("buildings", "建物"),
    "構築物": ("structures", "構築物"),
    "機械装置": ("machinery", "機械装置"),
    "車両運搬具": ("vehicles", "車両運搬具"),
    "工具器具備品": ("equipment", "工具器具備品"),
    "土地": ("land", "土地"),
    "建設仮勘定": ("construction_in_progress", "建設仮勘定"),
    "無形固定資産": ("intangible_assets", "無形固定資産"),
    "投資有価証券": ("investment_securities", "投資有価証券"),
    "長期貸付金": ("long_term_loans", "長期貸付金"),
    "繰延税金資産": ("deferred_tax_assets", "繰延税金資産"),
    "固定資産合計": ("fixed_assets", "固定資産合計"),
    "資産合計": ("total_assets", "資産合計"),
    "資産の部合計": ("total_assets", "資産合計"),
    
    # 負債の部 - 流動負債
    "支払手形": ("notes_payable", "支払手形"),
    "買掛金": ("payables", "買掛金"),
    "仕入債務": ("payables", "買掛金"),
    "短期借入金": ("short_term_debt", "短期借入金"),
    "1年内返済長期借入金": ("current_portion_ltd", "1年内返済長期借入金"),
    "未払金": ("accrued_expenses", "未払金"),
    "未払費用": ("accrued_liabilities", "未払費用"),
    "前受金": ("advance_received", "前受金"),
    "預り金": ("deposits_received", "預り金"),
    "賞与引当金": ("bonus_provision", "賞与引当金"),
    "流動負債合計": ("current_liabilities", "流動負債合計"),
    
    # 負債の部 - 固定負債
    "長期借入金": ("long_term_debt", "長期借入金"),
    "社債": ("bonds_payable", "社債"),
    "リース債務": ("lease_obligations", "リース債務"),
    "退職給付引当金": ("retirement_provision", "退職給付引当金"),
    "役員退職慰労引当金": ("director_retirement_provision", "役員退職慰労引当金"),
    "繰延税金負債": ("deferred_tax_liabilities", "繰延税金負債"),
    "固定負債合計": ("long_term_liabilities", "固定負債合計"),
    "負債合計": ("total_liabilities", "負債合計"),
    "負債の部合計": ("total_liabilities", "負債合計"),
    
    # 純資産の部
    "資本金": ("capital_stock", "資本金"),
    "資本剰余金": ("capital_surplus", "資本剰余金"),
    "利益剰余金": ("retained_earnings", "利益剰余金"),
    "自己株式": ("treasury_stock", "自己株式"),
    "純資産合計": ("net_assets", "純資産合計"),
    "純資産の部合計": ("net_assets", "純資産合計"),
    "負債純資産合計": ("total_liabilities_equity", "負債純資産合計"),
    
    # 損益計算書
    "売上高": ("revenue", "売上高"),
    "売上原価": ("cogs", "売上原価"),
    "売上総利益": ("gross_profit", "売上総利益"),
    "販売費及び一般管理費": ("sga", "販売費及び一般管理費"),
    "販管費": ("sga", "販売費及び一般管理費"),
    "役員報酬": ("executive_compensation", "役員報酬"),
    "給料手当": ("salaries", "給料手当"),
    "減価償却費": ("depreciation", "減価償却費"),
    "営業利益": ("operating_profit", "営業利益"),
    "営業外収益": ("non_operating_income", "営業外収益"),
    "受取利息": ("interest_income", "受取利息"),
    "営業外費用": ("non_operating_expenses", "営業外費用"),
    "支払利息": ("interest_expense", "支払利息"),
    "経常利益": ("ordinary_profit", "経常利益"),
    "特別利益": ("special_income", "特別利益"),
    "特別損失": ("special_loss", "特別損失"),
    "税引前当期純利益": ("income_before_tax", "税引前当期純利益"),
    "法人税等": ("income_taxes", "法人税等"),
    "当期純利益": ("net_income", "当期純利益"),
}


# ==========================================
# OCRプロセッサ
# ==========================================

class OCRProcessor:
    """OCR処理クラス"""
    
    def __init__(self):
        self.account_dict = ACCOUNT_MAPPINGS
    
    def extract_from_text(self, text: str) -> OCRExtraction:
        """
        テキストから財務データを抽出。
        (実際のOCRは外部ライブラリで行い、このメソッドは抽出済みテキストを処理)
        
        Args:
            text: OCR済みテキスト
        
        Returns:
            OCRExtraction
        """
        result = OCRExtraction(
            filename="manual_input",
            status=OCRStatus.EXTRACTED
        )
        
        # 数値を含む行を抽出
        lines = text.strip().split('\n')
        mappings = []
        
        for line in lines:
            mapping = self._parse_line(line)
            if mapping:
                mappings.append(mapping)
        
        result.mappings = mappings
        result.status = OCRStatus.MAPPED
        
        return result
    
    def _parse_line(self, line: str) -> Optional[AccountMapping]:
        """1行をパースして勘定科目と金額を抽出"""
        
        # 空行スキップ
        if not line.strip():
            return None
        
        # 数値パターン
        number_pattern = r'[\d,]+(?:\.\d+)?'
        
        # 数値を抽出
        numbers = re.findall(number_pattern, line)
        if not numbers:
            return None
        
        # 最後の数値を金額とみなす
        value_str = numbers[-1].replace(',', '')
        try:
            value = float(value_str)
        except ValueError:
            return None
        
        # 勘定科目名を抽出（数値の前の部分）
        name_part = re.split(number_pattern, line)[0].strip()
        if not name_part:
            return None
        
        # 標準科目にマッピング
        code, mapped_name = self._map_account(name_part)
        confidence = 1.0 if code else 0.5
        
        return AccountMapping(
            extracted_name=name_part,
            mapped_code=code or "",
            mapped_name=mapped_name or name_part,
            confidence=confidence,
            value=value
        )
    
    def _map_account(self, name: str) -> Tuple[str, str]:
        """勘定科目名を標準コードにマッピング"""
        
        # 完全一致
        if name in self.account_dict:
            return self.account_dict[name]
        
        # 部分一致
        for key, (code, mapped_name) in self.account_dict.items():
            if key in name or name in key:
                return (code, mapped_name)
        
        return ("", "")
    
    def mappings_to_dict(
        self, 
        mappings: List[AccountMapping],
        year: int = 2024
    ) -> Dict[str, Any]:
        """マッピング結果を辞書形式に変換"""
        
        result = {"year": year}
        
        for m in mappings:
            if m.mapped_code and m.value is not None:
                result[m.mapped_code] = m.value
        
        return result
    
    def mappings_to_csv(
        self, 
        mappings: List[AccountMapping],
        year: int = 2024
    ) -> str:
        """マッピング結果をCSV形式に変換"""
        
        data = self.mappings_to_dict(mappings, year)
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(data.keys())
        writer.writerow(data.values())
        
        return output.getvalue()
    
    def get_unmatched_items(
        self, 
        mappings: List[AccountMapping]
    ) -> List[AccountMapping]:
        """マッピングできなかった項目を返す"""
        return [m for m in mappings if not m.mapped_code]
    
    def validate_extraction(
        self, 
        mappings: List[AccountMapping]
    ) -> List[str]:
        """
        抽出結果を検証。
        
        Returns:
            警告メッセージのリスト
        """
        warnings = []
        
        # 必須項目チェック
        required = ["revenue", "operating_profit", "net_income", "total_assets", "net_assets"]
        found_codes = {m.mapped_code for m in mappings}
        
        for req in required:
            if req not in found_codes:
                warnings.append(f"必須項目 '{req}' が見つかりません")
        
        # BS整合性チェック
        assets = next((m.value for m in mappings if m.mapped_code == "total_assets"), None)
        liabilities = next((m.value for m in mappings if m.mapped_code == "total_liabilities"), None)
        equity = next((m.value for m in mappings if m.mapped_code == "net_assets"), None)
        
        if assets and liabilities and equity:
            if abs(assets - (liabilities + equity)) > assets * 0.01:
                warnings.append("資産=負債+純資産 の整合性エラー")
        
        return warnings


# ==========================================
# ファサード関数
# ==========================================

def process_ocr_text(text: str) -> OCRExtraction:
    """
    OCRテキストを処理して財務データを抽出。
    
    Args:
        text: OCR済みテキスト（または手動入力テキスト）
    
    Returns:
        OCRExtraction
    """
    processor = OCRProcessor()
    result = processor.extract_from_text(text)
    result.warnings = processor.validate_extraction(result.mappings)
    return result


def get_standard_accounts() -> Dict[str, Tuple[str, str]]:
    """標準勘定科目辞書を返す"""
    return ACCOUNT_MAPPINGS


def create_manual_input_template() -> str:
    """
    手動入力用テンプレートテキストを生成。
    
    Returns:
        入力用テンプレート文字列
    """
    template = """# 決算書データ入力
# 形式: 勘定科目名 金額（万円）
# 例:
# 売上高 100000
# 売上原価 70000

# === 貸借対照表 ===
# 資産の部
現金及び預金 
売掛金 
棚卸資産 
流動資産合計 
固定資産合計 
資産合計 

# 負債の部
買掛金 
短期借入金 
長期借入金 
流動負債合計 
固定負債合計 
負債合計 

# 純資産の部
資本金 
利益剰余金 
純資産合計 

# === 損益計算書 ===
売上高 
売上原価 
売上総利益 
販売費及び一般管理費 
役員報酬 
減価償却費 
営業利益 
経常利益 
当期純利益 
"""
    return template
