"""
Citation Schema for AI-generated content.
Provides structured attribution for all AI outputs.
"""
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class SourceType(str, Enum):
    """Types of sources for citations."""
    FINANCIAL_DATA = "financial_data"
    UPLOADED_DOC = "uploaded_doc"
    INDUSTRY_BENCHMARK = "industry_benchmark"
    SALES_DATA = "sales_data"
    USER_INPUT = "user_input"
    CALCULATION = "calculation"
    EXTERNAL_RESEARCH = "external_research"
    HISTORICAL_TREND = "historical_trend"


class Citation(BaseModel):
    """
    AI生成回答の根拠・出典を表すスキーマ。
    
    Example:
        Citation(
            source_type=SourceType.FINANCIAL_DATA,
            source_name="2024年度決算書",
            excerpt="ROA = 3.2%",
            confidence=0.95,
            page_or_location="P.15"
        )
    """
    source_type: SourceType = Field(..., description="データソースの種類")
    source_name: str = Field(..., description="ソース名（ファイル名、データセット名等）")
    excerpt: str = Field(..., description="該当箇所の抜粋（50文字以内推奨）")
    confidence: float = Field(
        default=1.0, 
        ge=0.0, 
        le=1.0, 
        description="この出典の信頼度 (0.0-1.0)"
    )
    page_or_location: Optional[str] = Field(
        default=None, 
        description="ページ番号、行番号、セル位置等"
    )
    
    def to_display_string(self) -> str:
        """UI表示用のフォーマット済み文字列を返す"""
        loc = f" ({self.page_or_location})" if self.page_or_location else ""
        return f"[{self.source_type.value}] {self.source_name}{loc}: {self.excerpt}"


class ReasoningStep(BaseModel):
    """AI推論過程の1ステップ"""
    step_number: int
    description: str
    supporting_citations: List[int] = Field(
        default=[], 
        description="このステップを裏付けるcitations配列のインデックス"
    )


class AIResponseWithCitations(BaseModel):
    """
    出典付きAI回答の統合スキーマ。
    全てのAI生成コンテンツはこのスキーマでラップされる。
    
    Example:
        AIResponseWithCitations(
            content="ROAが3.2%と業界平均(5.0%)を下回っています。",
            citations=[
                Citation(source_type="financial_data", source_name="2024年度決算書", ...),
                Citation(source_type="industry_benchmark", source_name="中小企業庁調査", ...)
            ],
            reasoning_chain=[
                ReasoningStep(step_number=1, description="財務データからROAを算出", ...),
                ReasoningStep(step_number=2, description="業界ベンチマークと比較", ...)
            ],
            confidence_score=0.85
        )
    """
    content: str = Field(..., description="AI生成コンテンツ本文")
    citations: List[Citation] = Field(
        default=[], 
        description="回答の根拠となる出典リスト"
    )
    reasoning_chain: List[ReasoningStep] = Field(
        default=[], 
        description="推論過程（ステップバイステップ）"
    )
    confidence_score: float = Field(
        default=0.0, 
        ge=0.0, 
        le=1.0, 
        description="回答全体の信頼度 (0.0-1.0)"
    )
    generated_at: datetime = Field(
        default_factory=datetime.now, 
        description="生成日時"
    )
    model_used: Optional[str] = Field(
        default=None, 
        description="使用したLLMモデル名"
    )
    
    def get_citation_summary(self) -> str:
        """出典一覧のサマリー文字列を返す"""
        if not self.citations:
            return "出典なし"
        return "\n".join([f"• {c.to_display_string()}" for c in self.citations])
    
    def has_sufficient_citations(self, min_count: int = 1) -> bool:
        """十分な出典があるかチェック"""
        return len(self.citations) >= min_count


class CitationBuilder:
    """
    出典を構築するためのヘルパークラス。
    データソースから自動的にCitationを生成。
    """
    
    @staticmethod
    def from_financial_data(
        metric_name: str,
        value: float,
        year: int,
        source_file: str = "財務諸表"
    ) -> Citation:
        """財務データから出典を生成"""
        return Citation(
            source_type=SourceType.FINANCIAL_DATA,
            source_name=f"{year}年度 {source_file}",
            excerpt=f"{metric_name} = {value:.2%}" if abs(value) < 10 else f"{metric_name} = {value:,.0f}",
            confidence=1.0,
            page_or_location=f"{year}年度データ"
        )
    
    @staticmethod
    def from_benchmark(
        metric_name: str,
        benchmark_value: float,
        industry: str,
        source: str = "中小企業庁 中小企業実態基本調査"
    ) -> Citation:
        """業界ベンチマークから出典を生成"""
        return Citation(
            source_type=SourceType.INDUSTRY_BENCHMARK,
            source_name=source,
            excerpt=f"{industry}業界 {metric_name} 平均 = {benchmark_value:.2%}",
            confidence=0.9,
            page_or_location=f"{industry}業界統計"
        )
    
    @staticmethod
    def from_calculation(
        formula: str,
        result: str,
        inputs: List[str]
    ) -> Citation:
        """計算結果から出典を生成"""
        return Citation(
            source_type=SourceType.CALCULATION,
            source_name="システム計算",
            excerpt=f"{formula} = {result}",
            confidence=1.0,
            page_or_location=f"入力: {', '.join(inputs)}"
        )
    
    @staticmethod
    def from_uploaded_document(
        doc_name: str,
        excerpt: str,
        page: Optional[str] = None
    ) -> Citation:
        """アップロードドキュメントから出典を生成"""
        return Citation(
            source_type=SourceType.UPLOADED_DOC,
            source_name=doc_name,
            excerpt=excerpt[:100] + "..." if len(excerpt) > 100 else excerpt,
            confidence=0.85,
            page_or_location=page
        )


# Type aliases for convenience
CitationList = List[Citation]
