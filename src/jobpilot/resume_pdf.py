"""PDF 简历解析(FR1 二期)。

两级策略:
1. 文本型 PDF:pdfplumber 直接抽取文本(零模型成本);
2. 扫描件/版式复杂(抽取文本过短):逐页渲染为图片,走视觉模型转 Markdown。
"""

import base64
import io
from pathlib import Path

MIN_TEXT_LENGTH = 120  # 少于该字符数视为扫描件,走视觉兜底

RESUME_PARSE_PROMPT = (
    "你收到一份简历的逐页截图。请把简历内容完整整理为 Markdown 文本:"
    "保留姓名、联系方式、教育经历、技能、项目经历、工作经历的全部原始信息,"
    "按标准简历结构分节,不遗漏、不编造、不添加任何原文没有的内容。只输出 Markdown。"
)


def extract_text(path: Path | str) -> str:
    """文本型 PDF 直接抽取(零成本路径)."""
    import pdfplumber

    parts = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            parts.append(page.extract_text() or "")
    return "\n\n".join(parts).strip()


def render_page_images(path: Path | str, *, max_pages: int = 3, resolution: int = 120) -> list[str]:
    """逐页渲染为 PNG base64 data URL(视觉兜底路径)."""
    import pdfplumber

    images = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages[:max_pages]:
            pil = page.to_image(resolution=resolution).original
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            images.append("data:image/png;base64," + base64.b64encode(buf.getvalue()).decode())
    return images


def parse_resume(gateway, path: Path | str) -> tuple[str, str]:
    """解析 PDF 简历,返回 (Markdown 文本, 使用通道: 'text' | 'vision')."""
    text = extract_text(path)
    if len(text) >= MIN_TEXT_LENGTH:
        return text, "text"
    images = render_page_images(path)
    md = gateway.text(RESUME_PARSE_PROMPT, images=images, module="resume")
    return md, "vision"


def update_profile_yaml(profile_path: Path | str, resume_md: str) -> Path:
    """把解析出的简历写回 profile.yaml 的 resume_md(重置 resume_version 使缓存失效)."""
    import yaml

    from jobpilot.models.profile import Profile

    path = Path(profile_path)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data["resume_md"] = resume_md
    data["resume_version"] = ""  # Profile 模型会按内容重新计算
    profile = Profile.model_validate(data)
    data["resume_version"] = profile.resume_version
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path
