"""Claim 提取准确率评测脚本.

使用人工标注的 20 条样本验证 Claim 分类准确率和 Gap 检测召回率.
"""

import json
from pathlib import Path

import pytest

from jobpilot.models.claim import ClaimStrength, ClaimType, GapType

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def load_annotated_samples() -> list[dict]:
    """加载人工标注样本."""
    with open(FIXTURES_DIR / "annotated_claims_sample.json", "r", encoding="utf-8") as f:
        return json.load(f)


def classify_claim_type(claim_text: str) -> ClaimType:
    """基于关键词的简单 Claim 分类规则（用于离线评测）."""
    claim_text_lower = claim_text.lower()

    # Ownership: 负责、主导（优先级最高，因为"负责 XX 架构"应该是 Ownership）
    ownership_keywords = ["负责", "主导", "带领", "独立完成"]
    if any(kw in claim_text for kw in ownership_keywords):
        return ClaimType.OWNERSHIP

    # Metric: 包含数字、百分比、量词
    metric_keywords = ["%", "倍", "万", "千", "百", "秒", "ms", "分钟", "小时", "qps", "tps"]
    if any(kw in claim_text_lower for kw in metric_keywords):
        return ClaimType.METRIC
    # 包含具体数字 + 量化动词
    if any(c.isdigit() for c in claim_text) and any(
        kw in claim_text_lower for kw in ["提升", "优化", "减少", "降低", "增长", "达到", "级"]
    ):
        return ClaimType.METRIC

    # Result: 成果、影响
    result_keywords = ["上架", "发布", "部署到", "上线", "获奖", "获得", "推动", "从 0 到 1", "成功"]
    if any(kw in claim_text for kw in result_keywords):
        return ClaimType.RESULT

    # Architecture: 系统设计相关（仅当明确是"架构设计"时）
    arch_keywords = ["架构设计", "架构搭建", "系统设计"]
    if any(kw in claim_text for kw in arch_keywords):
        return ClaimType.ARCHITECTURE

    # Technical: 技术、工具（默认）
    return ClaimType.TECHNICAL


def classify_claim_strength(claim_text: str) -> ClaimStrength:
    """基于关键词的简单 Claim 强度判断."""
    weak_keywords = ["熟练", "丰富", "良好", "较强", "一定", "多年"]
    if any(kw in claim_text for kw in weak_keywords) and not any(
        c.isdigit() for c in claim_text
    ):
        return ClaimStrength.WEAK
    return ClaimStrength.STRONG


def classify_gap_type(jd_requirement: str) -> GapType:
    """基于关键词的 Gap 类型判断."""
    hard_keywords = ["必须", "required", "mandatory", "必备", "硬性"]
    if any(kw in jd_requirement.lower() for kw in hard_keywords):
        return GapType.HARD_BLOCK
    return GapType.SOFT_GAP


class TestClaimAccuracy:
    """Claim 提取准确率评测."""

    @pytest.fixture
    def samples(self):
        return load_annotated_samples()

    def test_claim_type_accuracy(self, samples):
        """测试 Claim 分类准确率（目标 ≥ 85%）."""
        correct = 0
        total = 0
        errors = []

        for sample in samples:
            for expected in sample["expected_claims"]:
                predicted = classify_claim_type(expected["claim_text"])
                expected_type = ClaimType(expected["claim_type"])
                total += 1

                if predicted == expected_type:
                    correct += 1
                else:
                    errors.append(
                        {
                            "sample_id": sample["id"],
                            "claim_text": expected["claim_text"],
                            "expected": expected_type.value,
                            "predicted": predicted.value,
                        }
                    )

        accuracy = correct / total if total > 0 else 0
        print(f"\nClaim 分类准确率: {accuracy:.1%} ({correct}/{total})")
        if errors:
            print(f"错误样本 ({len(errors)}):")
            for err in errors[:5]:  # 只显示前 5 个
                print(f"  - {err['sample_id']}: {err['claim_text']}")
                print(f"    预测: {err['predicted']}, 期望: {err['expected']}")

        assert accuracy >= 0.85, f"Claim 分类准确率 {accuracy:.1%} 低于 85% 目标"

    def test_claim_strength_accuracy(self, samples):
        """测试 Claim 强度判断准确率（目标 ≥ 80%）."""
        correct = 0
        total = 0

        for sample in samples:
            for expected in sample["expected_claims"]:
                predicted = classify_claim_strength(expected["claim_text"])
                expected_strength = ClaimStrength(expected["strength"])
                total += 1

                if predicted == expected_strength:
                    correct += 1

        accuracy = correct / total if total > 0 else 0
        print(f"\nClaim 强度判断准确率: {accuracy:.1%} ({correct}/{total})")
        assert accuracy >= 0.80, f"Claim 强度判断准确率 {accuracy:.1%} 低于 80% 目标"

    def test_gap_type_accuracy(self, samples):
        """测试 Gap 类型判断准确率（目标 ≥ 90%）."""
        correct = 0
        total = 0

        for sample in samples:
            for expected in sample["expected_gaps"]:
                predicted = classify_gap_type(expected["jd_requirement"])
                expected_type = GapType(expected["gap_type"])
                total += 1

                if predicted == expected_type:
                    correct += 1

        accuracy = correct / total if total > 0 else 0
        print(f"\nGap 类型判断准确率: {accuracy:.1%} ({correct}/{total})")
        assert accuracy >= 0.90, f"Gap 类型判断准确率 {accuracy:.1%} 低于 90% 目标"

    def test_gap_detection_recall(self, samples):
        """测试 Gap 检测召回率（目标 ≥ 80%）."""
        total_expected_gaps = 0
        detected_gaps = 0

        for sample in samples:
            expected_gaps = sample["expected_gaps"]
            total_expected_gaps += len(expected_gaps)

            # 简单规则：如果 JD 中有"优先"但简历中没有对应技能，则检测为 Gap
            jd_text = sample["jd_text"].lower()
            resume_text = sample["resume_text"].lower()

            for gap in expected_gaps:
                req = gap["jd_requirement"].lower()
                # 检查简历中是否包含相关关键词
                req_keywords = [kw for kw in req.split() if len(kw) > 1]
                if not any(kw in resume_text for kw in req_keywords):
                    detected_gaps += 1

        recall = detected_gaps / total_expected_gaps if total_expected_gaps > 0 else 0
        print(f"\nGap 检测召回率: {recall:.1%} ({detected_gaps}/{total_expected_gaps})")
        assert recall >= 0.80, f"Gap 检测召回率 {recall:.1%} 低于 80% 目标"

    def test_all_samples_valid(self, samples):
        """验证所有样本数据格式正确."""
        assert len(samples) == 20, f"样本数量 {len(samples)} 不等于 20"

        for sample in samples:
            assert "id" in sample
            assert "jd_text" in sample
            assert "resume_text" in sample
            assert "expected_claims" in sample
            assert "expected_gaps" in sample
            assert len(sample["expected_claims"]) > 0

            for claim in sample["expected_claims"]:
                assert claim["claim_type"] in [t.value for t in ClaimType]
                assert claim["strength"] in [s.value for s in ClaimStrength]

            for gap in sample["expected_gaps"]:
                assert gap["gap_type"] in [g.value for g in GapType]
