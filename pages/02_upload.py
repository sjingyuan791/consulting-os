"""
02_upload.py — STEP 1: 財務データ登録コックピット
"""
import streamlit as st
import pandas as pd
import numpy as np
import json
from core.auth import check_auth
from core.normalizers import clean_financial_df, clean_sales_df
from core.quality_gate import check_financial_quality, check_sales_quality
from core.style_utils import load_custom_css
from core.external_data import ExternalDataConnector
from core.supabase_client import get_supabase_client
from core.repos.dataset_repo import DatasetRepo

st.set_page_config(
    page_title="財務データ登録 — Consulting OS",
    page_icon="📥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------------------------------------------ #
#  テンプレート生成
# ------------------------------------------------------------------ #

def create_pl_bs_template():
    """PL/BSテンプレート（CF計算書不要・中小企業向け）単位：百万円"""
    columns = [
        "年度",
        # P/L
        "売上高", "売上原価", "売上総利益", "販売費及び一般管理費",
        "営業利益", "営業外収益", "営業外費用（支払利息含む）",
        "経常利益", "特別損益", "法人税等", "当期純利益", "減価償却費",
        # B/S
        "現金預金", "売掛金", "棚卸資産", "その他流動資産",
        "流動資産合計", "固定資産合計", "資産合計",
        "買掛金", "短期借入金", "その他流動負債",
        "流動負債合計", "長期借入金", "固定負債合計", "純資産合計",
        # その他
        "従業員数",
    ]
    data = [
        [2023, 1000,600,400,280,120,5,15,110,0,30,80,20,
         100,150,80,50,380,400,780,80,100,60,240,300,320,160,20],
        [2024, 1100,660,440,300,140,5,15,130,0,35,95,22,
         120,160,85,55,420,380,800,85,90,65,240,280,305,175,22],
        [2025, 1200,720,480,320,160,5,12,153,0,40,113,24,
         150,170,90,60,470,360,830,90,80,70,240,260,290,200,25],
    ]
    return pd.DataFrame(data, columns=columns).to_csv(index=False).encode("utf-8-sig")


def create_loan_template():
    """借入金一覧テンプレート"""
    columns = [
        "借入先", "当初借入日", "当初借入残高（万円）", "現在の残高（万円）",
        "毎月返済額（万円）", "完済予定日", "金利（%）",
        "融資形態", "借入年数",
    ]
    data = [
        ["A銀行（本店）", "2021-04-01", 5000, 3500, 100, "2026-03-31", 1.5, "証書貸付", 5],
        ["B信用金庫", "2022-07-01", 3000, 2400, 80, "2027-06-30", 2.0, "証書貸付", 5],
        ["日本政策金融公庫", "2023-01-01", 2000, 1800, 50, "2026-12-31", 0.5, "証書貸付", 4],
        ["C銀行（手形貸付）", "2024-10-01", 500, 500, 500, "2024-12-31", 1.8, "手形貸付", 1],
    ]
    notes = pd.DataFrame([["※ 融資形態の選択肢: 証書貸付 / 手形貸付 / 当座貸付 / その他"]], columns=["備考"])
    df = pd.DataFrame(data, columns=columns)
    return df.to_csv(index=False).encode("utf-8-sig")


def create_sales_template(industry: str):
    base_cols = ["年月", "顧客名", "商品・サービス名", "数量", "売上金額（千円）", "原価（千円）", "粗利（千円）"]
    ext = {
        "小売業":   (["店舗名", "来店数", "客単価（円）"],        ["渋谷店", 150, 3300]),
        "製造業":   (["工場名", "ロット番号", "稼働率（%）"],     ["第1工場", "LOT-001", 85]),
        "建設業":   (["現場名", "工期", "原価区分"],               ["東京ビル新築", "6ヶ月", "材料費"]),
        "サービス業":(["担当者", "案件名", "契約種別"],            ["田中", "中期経営計画支援", "顧問契約"]),
    }
    add_cols, add_vals = ext.get(industry, ([], []))
    row = ["2024-04", "山田商事", "製品A", 10, 500, 150, 350] + add_vals
    return pd.DataFrame([row], columns=base_cols + add_cols).to_csv(index=False).encode("utf-8-sig")


# ------------------------------------------------------------------ #
#  UI パーツ
# ------------------------------------------------------------------ #

def render_health_card(title, score, icon, status_text):
    color = "#16a34a" if score >= 80 else "#d97706" if score >= 30 else "#dc2626"
    st.markdown(f"""
        <div style="background:white;border:1px solid #e5e7eb;border-radius:12px;
                    padding:16px;display:flex;align-items:center;gap:16px;
                    box-shadow:0 1px 3px rgba(0,0,0,0.05);">
            <div style="font-size:28px;">{icon}</div>
            <div style="flex:1;">
                <div style="font-size:0.78rem;color:#6b7280;font-weight:600;">{title}</div>
                <div style="font-size:1.4rem;font-weight:800;color:#1f2937;line-height:1.2;">
                    {score}<span style="font-size:0.8rem;color:#9ca3af;">/100</span>
                </div>
            </div>
            <div style="font-size:0.8rem;font-weight:700;color:{color};
                        background:{color}18;padding:4px 10px;border-radius:20px;">
                {status_text}
            </div>
        </div>
    """, unsafe_allow_html=True)


def sanitize_df(d):
    d = d.replace([np.inf, -np.inf], np.nan)
    return d.where(pd.notnull(d), None)


def read_csv_auto(f):
    """Shift-JIS / UTF-8 自動判定で CSV を読む"""
    try:
        return pd.read_csv(f)
    except UnicodeDecodeError:
        f.seek(0)
        return pd.read_csv(f, encoding="shift_jis")


# ------------------------------------------------------------------ #
#  データ確認テーブル
# ------------------------------------------------------------------ #

def render_verification_tables(v_fin):
    """登録済み財務データをPL/BS別に表示"""
    if not v_fin:
        st.info("財務データがまだ登録されていません。")
        return

    data = v_fin.get("normalized_json", [])
    if isinstance(data, dict):
        data = [data]

    all_records = []
    for item in data:
        recs = item.get("records", [])
        all_records.extend(recs)

    if not all_records:
        st.info("登録レコードがありません。")
        return

    df = pd.DataFrame(all_records)

    # --- P/L ---
    pl_cols = ["年度","売上高","売上原価","売上総利益","販売費及び一般管理費",
               "営業利益","営業外収益","営業外費用（支払利息含む）",
               "経常利益","特別損益","法人税等","当期純利益","減価償却費"]
    pl_exist = [c for c in pl_cols if c in df.columns]
    if pl_exist:
        st.markdown("#### 📈 損益計算書（P/L）")
        df_pl = df[pl_exist].copy()
        if "年度" in df_pl.columns:
            df_pl = df_pl.set_index("年度")
        st.dataframe(df_pl.T if len(df_pl) <= 5 else df_pl, use_container_width=True)

    # --- B/S ---
    bs_cols = ["年度","現金預金","売掛金","棚卸資産","その他流動資産",
               "流動資産合計","固定資産合計","資産合計",
               "買掛金","短期借入金","その他流動負債",
               "流動負債合計","長期借入金","固定負債合計","純資産合計"]
    bs_exist = [c for c in bs_cols if c in df.columns]
    if bs_exist:
        st.markdown("#### 🏦 貸借対照表（B/S）")
        df_bs = df[bs_exist].copy()
        if "年度" in df_bs.columns:
            df_bs = df_bs.set_index("年度")
        st.dataframe(df_bs.T if len(df_bs) <= 5 else df_bs, use_container_width=True)

    # --- 全科目 ---
    with st.expander("全科目を表示"):
        st.dataframe(df, use_container_width=True)

    vdate = v_fin.get("created_at", "")[:16]
    fname = v_fin.get("quality_json", {}).get("filename", "")
    st.caption(f"登録日時: {vdate}　ファイル: {fname}")


# ------------------------------------------------------------------ #
#  登録ファイル一覧
# ------------------------------------------------------------------ #

def render_file_list_table(dataset_type: str, client_id: str):
    repo = DatasetRepo()
    cur_v = repo.get_current_dataset_version(client_id, dataset_type)
    if not cur_v or not cur_v.get("normalized_json"):
        return
    data = cur_v.get("normalized_json")
    if isinstance(data, dict):
        data = [data]
    rows = []
    for item in data:
        if isinstance(item.get("meta"), dict):
            m = item["meta"]
            fname = f"自動取得（{m.get('target_industry','?')}/{m.get('target_location','?')}）"
            ftype = "外部API（e-Stat）"
            fdate = m.get("fetched_at", "")
        else:
            fname = item.get("filename", item.get("name", "不明"))
            ftype = item.get("type", "不明")
            fdate = item.get("uploaded_at", "")
        rows.append({"ファイル名": fname, "種別": ftype, "登録日時": fdate[:16]})
    if rows:
        st.markdown(f"**登録済みファイル**")
        st.dataframe(pd.DataFrame(rows), use_container_width=True)


# ------------------------------------------------------------------ #
#  メイン
# ------------------------------------------------------------------ #

def app():
    load_custom_css()
    from core.sidebar import render_sidebar
    render_sidebar()

    if not check_auth():
        st.warning("ログインが必要です。")
        return
    if not st.session_state.get("client_id"):
        st.warning("プロジェクトを選択してください。")
        return

    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:0.5rem;">
        <div style="background:#ede9fe;color:#5b21b6;font-size:0.72rem;font-weight:700;
                    padding:3px 10px;border-radius:999px;">STEP 1 — データ収集フェーズ</div>
        <div style="font-size:0.8rem;color:#9ca3af;">財務データ（PL/BS）の登録がメイン作業です</div>
    </div>
    """, unsafe_allow_html=True)
    st.title("📥 データ登録コックピット")
    st.caption("CF計算書は不要です。P/L・B/S・借入金一覧を登録してください。")

    repo = DatasetRepo()
    client_id = st.session_state.client_id

    v_fin = repo.get_current_dataset_version(client_id, "financial")
    v_int = repo.get_current_dataset_version(client_id, "internal")
    v_ext = repo.get_current_dataset_version(client_id, "external")

    s_fin = v_fin['quality_json'].get('quality_score', 0) if v_fin and v_fin.get('quality_json') else 0
    s_int = v_int['quality_json'].get('quality_score', 0) if v_int and v_int.get('quality_json') else 0
    s_ext = 80 if v_ext else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        render_health_card("財務データ（PL/BS）", s_fin, "💰", "登録済み" if s_fin > 0 else "未登録")
    with c2:
        render_health_card("内部データ（売上・文書）", s_int, "🏢", "登録済み" if s_int > 0 else "未登録")
    with c3:
        render_health_card("市場情報（外部データ）", s_ext, "🌍", "取得済み" if s_ext > 0 else "未取得")

    st.markdown("<br>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([
        "1. 財務データ（PL/BS）",
        "2. 内部データ（売上・文書）",
        "3. 外部データ（市場情報）",
    ])

    # ===================================================
    # TAB 1: 財務データ
    # ===================================================
    with tab1:
        st.markdown("### 📊 財務データ（PL/BS）登録")
        st.caption("決算書の数値を登録します。**CF計算書は不要**です（簡易キャッシュフローは自動計算）。単位：百万円")

        if v_fin:
            fname = v_fin.get("quality_json", {}).get("filename", "")
            vdate = v_fin.get("created_at", "")[:10]
            st.success(f"✅ 登録済み: **{fname}** （{vdate} 更新）")

        input_method = st.radio(
            "入力方法",
            ["📄 CSVアップロード", "✏️ 直接入力（手入力）", "📊 登録データを確認"],
            horizontal=True,
        )
        st.divider()

        # ---- CSV アップロード ----
        if input_method == "📄 CSVアップロード":
            col_dl, col_up = st.columns(2, gap="large")

            with col_dl:
                st.markdown("#### ① テンプレートをダウンロード")
                st.info("👇 このCSVに決算書（3〜5年分）の数値を入力してアップロードしてください。\n\nCF計算書は含まれていません。減価償却費は損益計算書の注記から取得してください。")
                st.download_button(
                    "📥 PL/BS テンプレート（CSV）",
                    create_pl_bs_template(),
                    "pl_bs_template.csv",
                    "text/csv",
                    use_container_width=True,
                    type="primary",
                )
                st.markdown("---")
                st.markdown("**借入金一覧テンプレート**")
                st.caption("融資1件につき1行。STEP 4（財務分析）で借入金を個別登録する際の参考にしてください。")
                st.download_button(
                    "📥 借入金一覧テンプレート（CSV）",
                    create_loan_template(),
                    "loan_list_template.csv",
                    "text/csv",
                    use_container_width=True,
                )
                with st.expander("借入金テンプレートの項目説明"):
                    st.markdown("""
| 項目 | 説明 |
|---|---|
| 借入先 | 銀行名・支店名 |
| 当初借入日 | 例: 2021-04-01 |
| 当初借入残高（万円） | 融資実行時の元本 |
| 現在の残高（万円） | 現時点の残高 |
| 毎月返済額（万円） | 月次元金返済額 |
| 完済予定日 | 例: 2026-03-31 |
| 金利（%） | 年利 |
| 融資形態 | 証書貸付／手形貸付／当座貸付／その他 |
| 借入年数 | 融資期間（年） |
""")

            with col_up:
                st.markdown("#### ② CSVをアップロード・保存")
                f_files = st.file_uploader(
                    "PL/BS CSV または Excel をアップロード（複数年度・複数ファイル可）",
                    type=["xlsx", "csv"],
                    key="fin_up",
                    accept_multiple_files=True,
                )

                if f_files:
                    processed_data = []
                    scores = []
                    has_error = False

                    for f in f_files:
                        try:
                            if f.name.endswith('.csv'):
                                df = read_csv_auto(f)
                            else:
                                df = pd.read_excel(f)

                            df_clean = clean_financial_df(df)
                            q_res = check_financial_quality(df_clean)
                            is_template = q_res['quality_score'] >= 40

                            df_to_save = sanitize_df(df_clean if is_template else df)
                            processed_data.append({
                                "filename": f.name,
                                "type": "financial_standard" if is_template else "support_document",
                                "records": df_to_save.to_dict('records'),
                                "uploaded_at": pd.Timestamp.now().isoformat(),
                            })
                            scores.append(f"{f.name}: {q_res['quality_score']}")

                            with st.expander(f"📄 {f.name} のプレビュー", expanded=True):
                                st.dataframe(df.head(10), use_container_width=True)
                                if is_template:
                                    st.success(f"品質スコア: {q_res['quality_score']}/100")
                                else:
                                    st.warning("テンプレート形式と一致しません。サポート資料として保存します。")

                        except Exception as e:
                            st.error(f"{f.name} の処理中にエラー: {e}")
                            has_error = True

                    if processed_data and not has_error:
                        if st.button("💾 保存する", type="primary", use_container_width=True):
                            version = repo.save_dataset_version(
                                client_id, "financial", processed_data,
                                {"filename": f"{len(processed_data)}ファイル",
                                 "file_list": [d["filename"] for d in processed_data],
                                 "quality_score": 100, "scores": scores},
                                "upload_multi",
                                created_by=st.session_state.user.id,
                            )
                            if version:
                                st.success(f"✅ {len(processed_data)}ファイルを保存しました！")
                                import time; time.sleep(1); st.rerun()

                st.markdown("---")
                render_file_list_table("financial", client_id)

        # ---- 直接入力 ----
        elif input_method == "✏️ 直接入力（手入力）":
            st.info("決算書（P/L・B/S）の数値を直接入力します。CF計算書は不要です。**単位：百万円**")

            years = st.multiselect(
                "入力する年度を選択（複数選択可）",
                [2019, 2020, 2021, 2022, 2023, 2024, 2025],
                default=[2023, 2024, 2025],
            )
            if not years:
                st.warning("年度を1つ以上選択してください。")
                st.stop()

            years = sorted(years)
            year_tabs = st.tabs([f"{y}年度" for y in years])
            all_year_data = {}

            for ytab, year in zip(year_tabs, years):
                with ytab:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown("**損益計算書（P/L）** — 単位：百万円")
                        revenue     = st.number_input("売上高", 0.0, key=f"rev_{year}", step=1.0, format="%.1f")
                        cogs        = st.number_input("売上原価", 0.0, key=f"cogs_{year}", step=1.0, format="%.1f")
                        gross       = revenue - cogs
                        st.metric("売上総利益（自動計算）", f"{gross:.1f} M")
                        sga         = st.number_input("販売費及び一般管理費", 0.0, key=f"sga_{year}", step=1.0, format="%.1f")
                        op_profit   = gross - sga
                        st.metric("営業利益（自動計算）", f"{op_profit:.1f} M")
                        non_op_inc  = st.number_input("営業外収益", 0.0, key=f"noi_{year}", step=0.1, format="%.1f")
                        non_op_exp  = st.number_input("営業外費用（支払利息含む）", 0.0, key=f"noe_{year}", step=0.1, format="%.1f")
                        ord_profit  = op_profit + non_op_inc - non_op_exp
                        st.metric("経常利益（自動計算）", f"{ord_profit:.1f} M")
                        special     = st.number_input("特別損益（特別利益は+、特別損失は-）", 0.0, key=f"sp_{year}", step=0.1, format="%.1f")
                        tax         = st.number_input("法人税等", 0.0, key=f"tax_{year}", step=0.1, format="%.1f")
                        net_profit  = ord_profit + special - tax
                        st.metric("当期純利益（自動計算）", f"{net_profit:.1f} M")
                        depreciation= st.number_input("減価償却費（注記より）", 0.0, key=f"dep_{year}", step=0.1, format="%.1f")

                    with c2:
                        st.markdown("**貸借対照表（B/S）** — 単位：百万円")
                        cash        = st.number_input("現金預金", 0.0, key=f"cash_{year}", step=1.0, format="%.1f")
                        receivables = st.number_input("売掛金・受取手形", 0.0, key=f"rec_{year}", step=1.0, format="%.1f")
                        inventory   = st.number_input("棚卸資産", 0.0, key=f"inv_{year}", step=1.0, format="%.1f")
                        other_ca    = st.number_input("その他流動資産", 0.0, key=f"oca_{year}", step=0.1, format="%.1f")
                        current_assets = cash + receivables + inventory + other_ca
                        st.metric("流動資産合計（自動計算）", f"{current_assets:.1f} M")
                        fixed_assets= st.number_input("固定資産合計", 0.0, key=f"fa_{year}", step=1.0, format="%.1f")
                        total_assets= current_assets + fixed_assets
                        st.metric("資産合計（自動計算）", f"{total_assets:.1f} M")
                        st.markdown("---")
                        payables    = st.number_input("買掛金・支払手形", 0.0, key=f"pay_{year}", step=0.5, format="%.1f")
                        st_loans    = st.number_input("短期借入金", 0.0, key=f"stl_{year}", step=0.5, format="%.1f")
                        other_cl    = st.number_input("その他流動負債", 0.0, key=f"ocl_{year}", step=0.5, format="%.1f")
                        current_liab= payables + st_loans + other_cl
                        st.metric("流動負債合計（自動計算）", f"{current_liab:.1f} M")
                        lt_loans    = st.number_input("長期借入金", 0.0, key=f"ltl_{year}", step=0.5, format="%.1f")
                        other_fl    = st.number_input("その他固定負債", 0.0, key=f"ofl_{year}", step=0.5, format="%.1f")
                        fixed_liab  = lt_loans + other_fl
                        st.metric("固定負債合計（自動計算）", f"{fixed_liab:.1f} M")
                        equity      = st.number_input("純資産合計", 0.0, key=f"eq_{year}", step=0.5, format="%.1f")
                        employees   = st.number_input("従業員数（人）", 0, key=f"emp_{year}", step=1)

                    all_year_data[str(year)] = {
                        "年度": year,
                        "売上高": revenue, "売上原価": cogs, "売上総利益": gross,
                        "販売費及び一般管理費": sga, "営業利益": op_profit,
                        "営業外収益": non_op_inc, "営業外費用（支払利息含む）": non_op_exp,
                        "経常利益": ord_profit, "特別損益": special,
                        "法人税等": tax, "当期純利益": net_profit,
                        "減価償却費": depreciation,
                        "現金預金": cash, "売掛金": receivables,
                        "棚卸資産": inventory, "その他流動資産": other_ca,
                        "流動資産合計": current_assets, "固定資産合計": fixed_assets,
                        "資産合計": total_assets, "買掛金": payables,
                        "短期借入金": st_loans, "その他流動負債": other_cl,
                        "流動負債合計": current_liab, "長期借入金": lt_loans,
                        "固定負債合計": fixed_liab, "純資産合計": equity,
                        "従業員数": employees,
                    }

            st.markdown("---")
            if st.button("💾 直接入力データを保存", type="primary", use_container_width=True):
                records = list(all_year_data.values())
                payload = [{
                    "filename": f"直接入力（{len(years)}年度）",
                    "type": "financial_direct_input",
                    "records": records,
                    "uploaded_at": pd.Timestamp.now().isoformat(),
                }]
                version = repo.save_dataset_version(
                    client_id, "financial", payload,
                    {"filename": f"直接入力（{len(years)}年度）", "quality_score": 90, "years": years},
                    "direct_input",
                    created_by=st.session_state.user.id,
                )
                if version:
                    st.success("✅ 財務データを保存しました！")
                    import time; time.sleep(1); st.rerun()

        # ---- データ確認 ----
        elif input_method == "📊 登録データを確認":
            render_verification_tables(v_fin)

    # ===================================================
    # TAB 2: 内部データ
    # ===================================================
    with tab2:
        st.markdown("### 🏢 内部データ（売上・文書）登録")

        sub_t1, sub_t2 = st.tabs(["売上データ", "文書・資料"])

        with sub_t1:
            st.subheader("売上データ登録")
            col_t1, col_t2 = st.columns([1, 2])
            with col_t1:
                industry = st.selectbox("業種テンプレート", ["小売業", "製造業", "建設業", "サービス業"])
                st.download_button(
                    "📥 売上テンプレートをダウンロード",
                    create_sales_template(industry),
                    f"sales_{industry}.csv", "text/csv",
                    use_container_width=True,
                )
            with col_t2:
                s_files = st.file_uploader(
                    "売上データ（CSV/Excel）をアップロード",
                    type=["xlsx", "csv"], key="sale_up", accept_multiple_files=True,
                )
                if s_files:
                    processed_sales, s_scores, s_has_error = [], [], False
                    for f in s_files:
                        try:
                            df_s = read_csv_auto(f) if f.name.endswith('.csv') else pd.read_excel(f)
                            df_s_clean = clean_sales_df(df_s)
                            q_res = check_sales_quality(df_s_clean)
                            processed_sales.append({
                                "filename": f.name, "type": "sales_transaction",
                                "records": sanitize_df(df_s_clean).to_dict('records'),
                                "uploaded_at": pd.Timestamp.now().isoformat(),
                            })
                            s_scores.append(f"{f.name}: {q_res['quality_score']}")
                            with st.expander(f"📄 {f.name} のプレビュー", expanded=True):
                                st.dataframe(df_s_clean.head(5), use_container_width=True)
                                st.caption(f"品質スコア: {q_res['quality_score']}/100")
                        except Exception as e:
                            st.error(f"{f.name}: {e}"); s_has_error = True

                    if processed_sales and not s_has_error:
                        if st.button("💾 売上データを保存", type="primary"):
                            repo.save_dataset_version(
                                client_id, "internal", processed_sales,
                                {"filename": f"{len(processed_sales)}ファイル", "quality_score": 100, "scores": s_scores},
                                "upload_multi", created_by=st.session_state.user.id,
                            )
                            st.success("✅ 売上データを保存しました！")
                            import time; time.sleep(1); st.rerun()

            st.markdown("---")
            render_file_list_table("internal", client_id)

        with sub_t2:
            st.subheader("文書・資料の登録")
            st.info("PDF・テキスト・Wordファイルを登録するとAI分析の参照資料として使われます。")
            i_docs = st.file_uploader(
                "文書をアップロード", type=["txt", "pdf", "docx", "json", "csv"],
                accept_multiple_files=True, key="int_docs",
            )
            if i_docs and st.button("📥 文書を取り込む", key="ingest_int"):
                processed_count = 0
                existing_docs = []
                cur_v = repo.get_current_dataset_version(client_id, "internal_docs")
                if cur_v and cur_v.get("normalized_json"):
                    prev = cur_v.get("normalized_json")
                    existing_docs = prev if isinstance(prev, list) else [prev]
                for f in i_docs:
                    try:
                        text = ""
                        if f.name.endswith(".pdf"):
                            import pypdf
                            reader = pypdf.PdfReader(f)
                            for page in reader.pages:
                                t = page.extract_text()
                                if t: text += t + "\n"
                        elif f.name.endswith(".txt"):
                            text = f.read().decode("utf-8")
                        elif f.name.endswith(".json"):
                            text = json.dumps(json.load(f), indent=2, ensure_ascii=False)
                        elif f.name.endswith(".csv"):
                            df_t = read_csv_auto(f)
                            text = f"### {f.name}\n\n" + df_t.to_markdown(index=False)
                        else:
                            continue
                        existing_docs.append({
                            "filename": f.name, "content": text,
                            "type": "internal_doc_text",
                            "uploaded_at": pd.Timestamp.now().isoformat(),
                        })
                        processed_count += 1
                    except Exception as e:
                        st.error(f"{f.name}: {e}")
                if processed_count > 0:
                    repo.save_dataset_version(
                        client_id, "internal_docs", existing_docs,
                        {"filename": f"バッチ（{processed_count}件）", "count": len(existing_docs)},
                        "upload_doc",
                        created_by=st.session_state.user.id if "user" in st.session_state else None,
                    )
                    st.success(f"✅ {processed_count}件の文書を登録しました。")
                    import time; time.sleep(1); st.rerun()
            st.markdown("---")
            render_file_list_table("internal_docs", client_id)

    # ===================================================
    # TAB 3: 外部データ
    # ===================================================
    with tab3:
        st.markdown("### 🌍 外部データ（市場情報）取得")
        st.caption("業種・所在地に基づいて政府統計（e-Stat）・地域経済データを自動取得します。")

        try:
            sb = get_supabase_client()
            c_res = sb.table("clients").select("industry,location").eq("id", client_id).single().execute()
            c_ind = c_res.data.get("industry", "未設定") if c_res.data else "未設定"
            c_loc = c_res.data.get("location", "未設定") if c_res.data else "未設定"
        except Exception:
            c_ind, c_loc = "不明", "不明"

        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown("#### ⚡ 自動取得（政府統計API）")
                st.markdown(f"対象: **{c_ind}** ／ **{c_loc}**")
                st.caption("業界平均指標・地域経済データをe-Stat（政府統計）から自動取得します。")
            with c2:
                if st.button("🔄 自動取得を実行", type="primary", use_container_width=True):
                    with st.spinner("政府統計APIからデータ取得中..."):
                        try:
                            conn = ExternalDataConnector()
                            stats = conn.get_industry_statistics(c_ind)
                            reg = conn.get_regional_market_potential(c_loc, c_ind)
                            data = {
                                "industry_stats": stats.dict() if stats else None,
                                "regional": reg,
                                "meta": {"fetched_at": pd.Timestamp.now().isoformat()},
                            }
                            repo.save_dataset_version(
                                client_id, "external", data, {"source": "auto-fetch"}, "api",
                                created_by=st.session_state.user.id,
                            )
                            st.success("✅ 外部データを取得しました！")
                            st.rerun()
                        except Exception as e:
                            st.error(f"取得失敗: {e}")

        st.divider()
        st.markdown("#### 手動アップロード（調査レポートなど）")
        e_docs = st.file_uploader(
            "レポートをアップロード（PDF/JSON/TXT）",
            type=["json", "pdf", "txt"], accept_multiple_files=True, key="ext_docs",
        )
        if e_docs and st.button("📥 レポートを取り込む"):
            processed_count = 0
            existing_docs = []
            cur_v = repo.get_current_dataset_version(client_id, "external_docs")
            if cur_v and cur_v.get("normalized_json"):
                prev = cur_v.get("normalized_json")
                existing_docs = prev if isinstance(prev, list) else [prev]
            for f in e_docs:
                try:
                    text = ""
                    if f.name.endswith(".pdf"):
                        import pypdf
                        reader = pypdf.PdfReader(f)
                        for page in reader.pages:
                            t = page.extract_text()
                            if t: text += t + "\n"
                    elif f.name.endswith(".txt"):
                        text = f.read().decode("utf-8")
                    elif f.name.endswith(".json"):
                        text = json.dumps(json.load(f), indent=2, ensure_ascii=False)
                    else:
                        continue
                    existing_docs.append({
                        "filename": f.name, "content": text,
                        "type": "external_document_text",
                        "uploaded_at": pd.Timestamp.now().isoformat(),
                    })
                    processed_count += 1
                except Exception as e:
                    st.error(f"{f.name}: {e}")
            if processed_count > 0:
                repo.save_dataset_version(
                    client_id, "external_docs", existing_docs,
                    {"filename": f"バッチ（{processed_count}件）", "count": len(existing_docs)},
                    "upload_doc",
                    created_by=st.session_state.user.id if "user" in st.session_state else None,
                )
                st.success(f"✅ {processed_count}件のレポートを取り込みました。")
                import time; time.sleep(1); st.rerun()

        st.markdown("---")
        render_file_list_table("external_docs", client_id)
        render_file_list_table("external", client_id)


if __name__ == "__main__":
    app()
