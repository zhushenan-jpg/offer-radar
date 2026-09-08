"""Interview Brief 数据模型单元测试."""

import pytest
from pydantic import ValidationError

from jobpilot.models.interview_brief import (
    FollowUp,
    InterviewBrief,
    PredictedQuestion,
    WeakAreaDrill,
)


class TestPredictedQuestion:
    """预测问题测试."""

    def test_valid_predicted_question(self):
        """验证有效预测问题."""
        question = PredictedQuestion(
            id="q_001",
            question_text="请介绍你的微服务架构经验",
            claim_type="Architecture",
            related_claim_ids=["claim_001"],
            probability=0.85,
            source="jd_direct",
        )
        assert question.id == "q_001"
        assert question.probability == 0.85

    def test_predicted_question_invalid_probability(self):
        """验证无效概率."""
        with pytest.raises(ValidationError):
            PredictedQuestion(
                id="q_001",
                question_text="test",
                claim_type="Technical",
                probability=1.5,  # 超出范围
                source="jd_direct",
            )


class TestFollowUp:
    """追问协议测试."""

    def test_valid_followup(self):
        """验证有效追问协议."""
        followup = FollowUp(
            question_id="q_001",
            followup_text="这个架构是你独立设计的吗？",
            detection_target="验证 Ownership",
            red_flags=["用'我们'代替'我'", "避重就轻"],
        )
        assert followup.question_id == "q_001"
        assert len(followup.red_flags) == 2


class TestWeakAreaDrill:
    """弱项练习测试."""

    def test_valid_weak_area_drill(self):
        """验证有效弱项练习."""
        drill = WeakAreaDrill(
            id="drill_001",
            target_claim_id="gap_001",
            drill_questions=["请介绍 Kubernetes 的核心概念"],
            expected_evidence="能说出 Pod、Service、Deployment",
            common_mistakes=["只背概念，说不出实际场景"],
        )
        assert drill.id == "drill_001"
        assert len(drill.drill_questions) == 1


class TestInterviewBrief:
    """面试速览测试."""

    def test_valid_interview_brief(self):
        """验证有效面试速览."""
        brief = InterviewBrief(
            id="brief_001",
            job_id="job_001",
            company_overview="这是一家云计算公司...",
            tech_stack=["Python", "Kubernetes", "Docker"],
            predicted_questions=[
                PredictedQuestion(
                    id="q_001",
                    question_text="请介绍微服务经验",
                    claim_type="Architecture",
                    probability=0.85,
                    source="jd_direct",
                )
            ],
            followup_protocol=[
                FollowUp(
                    question_id="q_001",
                    followup_text="是你独立设计的吗？",
                    detection_target="验证 Ownership",
                    red_flags=["用'我们'代替'我'"],
                )
            ],
            weak_area_drills=[
                WeakAreaDrill(
                    id="drill_001",
                    target_claim_id="gap_001",
                    drill_questions=["K8s 核心概念"],
                    expected_evidence="能说出核心概念",
                    common_mistakes=["只背概念"],
                )
            ],
            evidence_summary={"Architecture": ["claim_001"], "Technical": ["claim_002"]},
            brief_markdown="# 面试速览\n...",
            generation_tokens=200,
            generation_cost=0.10,
        )
        assert len(brief.predicted_questions) == 1
        assert len(brief.followup_protocol) == 1
        assert len(brief.weak_area_drills) == 1
        assert "Architecture" in brief.evidence_summary

    def test_empty_interview_brief(self):
        """验证空面试速览."""
        brief = InterviewBrief(
            id="brief_002",
            job_id="job_002",
        )
        assert len(brief.predicted_questions) == 0
        assert len(brief.followup_protocol) == 0
        assert len(brief.weak_area_drills) == 0
        assert brief.brief_markdown == ""

    def test_interview_brief_serialization(self):
        """验证面试速览序列化."""
        brief = InterviewBrief(
            id="brief_001",
            job_id="job_001",
            predicted_questions=[
                PredictedQuestion(
                    id="q_001",
                    question_text="请介绍微服务经验",
                    claim_type="Architecture",
                    probability=0.85,
                    source="jd_direct",
                )
            ],
        )

        # 序列化
        json_str = brief.model_dump_json()
        assert "brief_001" in json_str
        assert "微服务" in json_str

        # 反序列化
        brief2 = InterviewBrief.model_validate_json(json_str)
        assert brief2.id == "brief_001"
        assert len(brief2.predicted_questions) == 1
