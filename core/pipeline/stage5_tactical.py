"""
Stage 5: HOW-Tree Tactical Generator
Generates tactical execution options through deductive HOW tree decomposition.
"""
from typing import Dict, Any, Optional, List
from core.pipeline.base_engine import AIEngine, EngineConfig
from core.schemas.pipeline_stages import (
    Stage5Output, TacticalOptionSet, TacticalOption,
    HOWTree, HOWNode, PrioritizedAction, Milestone
)
import json
from datetime import datetime, timedelta


class TacticalGeneratorEngine(AIEngine[Dict[str, Any], Stage5Output]):
    """
    HOW-Tree Tactical Generator - Stage 5 of the consulting pipeline.
    
    Generates concrete tactical options and action plans through
    deductive decomposition of strategic objectives.
    """
    
    STAGE_NUMBER = 5
    STAGE_NAME = "HOW-Tree Tactical Generator"
    
    async def process(
        self,
        input_data: Dict[str, Any],
        previous_output: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Stage5Output:
        """
        Generate tactical options and HOW trees.
        """
        # Extract strategy from Stage 4
        stage4_output = previous_output or input_data.get("stage4_output", {})
        corporate_strategy = stage4_output.get("corporate_strategy", {})
        functional_strategies = stage4_output.get("functional_strategies", [])
        
        # Generate tactical option sets for each functional strategy
        tactical_option_sets = []
        for func_strategy in functional_strategies[:4]:
            option_set = self._generate_tactical_options(func_strategy)
            tactical_option_sets.append(option_set)
        
        # Generate HOW trees for key objectives
        how_trees = []
        for i, func_strategy in enumerate(functional_strategies[:3]):
            for objective in func_strategy.get("objectives", [])[:2]:
                how_tree = self._generate_how_tree(
                    objective,
                    func_strategy.get("function_name_ja", ""),
                    i
                )
                how_trees.append(how_tree)
        
        # Generate prioritized actions
        all_actions = self._extract_and_prioritize_actions(
            tactical_option_sets, how_trees
        )
        
        # Generate milestones
        milestones = self._generate_milestones(all_actions)
        
        # Identify quick wins
        quick_wins = [a.action for a in all_actions if a.quickwin][:5]
        
        # Generate implementation phases
        phases = self._generate_phases(all_actions)
        
        return Stage5Output(
            tactical_option_sets=tactical_option_sets,
            how_trees=how_trees,
            prioritized_actions=all_actions,
            milestones=milestones,
            quick_wins=quick_wins,
            implementation_phases=phases,
            confidence_score=0.80
        )
    
    def _generate_tactical_options(
        self,
        func_strategy: Dict
    ) -> TacticalOptionSet:
        """Generate tactical options for a functional strategy."""
        function = func_strategy.get("function", "operations")
        function_name = func_strategy.get("function_name_ja", "機能戦略")
        initiatives = func_strategy.get("key_initiatives", [])
        
        options = []
        
        # Generate 2-3 options per strategy
        option_configs = [
            ("保守的アプローチ", 0.6, 0.5, "low", "6ヶ月"),
            ("バランスアプローチ", 1.0, 0.7, "medium", "12ヶ月"),
            ("積極的アプローチ", 1.5, 0.9, "high", "18ヶ月")
        ]
        
        for i, (name, cost_mult, impact, difficulty, time) in enumerate(option_configs):
            base_initiative = initiatives[0] if initiatives else "改善施策"
            
            options.append(TacticalOption(
                id=f"opt_{function}_{i+1}",
                name=f"{function_name} - {name}",
                description=f"{base_initiative}を{name}で推進",
                pros=[
                    "リスクが限定的" if i == 0 else "バランスの取れた投資対効果" if i == 1 else "最大のインパクト",
                    "既存リソースで対応可能" if i == 0 else "段階的なリソース投入" if i == 1 else "抜本的な変革",
                ],
                cons=[
                    "成果が限定的" if i == 0 else "中程度の投資が必要" if i == 1 else "高い投資とリスク",
                    "競合に遅れる可能性" if i == 0 else "実行の複雑さ" if i == 1 else "組織への負荷",
                ],
                estimated_cost=100 * cost_mult,  # 百万円単位
                estimated_impact=impact,
                implementation_difficulty=difficulty,
                time_to_value=time,
                dependencies=[]
            ))
        
        # Recommend balanced approach by default
        return TacticalOptionSet(
            strategy_link=f"func_{function}",
            strategy_name=function_name,
            options=options,
            recommended_option=f"opt_{function}_2",
            recommendation_rationale="リスクと成果のバランスが最適であり、組織の実行能力に適合"
        )
    
    def _generate_how_tree(
        self,
        objective: str,
        function_name: str,
        index: int
    ) -> HOWTree:
        """Generate HOW tree for a strategic objective."""
        tree_id = f"how_tree_{index}"
        nodes = []
        
        # Root node (Level 0)
        root_id = f"{tree_id}_root"
        nodes.append(HOWNode(
            id=root_id,
            parent_id=None,
            level=0,
            description=objective,
            owner="責任者",
            deadline="Year 1 End",
            kpi="成果指標",
            children_ids=[]
        ))
        
        # Level 1 nodes (HOW to achieve root)
        level1_descriptions = [
            "体制・組織の整備",
            "プロセス・仕組みの構築",
            "ツール・システムの導入",
            "人材・スキルの強化"
        ]
        
        level1_ids = []
        for i, desc in enumerate(level1_descriptions[:3]):
            node_id = f"{tree_id}_L1_{i}"
            level1_ids.append(node_id)
            nodes.append(HOWNode(
                id=node_id,
                parent_id=root_id,
                level=1,
                description=f"{function_name}: {desc}",
                owner=f"{function_name}責任者",
                deadline=f"Q{i+2}",
                children_ids=[]
            ))
        
        # Update root's children
        nodes[0].children_ids = level1_ids
        
        # Level 2 nodes (concrete actions)
        action_templates = {
            "体制・組織の整備": ["担当チーム編成", "役割・権限の明確化", "会議体設置"],
            "プロセス・仕組みの構築": ["業務フロー設計", "標準手順書作成", "品質基準策定"],
            "ツール・システムの導入": ["要件定義", "ツール選定", "導入・研修"],
            "人材・スキルの強化": ["スキル評価", "研修計画策定", "OJT実施"]
        }
        
        for l1_idx, l1_id in enumerate(level1_ids):
            l1_desc = level1_descriptions[l1_idx]
            actions = action_templates.get(l1_desc, ["アクション1", "アクション2"])
            
            level2_ids = []
            for j, action in enumerate(actions[:2]):
                node_id = f"{tree_id}_L2_{l1_idx}_{j}"
                level2_ids.append(node_id)
                nodes.append(HOWNode(
                    id=node_id,
                    parent_id=l1_id,
                    level=2,
                    description=action,
                    owner="担当者",
                    deadline=f"Q{l1_idx + 1} Week {(j+1)*4}",
                    children_ids=[]
                ))
            
            # Update L1's children
            for node in nodes:
                if node.id == l1_id:
                    node.children_ids = level2_ids
        
        return HOWTree(
            tree_id=tree_id,
            root_objective=objective,
            strategy_link=f"func_{function_name}",
            nodes=nodes
        )
    
    def _extract_and_prioritize_actions(
        self,
        option_sets: List[TacticalOptionSet],
        how_trees: List[HOWTree]
    ) -> List[PrioritizedAction]:
        """Extract and prioritize actions from options and HOW trees."""
        actions = []
        action_id = 0
        
        # Extract from recommended options
        for opt_set in option_sets:
            rec_opt = next(
                (o for o in opt_set.options if o.id == opt_set.recommended_option),
                opt_set.options[1] if len(opt_set.options) > 1 else opt_set.options[0]
            )
            
            action_id += 1
            impact = rec_opt.estimated_impact
            effort = 0.3 if rec_opt.implementation_difficulty == "low" else 0.6 if rec_opt.implementation_difficulty == "medium" else 0.9
            priority = impact / (effort + 0.1)  # Avoid division by zero
            
            actions.append(PrioritizedAction(
                id=f"action_{action_id}",
                action=rec_opt.description,
                priority_score=priority,
                impact=impact,
                effort=effort,
                quickwin=impact > 0.5 and effort < 0.5,
                owner=opt_set.strategy_name,
                timeline=rec_opt.time_to_value
            ))
        
        # Extract leaf nodes from HOW trees
        for tree in how_trees:
            leaf_nodes = tree.get_leaf_actions()
            for leaf in leaf_nodes[:3]:
                action_id += 1
                actions.append(PrioritizedAction(
                    id=f"action_{action_id}",
                    action=leaf.description,
                    priority_score=0.7,
                    impact=0.6,
                    effort=0.4,
                    quickwin=leaf.level > 1,
                    owner=leaf.owner,
                    timeline=leaf.deadline or "Q1"
                ))
        
        # Sort by priority
        actions.sort(key=lambda x: x.priority_score, reverse=True)
        
        return actions[:15]  # Top 15 actions
    
    def _generate_milestones(
        self,
        actions: List[PrioritizedAction]
    ) -> List[Milestone]:
        """Generate implementation milestones."""
        base_date = datetime.now()
        milestones = []
        
        milestone_configs = [
            ("キックオフ完了", 30, ["体制構築", "キックオフ会議開催"]),
            ("クイックウィン達成", 90, ["早期成果創出", "成功事例共有"]),
            ("第1フェーズ完了", 180, ["主要施策の実行完了", "中間レビュー実施"]),
            ("第2フェーズ開始", 210, ["次フェーズ計画確定", "リソース再配置"]),
            ("全体完了", 365, ["全施策の完了", "最終評価実施"])
        ]
        
        for i, (name, days, deliverables) in enumerate(milestone_configs):
            target_date = base_date + timedelta(days=days)
            milestones.append(Milestone(
                id=f"milestone_{i+1}",
                name=name,
                target_date=target_date.strftime("%Y-%m-%d"),
                deliverables=deliverables,
                dependencies=[f"milestone_{i}"] if i > 0 else [],
                owner="プロジェクトマネージャー"
            ))
        
        return milestones
    
    def _generate_phases(
        self,
        actions: List[PrioritizedAction]
    ) -> List[Dict[str, Any]]:
        """Generate implementation phases."""
        quick_wins = [a for a in actions if a.quickwin]
        main_actions = [a for a in actions if not a.quickwin]
        
        return [
            {
                "phase": 1,
                "name": "クイックウィン & 基盤構築",
                "duration": "Month 1-3",
                "focus": "早期成果の創出と実行基盤の整備",
                "actions": [a.action for a in quick_wins[:5]],
                "resource_allocation": 0.3
            },
            {
                "phase": 2,
                "name": "本格展開",
                "duration": "Month 4-9",
                "focus": "主要施策の本格的な実行",
                "actions": [a.action for a in main_actions[:5]],
                "resource_allocation": 0.5
            },
            {
                "phase": 3,
                "name": "定着 & 最適化",
                "duration": "Month 10-12",
                "focus": "成果の定着と継続的改善",
                "actions": [a.action for a in main_actions[5:8]],
                "resource_allocation": 0.2
            }
        ]
    
    def build_prompt(
        self,
        input_data: Dict[str, Any],
        previous_output: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build prompt for AI-enhanced tactical generation."""
        return f"""戦略を具体的な施策に落とし込んでください。

## 戦略設計結果
{json.dumps(previous_output, ensure_ascii=False, indent=2) if previous_output else '{}'}

以下を生成してください：
1. 戦略ごとの施策オプション（3案）
2. HOW-Tree（目標の具体化）
3. 優先順位付けされたアクションリスト
4. マイルストーン計画"""


# Factory function
def create_tactical_generator(config: Optional[EngineConfig] = None) -> TacticalGeneratorEngine:
    """Create and return a Tactical Generator Engine instance."""
    return TacticalGeneratorEngine(config)
