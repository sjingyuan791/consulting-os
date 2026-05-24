"""
Enhanced Data Quality Gate for Consulting OS.
包括的なデータ品質保証モジュール（Garbage In, Garbage Out 防止）

機能:
1. バリデーション（必須項目チェック、数値形式確認）
2. 整合性チェック（BS合計=負債+純資産 等）
3. 異常値検出（利益率200%などの警告）
4. 品質スコア算出
"""
from typing import Dict, List, Optional, Any, Tuple
from pydantic import BaseModel, Field
from enum import Enum
import pandas as pd


# ==========================================
# 定数・設定
# ==========================================

class Severity(str, Enum):
    """問題の重大度"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class CheckCategory(str, Enum):
    """チェックカテゴリ"""
    REQUIRED = "required"
    FORMAT = "format"
    CONSISTENCY = "consistency"
    ANOMALY = "anomaly"
    COMPLETENESS = "completeness"


# データタイプ別の必須カラム
REQUIRED_COLUMNS = {
    "financials": {
        "必須": ["year", "sales", "operating_profit", "net_income", "total_assets", "net_assets"],
        "推奨": ["gross_profit", "current_assets", "current_liabilities", "depreciation"],
    },
    "loans": {
        "必須": ["借入先名", "現在残高", "年間返済額"],
        "推奨": ["金利", "担保", "返済期間年"],
    },
    "monthly": {
        "必須": ["月", "売上高"],
        "推奨": ["営業利益", "現預金残高"],
    },
    "employees": {
        "必須": ["従業員ID", "氏名", "部門"],
        "推奨": ["年収", "入社日"],
    },
    "customers": {
        "必須": ["得意先名", "売上高年間"],
        "推奨": ["売掛金残高", "回収サイト日"],
    },
    "products": {
        "必須": ["商品コード", "商品名", "単価"],
        "推奨": ["原価", "在庫数量"],
    },
}


# ==========================================
# データモデル
# ==========================================

class ValidationIssue(BaseModel):
    """検出された問題"""
    severity: Severity
    category: CheckCategory
    column: str = ""
    row: Optional[int] = None
    message: str
    value: Optional[Any] = None
    suggestion: str = ""


class QualityScore(BaseModel):
    """品質スコア"""
    overall: float = 0
    completeness: float = 0
    accuracy: float = 0
    consistency: float = 0
    grade: str = ""


class QualityGateResult(BaseModel):
    """品質ゲート結果"""
    dataset_type: str
    passed: bool = False
    score: QualityScore = Field(default_factory=QualityScore)
    issues: List[ValidationIssue] = []
    summary: str = ""
    row_count: int = 0
    column_count: int = 0
    required_missing: List[str] = []
    recommendations: List[str] = []


# ==========================================
# Quality Gate Engine
# ==========================================

class EnhancedQualityGateEngine:
    """拡張データ品質検証エンジン"""
    
    def __init__(self):
        self.required_columns = REQUIRED_COLUMNS
    
    def validate(self, df: pd.DataFrame, dataset_type: str = "financials") -> QualityGateResult:
        """データフレームを検証"""
        issues: List[ValidationIssue] = []
        
        row_count = len(df)
        col_count = len(df.columns)
        
        if row_count == 0:
            return QualityGateResult(
                dataset_type=dataset_type,
                passed=False,
                score=QualityScore(overall=0, grade="F"),
                issues=[ValidationIssue(
                    severity=Severity.ERROR,
                    category=CheckCategory.REQUIRED,
                    message="データが空です"
                )],
                summary="データなし"
            )
        
        # 1. 必須項目チェック
        req_issues, missing = self._check_required_columns(df, dataset_type)
        issues.extend(req_issues)
        
        # 2. 形式チェック
        fmt_issues = self._check_format(df)
        issues.extend(fmt_issues)
        
        # 3. 整合性チェック（財務データ）
        if dataset_type == "financials":
            consist_issues = self._check_consistency(df)
            issues.extend(consist_issues)
        
        # 4. 異常値チェック
        anomaly_issues = self._check_anomalies(df, dataset_type)
        issues.extend(anomaly_issues)
        
        # 5. 完全性チェック
        complete_issues, completeness = self._check_completeness(df)
        issues.extend(complete_issues)
        
        # 6. スコア計算
        score = self._calculate_score(issues, completeness, len(missing))
        
        # 7. 合否判定
        errors = sum(1 for i in issues if i.severity == Severity.ERROR)
        passed = errors == 0 and score.overall >= 60
        
        # 8. サマリー
        summary = self._generate_summary(score, issues)
        
        # 9. 提案
        recommendations = self._generate_recommendations(issues, missing)
        
        return QualityGateResult(
            dataset_type=dataset_type,
            passed=passed,
            score=score,
            issues=issues,
            summary=summary,
            row_count=row_count,
            column_count=col_count,
            required_missing=missing,
            recommendations=recommendations
        )
    
    def _check_required_columns(self, df: pd.DataFrame, dataset_type: str) -> Tuple[List[ValidationIssue], List[str]]:
        """必須カラムチェック"""
        issues = []
        missing = []
        
        req_def = self.required_columns.get(dataset_type, {})
        req_cols = req_def.get("必須", [])
        rec_cols = req_def.get("推奨", [])
        
        df_cols_lower = [c.lower() for c in df.columns]
        
        for col in req_cols:
            if col.lower() not in df_cols_lower and col not in df.columns:
                issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    category=CheckCategory.REQUIRED,
                    column=col,
                    message=f"必須項目 '{col}' がありません",
                    suggestion=f"CSVに '{col}' カラムを追加してください"
                ))
                missing.append(col)
        
        for col in rec_cols:
            if col.lower() not in df_cols_lower and col not in df.columns:
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    category=CheckCategory.REQUIRED,
                    column=col,
                    message=f"推奨項目 '{col}' がありません"
                ))
        
        return issues, missing
    
    def _check_format(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """形式チェック"""
        issues = []
        numeric_keywords = ['金額', '残高', '売上', '利益', '資産', '負債', 
                           'sales', 'profit', 'assets', 'amount', 'revenue']
        
        for col in df.columns:
            if any(kw in col.lower() for kw in numeric_keywords):
                non_numeric = df[col].apply(lambda x: not self._is_numeric(x) if pd.notna(x) else False)
                bad_rows = df.index[non_numeric].tolist()
                if bad_rows:
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        category=CheckCategory.FORMAT,
                        column=col,
                        message=f"'{col}' に数値以外のデータがあります（行: {bad_rows[:5]}）",
                        suggestion="数値形式で入力してください"
                    ))
        return issues
    
    def _is_numeric(self, value) -> bool:
        """数値判定"""
        if isinstance(value, (int, float)):
            return True
        if isinstance(value, str):
            try:
                float(value.replace(',', '').replace('円', '').replace('万', ''))
                return True
            except:
                return False
        return False
    
    def _check_consistency(self, df: pd.DataFrame) -> List[ValidationIssue]:
        """整合性チェック"""
        issues = []
        
        for idx, row in df.iterrows():
            # BS貸借一致
            assets = self._get_val(row, ['total_assets', '総資産', '資産合計'])
            liab = self._get_val(row, ['total_liabilities', '負債合計'])
            equity = self._get_val(row, ['net_assets', '純資産', '純資産合計'])
            
            if assets and liab is not None and equity:
                expected = liab + equity
                if abs(assets - expected) > assets * 0.01:
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        category=CheckCategory.CONSISTENCY,
                        row=int(idx),
                        message=f"BS不一致: 資産({assets:,.0f}) ≠ 負債+純資産({expected:,.0f})",
                        suggestion="資産合計を確認してください"
                    ))
            
            # 粗利計算
            sales = self._get_val(row, ['sales', '売上高'])
            cogs = self._get_val(row, ['cogs', '売上原価'])
            gross = self._get_val(row, ['gross_profit', '売上総利益'])
            
            if sales and cogs and gross:
                expected = sales - cogs
                if abs(gross - expected) > sales * 0.01:
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        category=CheckCategory.CONSISTENCY,
                        row=int(idx),
                        message=f"粗利不一致: {gross:,.0f} ≠ 売上-原価({expected:,.0f})"
                    ))
        
        return issues
    
    def _get_val(self, row: pd.Series, keys: List[str]) -> Optional[float]:
        """複数キーから数値取得"""
        for key in keys:
            if key in row.index and pd.notna(row[key]):
                val = row[key]
                if isinstance(val, (int, float)):
                    return float(val)
                try:
                    return float(str(val).replace(',', ''))
                except:
                    pass
        return None
    
    def _check_anomalies(self, df: pd.DataFrame, dataset_type: str) -> List[ValidationIssue]:
        """異常値チェック"""
        issues = []
        
        if dataset_type != "financials":
            return issues
        
        for idx, row in df.iterrows():
            sales = self._get_val(row, ['sales', '売上高'])
            if not sales or sales == 0:
                continue
            
            # 営業利益率
            op = self._get_val(row, ['operating_profit', '営業利益'])
            if op:
                margin = op / sales
                if margin < -0.5 or margin > 0.5:
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        category=CheckCategory.ANOMALY,
                        row=int(idx),
                        column="operating_profit",
                        message=f"営業利益率が異常: {margin*100:.1f}%（通常-50%～50%）"
                    ))
            
            # 粗利率
            gross = self._get_val(row, ['gross_profit', '売上総利益'])
            if gross:
                margin = gross / sales
                if margin < 0 or margin > 0.9:
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        category=CheckCategory.ANOMALY,
                        row=int(idx),
                        column="gross_profit",
                        message=f"粗利率が異常: {margin*100:.1f}%（通常0%～90%）"
                    ))
        
        return issues
    
    def _check_completeness(self, df: pd.DataFrame) -> Tuple[List[ValidationIssue], float]:
        """完全性チェック"""
        issues = []
        total = df.size
        nulls = df.isnull().sum().sum()
        completeness = (total - nulls) / total * 100 if total > 0 else 0
        
        for col in df.columns:
            null_rate = df[col].isnull().sum() / len(df)
            if null_rate > 0.5:
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    category=CheckCategory.COMPLETENESS,
                    column=col,
                    message=f"'{col}' の欠損率が高い: {null_rate*100:.0f}%"
                ))
        
        return issues, completeness
    
    def _calculate_score(self, issues: List[ValidationIssue], completeness: float, missing: int) -> QualityScore:
        """スコア計算"""
        errors = sum(1 for i in issues if i.severity == Severity.ERROR)
        warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
        
        accuracy = max(0, 100 - errors * 20 - warnings * 5)
        consist_cnt = sum(1 for i in issues if i.category == CheckCategory.CONSISTENCY)
        consistency = max(0, 100 - consist_cnt * 10)
        
        overall = completeness * 0.3 + accuracy * 0.4 + consistency * 0.3
        overall = max(0, overall - missing * 15)
        
        if overall >= 90: grade = "A"
        elif overall >= 75: grade = "B"
        elif overall >= 60: grade = "C"
        elif overall >= 40: grade = "D"
        else: grade = "F"
        
        return QualityScore(
            overall=round(overall, 1),
            completeness=round(completeness, 1),
            accuracy=round(accuracy, 1),
            consistency=round(consistency, 1),
            grade=grade
        )
    
    def _generate_summary(self, score: QualityScore, issues: List[ValidationIssue]) -> str:
        """サマリー生成"""
        errors = sum(1 for i in issues if i.severity == Severity.ERROR)
        warnings = sum(1 for i in issues if i.severity == Severity.WARNING)
        
        if errors == 0 and warnings == 0:
            return f"✅ 品質良好（{score.overall}/100 グレード:{score.grade}）"
        elif errors == 0:
            return f"⚠️ 軽微な問題あり（{score.overall}/100 警告:{warnings}件）"
        else:
            return f"❌ 要修正（{score.overall}/100 エラー:{errors}件）"
    
    def _generate_recommendations(self, issues: List[ValidationIssue], missing: List[str]) -> List[str]:
        """改善提案"""
        recs = []
        if missing:
            recs.append(f"必須項目を追加: {', '.join(missing)}")
        if any(i.category == CheckCategory.ANOMALY for i in issues):
            recs.append("異常値を確認・修正してください")
        if any(i.category == CheckCategory.CONSISTENCY for i in issues):
            recs.append("財務数値の整合性を確認してください")
        if any(i.category == CheckCategory.COMPLETENESS for i in issues):
            recs.append("欠損データを補完してください")
        if not recs:
            recs.append("特になし（品質良好）")
        return recs


# ==========================================
# ファサード関数
# ==========================================

def validate_dataframe(df: pd.DataFrame, dataset_type: str = "financials") -> QualityGateResult:
    """データフレームを検証"""
    engine = EnhancedQualityGateEngine()
    return engine.validate(df, dataset_type)


def validate_csv_file(filepath: str, dataset_type: str = "financials") -> QualityGateResult:
    """CSVファイルを検証"""
    try:
        df = pd.read_csv(filepath, encoding='utf-8-sig')
    except UnicodeDecodeError:
        df = pd.read_csv(filepath, encoding='cp932')
    return validate_dataframe(df, dataset_type)


def get_quality_report_text(result: QualityGateResult) -> str:
    """テキスト形式のレポート"""
    lines = [
        "=" * 50,
        "データ品質レポート",
        "=" * 50,
        f"タイプ: {result.dataset_type}",
        f"行数: {result.row_count} / カラム: {result.column_count}",
        "",
        f"【判定】{result.summary}",
        "",
        f"【スコア】総合:{result.score.overall} 完全性:{result.score.completeness} 正確性:{result.score.accuracy} 整合性:{result.score.consistency}",
    ]
    
    if result.issues:
        lines.append("")
        lines.append("【問題】")
        for i, issue in enumerate(result.issues[:10], 1):
            icon = "❌" if issue.severity == Severity.ERROR else "⚠️"
            lines.append(f"  {i}. {icon} {issue.message}")
        if len(result.issues) > 10:
            lines.append(f"  ... 他 {len(result.issues) - 10} 件")
    
    
    if result.recommendations:
        lines.append("")
        lines.append("【改善提案】")
        for r in result.recommendations:
            lines.append(f"  ・{r}")
    
    return "\n".join(lines)


# ==========================================
# Decision-Grade Quality Gate
# ==========================================

def check_strategic_refinement_quality(plan: Any) -> Any:
    """
    RefinedStrategicPlanの品質を評価し、Decision-Grade認定を行う。
    Type hinting is Any to avoid circular imports, but expects RefinedStrategicPlan.
    Returns DecisionGradeStatus.
    """
    from core.schemas.refinement_schema import DecisionGradeStatus
    
    reasons = []
    
    # 1. Financial Verification
    if not plan.financials_verified:
        reasons.append("財務データが未検証です (Financials Not Verified)")
        
    # 2. Forecast Source
    if plan.forecast_source != "deterministic_engine":
        reasons.append(f"財務予測ソースが不適切です: {plan.forecast_source}")
        
    # 3. Missing Inputs
    if len(plan.missing_inputs) > 0:
        fields = [m.field_name for m in plan.missing_inputs]
        reasons.append(f"必須入力項目が欠落しています: {', '.join(fields)}")
        
    warnings = []
    
    # 4. Scenario Existence (Old check simulation, New check scenarios)
    if plan.financials_verified and (not plan.scenarios or len(plan.scenarios) == 0):
        reasons.append("財務シナリオ分析（Base/Downside/Severe）が生成されていません")
        
    # 5. Review Scenarios for Viability (Hard Blocks & Warnings)
    if plan.scenarios:
        # Check Base Case
        base = next((s for s in plan.scenarios if "Base" in s.scenario_name), None)
        downside = next((s for s in plan.scenarios if "Downside" in s.scenario_name), None)
        
        if base:
            # DSCR Checks
            if base.debt_capacity:
                dscr = base.debt_capacity[0].dscr
                if dscr < 1.0:
                    reasons.append(f"Basic CaseのDSCRが危険域です: {dscr:.2f} (<1.0) -> 債務超過リスク")
                elif dscr < 1.2:
                    warnings.append(f"Basic CaseのDSCRが要注意です: {dscr:.2f} (<1.2)")
            
            # Cashflow Checks
            if base.cashflow:
                min_cash = min(cf.ending_cash for cf in base.cashflow)
                if min_cash < 0:
                    reasons.append(f"Basic Caseで資金ショートが発生します (Min: ¥{min_cash:,.0f})")
                elif min_cash < 100: # Assumption: 100 is low buffer
                    warnings.append(f"Basic Caseの資金繰りが逼迫しています (Min: ¥{min_cash:,.0f})")
                
        if downside:
            # Downside Survival Checks
            if downside.cashflow:
                min_cash_down = min(cf.ending_cash for cf in downside.cashflow)
                if min_cash_down < 0:
                    reasons.append(f"Downsideケース(売上20%減)で資金ショートします (Min: ¥{min_cash_down:,.0f})")
                elif min_cash_down < 50:
                    warnings.append(f"Downsideケースの資金余力が低いです (Min: ¥{min_cash_down:,.0f})")

    # 6. External Constraints
    if plan.external_constraints is None:
        reasons.append("外部環境制約（External Constraints）が考慮されていません")
        
    # 7. Confidence Level
    if plan.confidence_level < 0.7:
        warnings.append(f"AI確信度がやや低いです: {plan.confidence_level:.0%}")
        # Note: Originally block, maybe just warning now? User asked for Hard Block on DSCR/Cash, didn't specify Confidence. 
        # Let's keep strict block if very low? Or move to warning for <70%? 
        # Previous code blocked < 0.7. Let's keep it consistent or relax if strict blocks are financial.
        # Let's keep it as is (blocked) or move to warning if user wants "Audit Ready" which implies financials are key.
        # Refinement: Let's block < 0.5, warn < 0.8? 
        # Stick to previous logic: Block < 0.7.
        reasons.append(f"AI確信度が低いです: {plan.confidence_level:.0%}")

    if reasons:
        return DecisionGradeStatus(status="blocked", blocking_reasons=reasons, warnings=warnings)
    elif warnings:
        return DecisionGradeStatus(status="warning", blocking_reasons=[], warnings=warnings)
    else:
        return DecisionGradeStatus(status="approved", blocking_reasons=[], warnings=[])

