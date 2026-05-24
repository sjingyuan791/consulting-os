"""
Document Management Page - RAG ドキュメント管理
Upload, index, and search documents for AI-powered retrieval.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import json

# Page config
st.set_page_config(
    page_title="ドキュメント管理 | Consulting OS",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

from core.sidebar import render_sidebar
from core.style_utils import load_custom_css

load_custom_css()
render_sidebar()

# Check authentication
if "user" not in st.session_state or not st.session_state.user:
    st.warning("ログインしてください")
    st.stop()

if "selected_client" not in st.session_state or not st.session_state.selected_client:
    st.info("ホーム画面から顧客を選択してください")
    st.stop()

client = st.session_state.selected_client
client_id = client.get("id")

# Import RAG modules
try:
    from core.rag_service import RAGService, get_rag_service
    from core.rag_indexer import SourceType
    rag_available = True
except ImportError as e:
    rag_available = False
    st.error(f"RAGモジュールのインポートに失敗しました: {e}")

# ==========================================
# Header
# ==========================================
st.title("📚 ドキュメント管理")
st.caption(f"顧客: **{client.get('name', 'Unknown')}**")

# ==========================================
# Tabs
# ==========================================
tab_upload, tab_manage, tab_search = st.tabs([
    "📤 アップロード",
    "📋 管理",
    "🔍 検索テスト"
])

# ==========================================
# Tab 1: Upload Documents
# ==========================================
with tab_upload:
    st.subheader("ドキュメントのアップロード")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        upload_type = st.selectbox(
            "ドキュメントタイプ",
            options=["テキスト入力", "ファイルアップロード"],
            key="upload_type"
        )
        
        if upload_type == "テキスト入力":
            doc_title = st.text_input("ドキュメント名", placeholder="例: 2024年度経営方針")
            doc_content = st.text_area(
                "内容",
                height=300,
                placeholder="ドキュメントの内容を入力してください...\n\n会議メモ、方針書、市場調査レポートなど、AIに参照させたい情報を登録できます。"
            )
            source_type = "manual"
            
        else:  # ファイルアップロード
            uploaded_file = st.file_uploader(
                "ファイルを選択",
                type=["txt", "csv", "md", "pdf"],
                help="TXT, CSV, MD, PDF形式に対応"
            )
            
            if uploaded_file:
                doc_title = uploaded_file.name
                
                # Determine source type based on extension
                if uploaded_file.name.lower().endswith('.pdf'):
                    source_type = "pdf"
                    try:
                        # Reset pointer just in case
                        uploaded_file.seek(0)
                        doc_content = uploaded_file.read() # Read as bytes
                        
                        st.info(f"📄 PDFファイルが選択されました ({len(doc_content) / 1024:.1f} KB)")
                        
                    except Exception as e:
                        st.error(f"ファイル読み込みエラー: {e}")
                        doc_content = None
                        
                else:
                    # Text based files
                    if uploaded_file.name.lower().endswith('.csv'):
                        source_type = "csv"
                    else:
                        source_type = "text"
                        
                    # Read content based on file type
                    try:
                        content_bytes = uploaded_file.read()
                        
                        # Try multiple encodings
                        for encoding in ['utf-8', 'shift-jis', 'cp932', 'euc-jp']:
                            try:
                                doc_content = content_bytes.decode(encoding)
                                break
                            except UnicodeDecodeError:
                                continue
                        else:
                            doc_content = content_bytes.decode('utf-8', errors='replace')
                        
                        st.text_area(
                            "プレビュー",
                            doc_content[:2000] + ("..." if len(doc_content) > 2000 else ""),
                            height=200,
                            disabled=True
                        )
                            
                    except Exception as e:
                        st.error(f"ファイル読み込みエラー: {e}")
                        doc_content = None
                        doc_title = None
                        source_type = None
            else:
                doc_content = None
                doc_title = None
                source_type = None
    
    with col2:
        st.markdown("### インデックス設定")
        
        chunk_size = st.slider(
            "チャンクサイズ",
            min_value=500,
            max_value=2000,
            value=1000,
            step=100,
            help="テキストを分割する文字数"
        )
        
        chunk_overlap = st.slider(
            "オーバーラップ",
            min_value=0,
            max_value=500,
            value=200,
            step=50,
            help="チャンク間の重複文字数"
        )
        
        st.markdown("---")
        st.markdown("### メタデータ")
        
        doc_category = st.selectbox(
            "カテゴリ",
            ["経営方針", "財務データ", "市場調査", "会議メモ", "その他"]
        )
        
        doc_tags = st.text_input(
            "タグ（カンマ区切り）",
            placeholder="例: 2024, 重要, 戦略"
        )
    
    # Upload button
    st.markdown("---")
    
    if st.button("📥 インデックスに追加", type="primary", use_container_width=True):
        if not rag_available:
            st.error("RAGモジュールが利用できません")
        elif not doc_title or not doc_content:
            st.error("ドキュメント名と内容を入力してください")
        else:
            with st.spinner("インデックス中..."):
                try:
                    service = get_rag_service()
                    
                    # Prepare metadata
                    metadata = {
                        "category": doc_category,
                        "tags": [t.strip() for t in doc_tags.split(",") if t.strip()],
                        "indexed_at": datetime.now().isoformat()
                    }
                    
                    # Index document
                    if source_type == "pdf":
                        result = service.index_pdf(
                            client_id=client_id,
                            pdf_file=doc_content, # bytes
                            filename=doc_title,
                            metadata=metadata
                        )
                    else:
                        result = service.index_document(
                            client_id=client_id,
                            content=doc_content, # string
                            source_type=source_type,
                            source_name=doc_title,
                            metadata=metadata
                        )
                    
                    if result.success:
                        st.success(f"✅ インデックス完了: {result.chunks_created} チャンク作成")
                        st.balloons()
                    else:
                        st.error(f"❌ エラー: {result.error}")
                        
                except Exception as e:
                    st.error(f"インデックスエラー: {e}")

# ==========================================
# Tab 2: Manage Documents
# ==========================================
with tab_manage:
    st.subheader("インデックス済みドキュメント")
    
    if rag_available:
        try:
            service = get_rag_service()
            docs = service.list_documents(client_id)
            total_chunks = service.get_document_count(client_id)
            
            # Stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("ドキュメント数", len(docs))
            with col2:
                st.metric("総チャンク数", total_chunks)
            with col3:
                avg_chunks = total_chunks / len(docs) if docs else 0
                st.metric("平均チャンク/ドキュメント", f"{avg_chunks:.1f}")
            
            st.markdown("---")
            
            if docs:
                # Document list
                for doc in docs:
                    with st.expander(f"📄 {doc['source_name']} ({doc['chunk_count']} chunks)"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.markdown(f"**タイプ:** {doc['source_type']}")
                            st.markdown(f"**登録日:** {doc['created_at'][:10]}")
                        
                        with col2:
                            if st.button(
                                "🗑️ 削除",
                                key=f"delete_{doc['source_name']}",
                                type="secondary"
                            ):
                                with st.spinner("削除中..."):
                                    deleted = service.delete_document(client_id, doc['source_name'])
                                    st.success(f"削除完了: {deleted} チャンク")
                                    st.rerun()
            else:
                st.info("インデックス済みドキュメントはありません")
                
        except Exception as e:
            st.error(f"ドキュメント一覧の取得に失敗: {e}")
    else:
        st.warning("RAGモジュールが利用できません")

# ==========================================
# Tab 3: Search Test
# ==========================================
with tab_search:
    st.subheader("検索テスト")
    
    query = st.text_input(
        "検索クエリ",
        placeholder="例: 来期の売上目標について教えてください",
        key="search_query"
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        search_count = st.slider("結果数", 1, 10, 5)
    with col2:
        search_threshold = st.slider("類似度閾値", 0.0, 1.0, 0.3, 0.1)
    with col3:
        use_reranking = st.checkbox("リランキング使用", value=True)
    
    if st.button("🔍 検索", type="primary"):
        if not query:
            st.warning("検索クエリを入力してください")
        elif not rag_available:
            st.error("RAGモジュールが利用できません")
        else:
            with st.spinner("検索中..."):
                try:
                    from core.rag_retriever import RAGRetriever, SearchConfig
                    
                    config = SearchConfig(
                        match_threshold=search_threshold,
                        match_count=search_count,
                        enable_reranking=use_reranking
                    )
                    
                    retriever = RAGRetriever(config)
                    result = retriever.search(query, client_id, match_count=search_count)
                    
                    # Show results
                    st.markdown(f"**検索時間:** {result.search_time_ms:.1f}ms | **戦略:** {result.strategy_used.value}")
                    
                    if result.results:
                        for i, res in enumerate(result.results, 1):
                            with st.expander(
                                f"#{i} {res.source_name} (類似度: {res.similarity:.2%})",
                                expanded=(i == 1)
                            ):
                                st.markdown(res.content)
                                st.caption(f"タイプ: {res.source_type}")
                    else:
                        st.info("該当するドキュメントが見つかりませんでした")
                        
                except Exception as e:
                    st.error(f"検索エラー: {e}")
    
    st.markdown("---")
    
    # RAG Query Test
    st.subheader("RAG応答テスト")
    
    rag_query = st.text_area(
        "質問",
        placeholder="ドキュメントに基づいて質問してください...",
        height=100,
        key="rag_query"
    )
    
    if st.button("💬 RAG応答生成", type="primary"):
        if not rag_query:
            st.warning("質問を入力してください")
        elif not rag_available:
            st.error("RAGモジュールが利用できません")
        else:
            with st.spinner("回答生成中..."):
                try:
                    service = get_rag_service()
                    response = service.query(client_id, rag_query)
                    
                    # Display response
                    st.markdown("### 回答")
                    st.markdown(response.answer)
                    
                    # Show metadata
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("信頼度", f"{response.confidence_score:.0%}")
                    with col2:
                        context_status = "✅ 使用" if response.context_used else "❌ 未使用"
                        st.metric("コンテキスト", context_status)
                    
                    # Show citations
                    if response.citations:
                        st.markdown("### 参照元")
                        for cite in response.citations:
                            with st.expander(f"📄 {cite.source_name} ({cite.relevance:.0%})"):
                                st.markdown(cite.excerpt)
                    
                    # Show retrieval info
                    if response.retrieval_info:
                        with st.expander("🔧 詳細情報"):
                            st.json(response.retrieval_info)
                            
                except Exception as e:
                    st.error(f"RAG応答エラー: {e}")

# ==========================================
# Sidebar Info
# ==========================================
with st.sidebar:
    st.markdown("### 📚 RAGについて")
    st.markdown("""
    **RAG (Retrieval-Augmented Generation)**
    
    登録したドキュメントをAIが参照して、
    より正確で根拠のある回答を生成します。
    
    **対応形式:**
    - テキスト (TXT, MD)
    - CSV
    
    **推奨ドキュメント:**
    - 経営方針書
    - 財務データ
    - 市場調査レポート
    - 会議議事録
    - 業界レポート
    """)
