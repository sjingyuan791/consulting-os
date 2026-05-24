"""
統合テスト: MidtermPlanEngine 全13セクション一括生成
実際のLLM呼び出しを含むEnd-to-Endテスト
"""
import asyncio
import json
import sys
import time

def main():
    from core.midterm_plan_engine import MidtermPlanEngine, SECTION_DEFINITIONS

    engine = MidtermPlanEngine(
        pipeline_data={
            "financial": {"revenue": [100, 110, 120], "profit": [10, 12, 15]},
            "internal": {"employees": 50, "departments": ["営業", "開発", "管理"]},
            "external": {"market_size": "500億円", "growth_rate": "3%"}
        },
        guardrails={
            "mission_objective": "顧客価値の最大化を通じて持続可能な成長を実現する",
            "success_state_definition": "売上高を1.5倍に伸ばす",
            "core_values": ["誠実", "革新", "顧客第一"],
            "time_horizon_years": 3
        },
        client_id="integration-test"
    )

    print("=" * 60)
    print("🧪 統合テスト: 全13セクション一括生成")
    print("=" * 60)

    start = time.time()
    results = {"pass": 0, "fail": 0, "errors": []}

    def progress(pct, msg):
        print(f"  [{pct:3d}%] {msg}")

    try:
        doc = asyncio.run(engine.generate_full_plan(progress_callback=progress))
    except Exception as e:
        print(f"\n❌ FATAL: generate_full_plan() がクラッシュ: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    elapsed = time.time() - start
    print(f"\n⏱️ 生成時間: {elapsed:.1f}秒")
    print(f"📄 セクション数: {len(doc.sections)}")

    # --- 各セクション検証 ---
    print("\n" + "-" * 60)
    print("📊 セクション別検証結果")
    print("-" * 60)

    for i, section in enumerate(doc.sections):
        sec_def = SECTION_DEFINITIONS[i]
        errors = []

        # Check 1: section_id
        if section.section_id != sec_def["id"]:
            errors.append(f"section_id不一致: {section.section_id} != {sec_def['id']}")

        # Check 2: narrative exists
        nar_len = len(section.narrative) if section.narrative else 0
        if nar_len == 0:
            errors.append("narrative が空")
        elif "エラー" in section.narrative:
            errors.append(f"narrative にエラー文言: {section.narrative[:80]}")

        # Check 3: data exists
        data_keys = list(section.data.keys()) if section.data else []
        if not data_keys:
            errors.append("data が空")

        # Result
        status = "✅" if not errors else "❌"
        if errors:
            results["fail"] += 1
            results["errors"].append((sec_def["id"], sec_def["title"], errors))
        else:
            results["pass"] += 1

        print(f"  {status} §{sec_def['id']:2d} {sec_def['title']:<20s} | NAR:{nar_len:4d}文字 | DATA:{len(data_keys)}キー {data_keys[:3]}")

    # --- typed_sections 検証 ---
    print("\n" + "-" * 60)
    print("🔗 セクション間連携 (typed_sections)")
    print("-" * 60)

    expected_keys = [
        "philosophy", "vision", "external", "internal", "root_cause",
        "swot", "cross_swot", "corporate_strategy", "domain_strategy",
        "functional", "initiatives", "kpi", "financial"
    ]

    ts_pass = 0
    ts_fail = 0
    for key in expected_keys:
        val = engine.typed_sections.get(key)
        if val is not None:
            print(f"  ✅ {key:<22s} → {type(val).__name__}")
            ts_pass += 1
        else:
            print(f"  ⚠️ {key:<22s} → None (Pydantic validation warning)")
            ts_fail += 1

    # --- Document attributes ---
    print("\n" + "-" * 60)
    print("📦 ドキュメント属性")
    print("-" * 60)
    print(f"  document_id:    {doc.document_id}")
    print(f"  client_id:      {doc.client_id}")
    print(f"  plan_period:    {doc.plan_period}")
    print(f"  sections:       {len(doc.sections)}")
    print(f"  dependency_map: {'あり' if doc.dependency_map else 'なし'}")

    # --- Summary ---
    print("\n" + "=" * 60)
    total = results["pass"] + results["fail"]
    print(f"📋 結果サマリ: {results['pass']}/{total} セクション成功")
    print(f"   セクション間連携: {ts_pass}/{len(expected_keys)} キー格納済み")
    print(f"   生成時間: {elapsed:.1f}秒")

    if results["errors"]:
        print("\n⚠️ 失敗セクション:")
        for sid, title, errs in results["errors"]:
            for e in errs:
                print(f"   §{sid} {title}: {e}")

    if results["fail"] == 0 and ts_pass > 0:
        print("\n🎉 統合テスト PASSED!")
    elif results["fail"] == 0:
        print("\n⚠️ セクション生成は全成功、typed_sections格納に警告あり")
    else:
        print("\n❌ 統合テスト FAILED")

    print("=" * 60)

if __name__ == "__main__":
    main()
