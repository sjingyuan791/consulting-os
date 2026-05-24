"""
Mid-Term Management Plan Narrative Generator.
中期経営計画書のナラティブ（全文レポート）生成モジュール。

構造化JSONデータからプロフェッショナルなコンサルティングレポート形式の
テキストを生成する。
"""
from typing import Optional
from datetime import datetime

from core.schemas.midterm_plan_schema import (
    MidtermPlanDocument, LogicalDependencyMap, SECTION_DEFINITIONS
)


class MidtermPlanNarrative:
    """中期経営計画書のナラティブ生成器"""

    def __init__(self, document: MidtermPlanDocument):
        self.document = document

    def generate_full_markdown(self) -> str:
        """全文Markdownレポートを生成"""
        lines = []

        # Title
        lines.append(f"# 中期経営計画書")
        lines.append(f"")
        lines.append(f"**作成日**: {self.document.created_at[:10]}")
        lines.append(f"**計画期間**: {self.document.plan_period}")
        if self.document.client_id:
            lines.append(f"**クライアント**: {self.document.client_id[:8]}...")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

        # Table of Contents
        lines.append(f"## 目次")
        lines.append(f"")
        for sec_def in SECTION_DEFINITIONS:
            lines.append(f"{sec_def['id']}. [{sec_def['title']}](#{sec_def['id']}-{sec_def['title_en'].lower().replace(' ', '-')})")
        lines.append(f"")
        lines.append(f"---")
        lines.append(f"")

        # Sections
        for section in self.document.sections:
            # Section header
            sec_def = SECTION_DEFINITIONS[section.section_id - 1]
            lines.append(f"<a id=\"{sec_def['id']}-{sec_def['title_en'].lower().replace(' ', '-')}\"></a>")
            lines.append(f"")

            # Reference note
            if section.references:
                ref_titles = []
                for ref_id in section.references:
                    ref_def = SECTION_DEFINITIONS[ref_id - 1]
                    ref_titles.append(f"セクション{ref_id}「{ref_def['title']}」")
                lines.append(f"> **参照**: {', '.join(ref_titles)}")
                lines.append(f"")

            # Narrative content
            lines.append(section.narrative)
            lines.append(f"")
            lines.append(f"---")
            lines.append(f"")

        # Dependency Map
        lines.append(f"## 付録: セクション間論理依存マップ")
        lines.append(f"")
        if self.document.dependency_map:
            lines.append(f"```mermaid")
            lines.append(self.document.dependency_map.to_mermaid())
            lines.append(f"```")
        lines.append(f"")

        return "\n".join(lines)

    def generate_executive_summary(self) -> str:
        """エグゼクティブサマリーを生成"""
        lines = []
        lines.append("# エグゼクティブサマリー")
        lines.append("")

        # Extract key points from each section
        for section in self.document.sections:
            narrative_preview = section.narrative[:200].strip()
            # Skip the markdown header
            content_lines = narrative_preview.split("\n")
            content = " ".join(
                l.strip() for l in content_lines
                if l.strip() and not l.strip().startswith("#")
            )[:150]
            if content:
                lines.append(f"**{section.section_id}. {section.section_title}**: {content}...")
                lines.append("")

        return "\n".join(lines)

    def generate_json_output(self) -> dict:
        """全セクションのJSON出力を生成"""
        return {
            "document_id": self.document.document_id,
            "created_at": self.document.created_at,
            "plan_period": self.document.plan_period,
            "sections": [
                {
                    "section_id": s.section_id,
                    "section_title": s.section_title,
                    "section_title_en": s.section_title_en,
                    "references": s.references,
                    "data": s.data
                }
                for s in self.document.sections
            ],
            "dependency_map": (
                self.document.dependency_map.model_dump()
                if self.document.dependency_map else None
            )
        }


def generate_midterm_plan_report(document: MidtermPlanDocument) -> dict:
    """
    中期経営計画書の3形式出力を生成するファサード関数。
    
    Returns:
        {
            "markdown": 全文Markdownレポート,
            "json": 構造化JSON,
            "executive_summary": エグゼクティブサマリー,
            "dependency_mermaid": 依存マップMermaid
        }
    """
    narrator = MidtermPlanNarrative(document)
    return {
        "markdown": narrator.generate_full_markdown(),
        "json": narrator.generate_json_output(),
        "executive_summary": narrator.generate_executive_summary(),
        "dependency_mermaid": (
            document.dependency_map.to_mermaid()
            if document.dependency_map else ""
        )
    }
