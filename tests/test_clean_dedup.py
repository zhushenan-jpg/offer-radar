from jobpilot.collectors.clean import clean_jd
from jobpilot.collectors.dedup import dedupe_jobs
from jobpilot.models.job import JobPosting


class TestClean:
    def test_boilerplate_section_removed_core_kept(self):
        md = "## 职位描述\n- 熟练使用 Python\n- 熟悉 SQL\n\n## 薪资与福利\n日薪 200-350 元\n\n## 公司介绍\nNimbus Cloud 是一家云计算公司。\n"
        out = clean_jd(md)
        assert "熟练使用 Python" in out
        assert "薪资与福利" not in out and "日薪" not in out
        assert "公司介绍" not in out and "云计算公司" not in out

    def test_only_deletes_never_rewrites(self):
        md = "## 职位描述\n熟练使用 Python 与 FastAPI,了解 Docker 部署。\n"
        assert "熟练使用 Python 与 FastAPI,了解 Docker 部署。" in clean_jd(md)

    def test_english_benefits_section(self):
        md = "## About the role\nBuild APIs.\n\n## Benefits\nFree lunch.\n"
        out = clean_jd(md)
        assert "Build APIs." in out and "Free lunch" not in out

    def test_plain_text_without_headings(self):
        md = "Keep our infrastructure healthy.\n\nPerks: free snacks.\nStrong Python skills."
        out = clean_jd(md)
        assert "Strong Python skills." in out


def make_job(title, company="Stripe", source="greenhouse", loc="SF"):
    return JobPosting(
        id=JobPosting.compute_id(source, company, title, loc),
        source=source,
        company=company,
        title=title,
        location=loc,
        description_md=f"# {title}\nJD body",
    )


class TestDedupe:
    def test_exact_id_dedup(self):
        j1 = make_job("Backend Engineer")
        j2 = make_job("Backend Engineer")
        kept, removed = dedupe_jobs([j1, j2])
        assert len(kept) == 1 and removed == 1

    def test_punctuation_variant_same_company_dedup(self):
        kept, removed = dedupe_jobs(
            [make_job("Backend Intern - Shanghai"), make_job("Backend  Intern Shanghai")]
        )
        assert len(kept) == 1 and removed == 1

    def test_same_title_different_company_kept(self):
        kept, removed = dedupe_jobs(
            [make_job("Backend Engineer", company="A"), make_job("Backend Engineer", company="B")]
        )
        assert len(kept) == 2 and removed == 0

    def test_distinct_titles_kept(self):
        kept, removed = dedupe_jobs(
            [make_job("Backend Engineer"), make_job("Data Analyst, Finance")]
        )
        assert len(kept) == 2 and removed == 0
