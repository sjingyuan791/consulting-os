import streamlit as st
import json
import pandas as pd
from typing import Any, Dict
import graphviz
import time

from core.auth import check_auth
from core.llm_client import run_strategy_chat
from core.repos.strategy_run_repo import StrategyRunRepo
from core.schemas.strategy import StrategyResponse, StrategyOptionItem
from core.schemas.common import StrategyModuleSchema # Helper for reconstructing models if needed
from core.style_utils import load_custom_css
from core.supabase_client import get_supabase_client

# Graphviz Helper
def render_issue_tree(node, dot=None, parent_id=None):
    if dot is None:
        dot = graphviz.Digraph()
        dot.attr(rankdir='LR')
    
    # New Schema: IssueNode (dict with label/children)
    if isinstance(node, dict) and "label" in node:
        label = node.get("label", "Issue")
        children = node.get("children", []) or []
        
        node_id = f"node_{hash(label)}{hash(str(children))}"[-8:] 
        dot.node(node_id, label, shape='box')
        
        if parent_id:
            dot.edge(parent_id, node_id)
            
        for child in children:
            render_issue_tree(child, dot, node_id)
            
    # Legacy: Dict[str, Any] (label as key)
    elif isinstance(node, dict):
        for key, value in node.items():
            node_hash = str(hash(key)) + str(hash(str(value))) # Simple collision avoidance
            node_id = f"node_{node_hash}"[-8:] 
            
            dot.node(node_id, key, shape='box')
            if parent_id:
                dot.edge(parent_id, node_id)
            render_issue_tree(value, dot, node_id)
            
    # Legacy: List (children)
    elif isinstance(node, list):
        for item in node:
            # If item is IssueNode-like dict
            if isinstance(item, dict) and "label" in item:
                render_issue_tree(item, dot, parent_id)
            else:
                # String leaf
                item_id = f"item_{hash(str(item))}"[-8:]
                dot.node(item_id, str(item), shape='oval', style='dashed')
                if parent_id:
                    dot.edge(parent_id, item_id)
    else:
        # String leaf
        leaf_id = f"leaf_{hash(str(node))}"[-8:]
        dot.node(leaf_id, str(node), shape='plain')
        if parent_id:
            dot.edge(parent_id, leaf_id)
            
    return dot
    
def handle_chat_submit(prompt, thread_id, repo, final_package, history):
    """Helper to process chat submission from input or buttons."""
    # 1. Optimistically save user message
    repo.add_message(thread_id, "user", prompt)

    # 2. Call AI
    with st.spinner("AIコンサルタントが思考中..."):
        # Prepare base context
        context_data = {"base_data": final_package}
        
        # --- RAG Context Injection ---
        try:
            from core.rag_service import get_rag_service
            
            client_id = final_package.get("meta", {}).get("client_id", "")
            if client_id:
                rag_service = get_rag_service()
                rag_context = rag_service.get_context(
                    client_id=client_id,
                    query=prompt,
                    max_tokens=2000
                )
                if rag_context:
                    context_data["rag_documents"] = rag_context
        except Exception:
            pass  # RAG not available or failed
        
        context_json = json.dumps(context_data, default=str)[:10000]
        
        # API History format
        api_hist = [{"role": m["role"], "content": json.dumps(m["content"]) if isinstance(m["content"], dict) else m["content"]} for m in history]
        api_hist.append({"role": "user", "content": prompt})
        
        try:
            response_obj = run_strategy_chat(api_hist, context_json)
            
            # Save assistant message
            repo.add_message(thread_id, "assistant", response_obj.model_dump())
            st.rerun()
            
        except Exception as e:
            import logging
            logging.error(f"Strategy chat error: {type(e).__name__}")
            st.error("AI処理中にエラーが発生しました。しばらくしてから再試行してください。")

def app():
    load_custom_css()
    from core.sidebar import render_sidebar
    render_sidebar()
    
    if not check_auth():
        st.warning("ログインしてください。")
        return
    
    st.set_page_config(layout="wide",
    initial_sidebar_state="expanded")

    client_id = st.session_state.get("client_id")
    if not client_id:
        st.warning("ホーム画面からクライアントを選択してください。")
        st.stop()
    user_id = st.session_state.user.id

    # --- 1. Load Persistence Layer ---
    repo = StrategyRunRepo()
    
    # Get latest Strategy Run (The Context)
    current_run = repo.get_current_strategy_run(client_id)
    
    if not current_run:
        st.info("戦略データが見つかりません。「分析・戦略立案」ページで分析を実行してください。")
        return

    # Extract Context from Run
    final_package = current_run.get("final_strategy_package_json", {})
    
    # Load Chat Thread
    try:
        thread_id = repo.get_or_create_thread(current_run['id'], created_by=user_id)
        history = repo.get_thread_history(thread_id)
    except Exception as e:
        st.error(f"チャット履歴の読み込みに失敗しました: {e}")
        return

    st.title("AI戦略パートナー (Strategy Discussion)")
    st.caption(f"Context: Strategy Run {current_run['id'][:8]}...")

    # Layout: Left = Mental Model (State), Right = Chat (Discussion)
    col_state, col_chat = st.columns([1.2, 2])
    
    # --- Retrieve Latest AI State ---
    # We look for the last message from assistant to populate the "Current Thinking"
    latest_ai_state = {}
    for msg in reversed(history):
        if msg["role"] == "assistant" and isinstance(msg["content"], dict):
            latest_ai_state = msg["content"]
            break
    
    if not latest_ai_state:
        # Fallback to initial package data
        latest_ai_state = {
            "issue_definition": "Initial Scope",
            "hypotheses": [],
            "issue_tree": final_package.get("root_cause_diagnosis", {}).get("issue_tree", None)
        }

    with col_state:
        tab_reasoning, tab_options = st.tabs(["思考モデル (Mental Model)", "戦略オプション (Options)"])
        
        with tab_reasoning:
            st.info("AIは会話を通じて、このモデル（論点・仮説）を更新し続けます。")
            
            with st.container(border=True):
                st.markdown(f"**論点定義**: {latest_ai_state.get('issue_definition', 'Not defined')}")
                
                st.markdown("**現在の有力仮説**:")
                hyps = latest_ai_state.get("hypotheses", [])
                if hyps:
                    for h in hyps:
                        st.markdown(f"- {h}")
                else:
                    st.caption("No hypotheses yet.")

                st.markdown(f"**確信度**: {latest_ai_state.get('confidence', 0.5):.0%}")

            st.markdown("#### 論点ツリー (Issue Tree)")
            tree_data = latest_ai_state.get("issue_tree")
            if tree_data:
                try:
                    graph = render_issue_tree(tree_data)
                    st.graphviz_chart(graph)
                except Exception:
                    st.caption("Complex tree structure - visualization skipped.")
            else:
                 st.caption("No issue tree available.")

        with tab_options:
            st.caption("現在提案されている戦略案です。会話を通じてこれを修正できます。")
            options_data = final_package.get("strategy_options", {}).get("options", [])
            
            if not options_data:
                st.warning("戦略オプションが見つかりません。")
            else:
                for opt in options_data:
                    with st.expander(f"**{opt.get('name', 'Option')}**", expanded=False):
                        st.markdown(f"_{opt.get('description', '')}_")
                        st.markdown("**メリット (Pros):**")
                        for p in opt.get("pros", []):
                            st.markdown(f"- {p}")
                        st.markdown("**デメリット (Cons):**")
                        for c in opt.get("cons", []):
                            st.markdown(f"- {c}")
                        
                        st.markdown(f"**投資額 (Investment)**: {opt.get('investment_required', 'N/A')}")
                        st.markdown(f"**想定効果 (Impact)**: {opt.get('estimated_impact', 'N/A')}")


    with col_chat:
        st.markdown("### 💬 戦略ダイアログ")
        
        # Display History
        for msg in history:
            role = msg["role"]
            content = msg["content"]
            
            with st.chat_message(role):
                if role == "user":
                    st.write(content)
                else:
                    # Assistant (Structured)
                    if isinstance(content, dict):
                        # Display the conversational part ONLY
                        chat_text = content.get("chat_response", "")
                        if not chat_text:
                            # Fallback for old messages or missing field
                            chat_text = content.get("preliminary_insight", "分析を更新しました。")
                        st.write(chat_text)
                        
                        # --- Strategy Revision Proposal ---
                        revised_opts = content.get("revised_strategy_options")
                        revision_reason = content.get("revision_reason")
                        
                        if revised_opts:
                            with st.status("🔄 戦略オプションの修正提案があります", expanded=True):
                                st.write(f"**理由:** {revision_reason}")
                                st.json(revised_opts, expanded=False)
                                
                                if st.button("この修正案で戦略を更新する (New Version)", key=f"btn_update_{msg.get('created_at', 'now')}"):
                                    try:
                                        from core.strategy_refinement_service import refinement_service
                                        
                                        new_run_id = refinement_service.commit_refinement(
                                            base_run_id=current_run['id'],
                                            refined_options=revised_opts,
                                            reasoning_state={
                                                "issue_definition": content.get("issue_definition"),
                                                "hypotheses": content.get("hypotheses"),
                                                "issue_tree": content.get("issue_tree"),
                                                "confidence": content.get("confidence")
                                            },
                                            refinement_reason=revision_reason,
                                            user_id=user_id,
                                            origin_chat_id=msg.get("id")
                                        )
                                        st.success(f"新しい戦略バージョンを作成しました！ (Run ID: {new_run_id})")
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"更新に失敗しました: {e}")
                    else:
                        st.write(content)

        # Chat Input
        if prompt := st.chat_input("仮説に対する反論、質問、新しい情報の提供..."):
            handle_conversation_turn(prompt, thread_id, repo, final_package, history, latest_ai_state)

def handle_conversation_turn(prompt, thread_id, repo, final_package, history, current_state):
    """
    Handles a turn of conversation, injecting the current reasoning state.
    """
    # 1. Save User Message
    repo.add_message(thread_id, "user", prompt)
    
    # 2. Prepare Context with Reasoning State
    # We combine the base Strategy Package with the dynamic 'current_state' from the last turn
    # This ensures the AI 'remembers' its own issue tree and hypotheses.
    
    dynamic_context = {
        "base_data": final_package,
        "current_reasoning_state": current_state # {issue_tree, hypotheses, etc.}
    }
    
    # --- Monitoring & Learning Feedback Injection (Optimized: Single Query) ---
    sb = get_supabase_client()
    run_id = final_package.get("meta", {}).get("run_id", "")
    parent_id = final_package.get("meta", {}).get("parent_run_id")
    
    try:
        # Optimized: Fetch monitoring and learning data in parallel concept
        # but sequential for simplicity - both are single queries now
        
        # 1. Get monitoring feedback via single join-like query
        if run_id:
            exec_res = sb.table("strategy_execution_runs").select(
                "id, monitoring_runs(gap_analysis_json)"
            ).eq("strategy_run_id", run_id).order("created_at", desc=True).limit(1).execute()
            
            if exec_res.data and exec_res.data[0].get("monitoring_runs"):
                mon_data = exec_res.data[0]["monitoring_runs"]
                if isinstance(mon_data, list) and mon_data:
                    feedback = mon_data[0].get("gap_analysis_json", {}).get("strategy_feedback_context")
                    if feedback:
                        dynamic_context["monitoring_feedback"] = feedback
                        prompt = f"{prompt}\n\n{feedback}"
        
        # 2. Get learning hypotheses (if parent exists)
        if parent_id:
            learning_res = sb.table("strategy_learning_records").select(
                "generated_hypotheses_json"
            ).eq("strategy_run_id", parent_id).order("created_at", desc=True).limit(1).execute()
            
            if learning_res.data:
                hyps = learning_res.data[0].get("generated_hypotheses_json", [])
                if hyps:
                    dynamic_context["learned_hypotheses"] = hyps
                    prompt = f"{prompt}\n\n[System Insight] Derived from previous cycle:\n" + "\n".join([f"- {h}" for h in hyps])
                    
    except Exception as e:
        import logging
        logging.warning(f"Failed to fetch context data: {type(e).__name__}")
    
    # --- RAG Context Injection ---
    try:
        from core.rag_service import get_rag_service
        
        client_id = final_package.get("meta", {}).get("client_id", "")
        if client_id:
            rag_service = get_rag_service()
            
            # Retrieve relevant documents based on user query
            rag_context = rag_service.get_context(
                client_id=client_id,
                query=prompt,
                max_tokens=2000
            )
            
            if rag_context:
                dynamic_context["rag_documents"] = rag_context
                
                # Get citations for transparency
                citations = rag_service.retriever.get_sources_for_response(prompt, client_id)
                if citations:
                    dynamic_context["rag_citations"] = citations
                    
    except ImportError:
        pass  # RAG not available
    except Exception as e:
        import logging
        logging.warning(f"RAG context retrieval failed: {type(e).__name__}")
        
    context_json = json.dumps(dynamic_context, default=str)[:15000] # Limit token usage
    
    # 3. Call AI
    with st.spinner("AIパートナーが思考モデルを更新中..."):
        # API Component
        api_hist = [{"role": m["role"], "content": json.dumps(m["content"]) if isinstance(m["content"], dict) else m["content"]} for m in history]
        api_hist.append({"role": "user", "content": prompt})
        
        try:
            response_obj = run_strategy_chat(api_hist, context_json)
            
            # Save Assistant Message (Structured)
            repo.add_message(thread_id, "assistant", response_obj.model_dump())
            st.rerun()
            
        except Exception as e:
            import logging
            logging.error(f"Strategy chat error: {type(e).__name__}")
            st.error("AIパートナーとの通信に失敗しました。しばらくしてから再試行してください。")

if __name__ == "__main__":
    app()
