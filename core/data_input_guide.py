"""
Data Input Guide for Consulting OS.
データ入力ガイド・UIヘルパーモジュール。

機能:
1. データタイプ別入力ガイド表示
2. 入力フォーム生成支援
3. サンプルデータ表示
4. バリデーション結果の可視化
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import os


# ==========================================
# 定数
# ==========================================

@dataclass
class FieldDefinition:
    """フィールド定義"""
    name: str
    name_ja: str
    data_type: str  # "number", "text", "date", "select"
    required: bool = False
    description: str = ""
    example: str = ""
    format_hint: str = ""
    unit: str = ""
    validation: str = ""  # 追加バリデーションルール


# データセット定義
DATASET_DEFINITIONS = {
    "financials": {
        "name": "決算書",
        "category": "財務データ",
        "description": "貸借対照表（BS）と損益計算書（PL）の勘定科目データ",
        "sample_file": "01_財務データ/決算書.csv",
        "fields": [
            FieldDefinition("year", "年度", "number", True, "決算年度", "2024", "YYYY", "年"),
            FieldDefinition("sales", "売上高", "number", True, "年間売上高", "100000000", "数値", "円"),
            FieldDefinition("cogs", "売上原価", "number", False, "売上原価", "70000000", "数値", "円"),
            FieldDefinition("gross_profit", "売上総利益", "number", False, "売上-原価", "30000000", "数値", "円"),
            FieldDefinition("sga", "販管費", "number", False, "販売費及び一般管理費", "20000000", "数値", "円"),
            FieldDefinition("operating_profit", "営業利益", "number", True, "本業の利益", "10000000", "数値", "円"),
            FieldDefinition("net_income", "当期純利益", "number", True, "最終利益", "6000000", "数値", "円"),
            FieldDefinition("total_assets", "総資産", "number", True, "資産合計", "80000000", "数値", "円"),
            FieldDefinition("current_assets", "流動資産", "number", False, "流動資産計", "40000000", "数値", "円"),
            FieldDefinition("current_liabilities", "流動負債", "number", False, "流動負債計", "25000000", "数値", "円"),
            FieldDefinition("net_assets", "純資産", "number", True, "純資産合計", "35000000", "数値", "円"),
            FieldDefinition("depreciation", "減価償却費", "number", False, "年間減価償却費", "3000000", "数値", "円"),
        ]
    },
    "loans": {
        "name": "借入一覧",
        "category": "財務データ",
        "description": "銀行借入・リース等の明細",
        "sample_file": "01_財務データ/借入一覧.csv",
        "fields": [
            FieldDefinition("借入先名", "借入先名", "text", True, "銀行名等", "〇〇銀行", "", ""),
            FieldDefinition("借入種別", "借入種別", "select", False, "長期/短期/リース", "長期借入金", "", ""),
            FieldDefinition("当初借入額", "当初借入額", "number", False, "借入時金額", "50000000", "数値", "円"),
            FieldDefinition("現在残高", "現在残高", "number", True, "現在の残高", "35000000", "数値", "円"),
            FieldDefinition("年間返済額", "年間返済額", "number", True, "年間返済額（元利合計）", "6000000", "数値", "円"),
            FieldDefinition("金利", "金利", "number", False, "年利率", "1.5", "0.0〜100.0", "%"),
            FieldDefinition("担保", "担保", "text", False, "担保の有無・種類", "土地建物", "", ""),
            FieldDefinition("保証人", "保証人", "text", False, "保証人の有無", "代表者", "", ""),
        ]
    },
    "monthly": {
        "name": "月次推移",
        "category": "財務データ",
        "description": "月次の売上・経費・残高データ",
        "sample_file": "01_財務データ/月次推移.csv",
        "fields": [
            FieldDefinition("月", "月", "text", True, "対象月", "2024/04", "YYYY/MM", ""),
            FieldDefinition("売上高", "売上高", "number", True, "月間売上", "8500000", "数値", "円"),
            FieldDefinition("売上原価", "売上原価", "number", False, "月間原価", "5500000", "数値", "円"),
            FieldDefinition("営業利益", "営業利益", "number", False, "月間営業利益", "700000", "数値", "円"),
            FieldDefinition("現預金残高", "現預金残高", "number", False, "月末現預金", "12000000", "数値", "円"),
        ]
    },
    "employees": {
        "name": "従業員一覧",
        "category": "内部環境データ",
        "description": "従業員の基本情報・給与データ",
        "sample_file": "02_内部環境データ/従業員一覧.csv",
        "fields": [
            FieldDefinition("従業員ID", "従業員ID", "text", True, "社員番号", "E001", "", ""),
            FieldDefinition("氏名", "氏名", "text", True, "従業員名", "山田太郎", "", ""),
            FieldDefinition("部門", "部門", "text", True, "所属部門", "営業部", "", ""),
            FieldDefinition("役職", "役職", "text", False, "役職名", "部長", "", ""),
            FieldDefinition("雇用形態", "雇用形態", "select", False, "正社員/パート等", "正社員", "", ""),
            FieldDefinition("年収", "年収", "number", False, "年間給与（賞与含む）", "6000000", "数値", "円"),
        ]
    },
    "customers": {
        "name": "得意先一覧",
        "category": "内部環境データ",
        "description": "顧客・取引先情報",
        "sample_file": "02_内部環境データ/得意先一覧.csv",
        "fields": [
            FieldDefinition("得意先名", "得意先名", "text", True, "会社名", "株式会社〇〇商事", "", ""),
            FieldDefinition("売上高年間", "売上高年間", "number", True, "年間売上高", "30000000", "数値", "円"),
            FieldDefinition("売掛金残高", "売掛金残高", "number", False, "現在の売掛金", "5000000", "数値", "円"),
            FieldDefinition("回収サイト日", "回収サイト日", "number", False, "平均回収日数", "30", "数値", "日"),
        ]
    },
    "products": {
        "name": "商品・在庫マスタ",
        "category": "内部環境データ",
        "description": "商品マスタと在庫情報",
        "sample_file": "02_内部環境データ/商品・在庫マスタ.csv",
        "fields": [
            FieldDefinition("商品コード", "商品コード", "text", True, "商品ID", "P001", "", ""),
            FieldDefinition("商品名", "商品名", "text", True, "商品名称", "製品A", "", ""),
            FieldDefinition("単価", "単価", "number", True, "販売単価", "5000", "数値", "円"),
            FieldDefinition("原価", "原価", "number", False, "仕入原価", "3500", "数値", "円"),
            FieldDefinition("在庫数量", "在庫数量", "number", False, "現在在庫", "200", "数値", "個"),
        ]
    },
}


# ==========================================
# UIヘルパー
# ==========================================

def get_dataset_info(dataset_type: str) -> Dict[str, Any]:
    """データセット情報を取得"""
    if dataset_type not in DATASET_DEFINITIONS:
        return {"error": f"Unknown dataset type: {dataset_type}"}
    
    defn = DATASET_DEFINITIONS[dataset_type]
    fields_info = []
    
    for f in defn["fields"]:
        fields_info.append({
            "name": f.name,
            "name_ja": f.name_ja,
            "type": f.data_type,
            "required": f.required,
            "description": f.description,
            "example": f.example,
            "unit": f.unit,
        })
    
    return {
        "dataset_type": dataset_type,
        "name": defn["name"],
        "category": defn["category"],
        "description": defn["description"],
        "sample_file": defn["sample_file"],
        "fields": fields_info,
        "required_count": sum(1 for f in defn["fields"] if f.required),
        "total_fields": len(defn["fields"]),
    }


def get_all_datasets() -> List[Dict[str, Any]]:
    """全データセット一覧を取得"""
    result = []
    for dt in DATASET_DEFINITIONS:
        info = get_dataset_info(dt)
        result.append({
            "dataset_type": dt,
            "name": info["name"],
            "category": info["category"],
            "required_count": info["required_count"],
            "sample_file": info["sample_file"],
        })
    return result


def get_input_guide_text(dataset_type: str) -> str:
    """テキスト形式の入力ガイドを生成"""
    info = get_dataset_info(dataset_type)
    
    if "error" in info:
        return info["error"]
    
    lines = [
        "=" * 50,
        f"📋 {info['name']} 入力ガイド",
        "=" * 50,
        f"カテゴリ: {info['category']}",
        f"説明: {info['description']}",
        f"サンプル: {info['sample_file']}",
        "",
        "【入力項目】",
    ]
    
    for f in info["fields"]:
        req = "【必須】" if f["required"] else ""
        unit = f" ({f['unit']})" if f["unit"] else ""
        lines.append(f"  {req}{f['name_ja']}: {f['description']} 例: {f['example']}{unit}")
    
    lines.append("")
    lines.append(f"必須項目数: {info['required_count']} / 全{info['total_fields']}項目")
    lines.append("=" * 50)
    
    return "\n".join(lines)


def get_sample_data_path(dataset_type: str, base_dir: str = "sample_data") -> Optional[str]:
    """サンプルデータのパスを取得"""
    if dataset_type not in DATASET_DEFINITIONS:
        return None
    
    sample_file = DATASET_DEFINITIONS[dataset_type]["sample_file"]
    full_path = os.path.join(base_dir, sample_file)
    
    return full_path if os.path.exists(full_path) else None


def generate_csv_header(dataset_type: str) -> str:
    """CSVヘッダー行を生成"""
    if dataset_type not in DATASET_DEFINITIONS:
        return ""
    
    fields = DATASET_DEFINITIONS[dataset_type]["fields"]
    headers = [f.name for f in fields]
    
    return ",".join(headers)


def generate_csv_template(dataset_type: str) -> str:
    """空のCSVテンプレートを生成"""
    if dataset_type not in DATASET_DEFINITIONS:
        return ""
    
    fields = DATASET_DEFINITIONS[dataset_type]["fields"]
    headers = [f.name for f in fields]
    examples = [f.example for f in fields]
    
    return "\n".join([
        ",".join(headers),
        ",".join(examples),
    ])


# ==========================================
# バリデーション結果の可視化
# ==========================================

def format_validation_result_for_ui(result) -> Dict[str, Any]:
    """
    バリデーション結果をUI表示用に整形。
    
    Args:
        result: QualityGateResult
    
    Returns:
        UI用データ
    """
    # スコアカラー
    score = result.score.overall
    if score >= 80:
        score_color = "green"
        score_icon = "✅"
    elif score >= 60:
        score_color = "yellow"
        score_icon = "⚠️"
    else:
        score_color = "red"
        score_icon = "❌"
    
    # 問題をグループ化
    errors = [i for i in result.issues if i.severity.value == "error"]
    warnings = [i for i in result.issues if i.severity.value == "warning"]
    
    return {
        "passed": result.passed,
        "summary": result.summary,
        "score": {
            "overall": score,
            "grade": result.score.grade,
            "color": score_color,
            "icon": score_icon,
            "breakdown": {
                "completeness": result.score.completeness,
                "accuracy": result.score.accuracy,
                "consistency": result.score.consistency,
            }
        },
        "counts": {
            "rows": result.row_count,
            "columns": result.column_count,
            "errors": len(errors),
            "warnings": len(warnings),
        },
        "errors": [{"message": e.message, "column": e.column, "row": e.row} for e in errors[:5]],
        "warnings": [{"message": w.message, "column": w.column} for w in warnings[:5]],
        "recommendations": result.recommendations,
        "missing_required": result.required_missing,
    }


def get_quality_badge(score: float, grade: str) -> str:
    """品質バッジHTML"""
    colors = {"A": "#22c55e", "B": "#84cc16", "C": "#eab308", "D": "#f97316", "F": "#ef4444"}
    color = colors.get(grade, "#64748b")
    
    return f"""
    <div style="display:inline-block; padding:4px 12px; border-radius:16px; 
                background:{color}; color:white; font-weight:bold;">
        {score:.0f}/100 ({grade})
    </div>
    """
