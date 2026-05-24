"""
CSV Template Generator for Consulting OS.
Generates industry-specific financial data templates.

CSVテンプレート生成モジュール:
- 基本財務テンプレート
- 業種固有テンプレート（飲食/医療/製造/建設）
- M&A DD用拡張テンプレート
- ブランク許容フィールドの明示
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import csv
import io


# ==========================================
# フィールド定義
# ==========================================

@dataclass
class FieldDefinition:
    """CSVフィールド定義"""
    name: str
    label_ja: str
    unit: str = ""
    required: bool = True
    description: str = ""
    category: str = "基本"


# 基本財務項目（必須）
BASIC_FINANCIAL_FIELDS = [
    FieldDefinition("年度", "年度", "", True, "会計年度（西暦）", "基本"),
    FieldDefinition("売上高", "売上高", "万円", True, "年間売上高", "PL"),
    FieldDefinition("売上原価", "売上原価", "万円", False, "売上原価・仕入高", "PL"),
    FieldDefinition("売上総利益", "売上総利益", "万円", False, "粗利益（売上-原価）", "PL"),
    FieldDefinition("販売管理費", "販売管理費", "万円", False, "販管費合計", "PL"),
    FieldDefinition("営業利益", "営業利益", "万円", True, "本業の利益", "PL"),
    FieldDefinition("経常利益", "経常利益", "万円", False, "経常的な利益", "PL"),
    FieldDefinition("当期純利益", "当期純利益", "万円", True, "最終利益", "PL"),
]

# 拡張財務項目（詳細分析用）
EXTENDED_FINANCIAL_FIELDS = [
    FieldDefinition("営業外収益", "営業外収益", "万円", False, "受取利息等", "PL"),
    FieldDefinition("営業外費用", "営業外費用", "万円", False, "支払利息等", "PL"),
    FieldDefinition("特別利益", "特別利益", "万円", False, "臨時的な利益", "PL"),
    FieldDefinition("特別損失", "特別損失", "万円", False, "臨時的な損失", "PL"),
    FieldDefinition("減価償却費", "減価償却費", "万円", False, "EBITDA算出用", "PL"),
    FieldDefinition("人件費", "人件費", "万円", False, "給与・福利厚生", "PL"),
    FieldDefinition("広告宣伝費", "広告宣伝費", "万円", False, "マーケティング費用", "PL"),
    FieldDefinition("研究開発費", "研究開発費", "万円", False, "R&D投資", "PL"),
]

# 貸借対照表項目
BALANCE_SHEET_FIELDS = [
    FieldDefinition("総資産", "総資産", "万円", True, "資産合計", "BS"),
    FieldDefinition("流動資産", "流動資産", "万円", False, "1年以内に現金化できる資産", "BS"),
    FieldDefinition("現預金", "現預金", "万円", False, "現金・預金", "BS"),
    FieldDefinition("売掛金", "売掛金", "万円", False, "売上債権", "BS"),
    FieldDefinition("棚卸資産", "棚卸資産", "万円", False, "在庫", "BS"),
    FieldDefinition("固定資産", "固定資産", "万円", False, "土地・建物・設備等", "BS"),
    FieldDefinition("流動負債", "流動負債", "万円", False, "1年以内に返済する負債", "BS"),
    FieldDefinition("買掛金", "買掛金", "万円", False, "仕入債務", "BS"),
    FieldDefinition("短期借入金", "短期借入金", "万円", False, "1年以内返済の借入", "BS"),
    FieldDefinition("固定負債", "固定負債", "万円", False, "長期負債", "BS"),
    FieldDefinition("長期借入金", "長期借入金", "万円", False, "1年超の借入", "BS"),
    FieldDefinition("純資産", "純資産", "万円", True, "自己資本", "BS"),
    FieldDefinition("有利子負債合計", "有利子負債合計", "万円", False, "借入金合計", "BS"),
]

# M&A DD用項目
MA_DD_FIELDS = [
    FieldDefinition("役員借入金", "役員借入金", "万円", False, "経営者からの借入", "DD"),
    FieldDefinition("個人保証額", "個人保証額", "万円", False, "経営者の個人保証", "DD"),
    FieldDefinition("未払残業代", "未払残業代", "万円", False, "未払労働債務", "DD"),
    FieldDefinition("リース債務", "リース債務", "万円", False, "オフバランス債務", "DD"),
    FieldDefinition("退職給付債務", "退職給付債務", "万円", False, "将来の退職金負担", "DD"),
]

# 経営指標
MANAGEMENT_FIELDS = [
    FieldDefinition("従業員数", "従業員数", "人", False, "正社員・パート含む", "経営"),
    FieldDefinition("正社員数", "正社員数", "人", False, "正規雇用のみ", "経営"),
    FieldDefinition("パート数", "パート・アルバイト数", "人", False, "非正規雇用", "経営"),
]

# 業種固有項目（飲食業）
RESTAURANT_FIELDS = [
    FieldDefinition("坪数", "店舗面積", "坪", False, "店舗の広さ", "飲食"),
    FieldDefinition("席数", "座席数", "席", False, "客席数", "飲食"),
    FieldDefinition("日次客数", "1日平均客数", "人", False, "日次来客数", "飲食"),
    FieldDefinition("原材料費", "原材料費", "万円", False, "Food Cost", "飲食"),
    FieldDefinition("家賃", "家賃", "万円", False, "月額賃料", "飲食"),
]

# 業種固有項目（医療）
HEALTHCARE_FIELDS = [
    FieldDefinition("病床数", "病床数", "床", False, "入院ベッド数", "医療"),
    FieldDefinition("外来患者数", "年間外来患者数", "人", False, "外来延べ患者数", "医療"),
    FieldDefinition("入院患者延日数", "入院患者延日数", "日", False, "年間入院延べ日数", "医療"),
    FieldDefinition("看護師数", "看護師数", "人", False, "看護スタッフ数", "医療"),
]

# 業種固有項目（製造業）
MANUFACTURING_FIELDS = [
    FieldDefinition("生産高", "生産高", "万円", False, "年間生産額", "製造"),
    FieldDefinition("設備稼働率", "設備稼働率", "%", False, "生産設備の稼働率", "製造"),
    FieldDefinition("不良率", "不良率", "%", False, "製品不良の発生率", "製造"),
    FieldDefinition("外注費", "外注費", "万円", False, "外注加工費", "製造"),
]

# 業種固有項目（建設業）
CONSTRUCTION_FIELDS = [
    FieldDefinition("完成工事高", "完成工事高", "万円", False, "年間完成工事売上", "建設"),
    FieldDefinition("受注残高", "受注残高", "万円", False, "未完成工事残高", "建設"),
    FieldDefinition("外注費", "外注費", "万円", False, "下請費用", "建設"),
    FieldDefinition("技術者数", "技術者数", "人", False, "1級/2級建築士等", "建設"),
]


# ==========================================
# テンプレート生成クラス
# ==========================================

class CSVTemplateGenerator:
    """CSVテンプレート生成クラス"""
    
    INDUSTRY_FIELDS = {
        "general": [],
        "restaurant": RESTAURANT_FIELDS,
        "healthcare": HEALTHCARE_FIELDS,
        "manufacturing": MANUFACTURING_FIELDS,
        "construction": CONSTRUCTION_FIELDS,
    }
    
    def generate_template(
        self,
        industry: str = "general",
        include_dd_fields: bool = False,
        include_extended: bool = True,
        sample_rows: int = 3
    ) -> str:
        """
        CSVテンプレートを生成。
        
        Args:
            industry: 業種（general/restaurant/healthcare/manufacturing/construction）
            include_dd_fields: M&A DD項目を含めるか
            include_extended: 拡張財務項目を含めるか
            sample_rows: サンプルデータ行数
        
        Returns:
            CSV形式の文字列
        """
        # フィールド構築
        fields = (
            BASIC_FINANCIAL_FIELDS +
            (EXTENDED_FINANCIAL_FIELDS if include_extended else []) +
            BALANCE_SHEET_FIELDS +
            (MA_DD_FIELDS if include_dd_fields else []) +
            MANAGEMENT_FIELDS +
            self.INDUSTRY_FIELDS.get(industry, [])
        )
        
        # ヘッダー行
        headers = [f.name for f in fields]
        
        # サンプルデータ行
        rows = []
        base_year = 2023
        for i in range(sample_rows):
            row = self._generate_sample_row(fields, base_year + i)
            rows.append(row)
        
        # CSV生成
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        
        return output.getvalue()
    
    def generate_field_guide(
        self,
        industry: str = "general",
        include_dd_fields: bool = False,
        include_extended: bool = True
    ) -> str:
        """
        フィールドガイド（入力説明）を生成。
        
        Returns:
            Markdown形式のフィールドガイド
        """
        fields = (
            BASIC_FINANCIAL_FIELDS +
            (EXTENDED_FINANCIAL_FIELDS if include_extended else []) +
            BALANCE_SHEET_FIELDS +
            (MA_DD_FIELDS if include_dd_fields else []) +
            MANAGEMENT_FIELDS +
            self.INDUSTRY_FIELDS.get(industry, [])
        )
        
        guide = "# 財務データ入力ガイド\n\n"
        guide += "## 凡例\n"
        guide += "- ◎ 必須項目\n"
        guide += "- ○ 任意項目（入力推奨）\n"
        guide += "- △ 任意項目（ブランク可）\n\n"
        
        # カテゴリ別にグループ化
        categories = {}
        for f in fields:
            if f.category not in categories:
                categories[f.category] = []
            categories[f.category].append(f)
        
        for cat, cat_fields in categories.items():
            guide += f"## {cat}\n\n"
            guide += "| 項目名 | 単位 | 必須 | 説明 |\n"
            guide += "|--------|------|------|------|\n"
            for f in cat_fields:
                req = "◎" if f.required else "○"
                guide += f"| {f.label_ja} | {f.unit} | {req} | {f.description} |\n"
            guide += "\n"
        
        return guide
    
    def _generate_sample_row(self, fields: List[FieldDefinition], year: int) -> List[str]:
        """サンプルデータ行を生成"""
        row = []
        for f in fields:
            if f.name == "年度":
                row.append(str(year))
            elif not f.required:
                # 任意項目はブランクにする
                row.append("")
            elif "売上" in f.name:
                row.append("100000")
            elif "利益" in f.name:
                row.append("5000")
            elif "資産" in f.name or "負債" in f.name or "純資産" in f.name:
                row.append("50000")
            else:
                row.append("")
        return row


# ==========================================
# ファサード関数
# ==========================================

def generate_financial_template(
    industry: str = "general",
    include_dd_fields: bool = False
) -> str:
    """
    財務データテンプレートを生成。
    
    Args:
        industry: 業種（general/restaurant/healthcare/manufacturing/construction）
        include_dd_fields: M&A DD項目を含めるか
    
    Returns:
        CSV形式の文字列
    """
    generator = CSVTemplateGenerator()
    return generator.generate_template(
        industry=industry,
        include_dd_fields=include_dd_fields,
        include_extended=True,
        sample_rows=3
    )


def generate_field_guide(industry: str = "general") -> str:
    """フィールドガイドを生成"""
    generator = CSVTemplateGenerator()
    return generator.generate_field_guide(
        industry=industry,
        include_dd_fields=True,
        include_extended=True
    )


def get_available_industries() -> List[Dict[str, str]]:
    """利用可能な業種一覧を返す"""
    return [
        {"code": "general", "name": "一般（全業種共通）"},
        {"code": "restaurant", "name": "飲食業"},
        {"code": "healthcare", "name": "医療・介護"},
        {"code": "manufacturing", "name": "製造業"},
        {"code": "construction", "name": "建設業"},
    ]
