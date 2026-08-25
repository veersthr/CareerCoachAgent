"""Canonical skill taxonomy (~60 skills) used by the Extractor to canonicalize
raw JD skill mentions via embeddings.py (cosine similarity, threshold 0.75).

Each entry's `aliases` list feeds the embedding text (canonical name + aliases)
so that common JD phrasings ("k8s", "Node", "Postgres") match the canonical name
even when the JD doesn't use the exact taxonomy string.
"""

from typing import TypedDict

from schemas import Domain


class TaxonomySkill(TypedDict):
    name: str
    domain: str
    aliases: list[str]


SKILL_TAXONOMY: list[TaxonomySkill] = [
    # --- programming_language ---
    {"name": "Python", "domain": Domain.PROGRAMMING_LANGUAGE, "aliases": ["Python3", "Python 3"]},
    {"name": "JavaScript", "domain": Domain.PROGRAMMING_LANGUAGE, "aliases": ["JS", "ECMAScript", "ES6"]},
    {"name": "TypeScript", "domain": Domain.PROGRAMMING_LANGUAGE, "aliases": ["TS"]},
    {"name": "Java", "domain": Domain.PROGRAMMING_LANGUAGE, "aliases": ["Core Java", "J2EE"]},
    {"name": "C++", "domain": Domain.PROGRAMMING_LANGUAGE, "aliases": ["Cpp", "C plus plus"]},
    {"name": "Go", "domain": Domain.PROGRAMMING_LANGUAGE, "aliases": ["Golang"]},
    {"name": "Rust", "domain": Domain.PROGRAMMING_LANGUAGE, "aliases": []},
    {"name": "SQL", "domain": Domain.PROGRAMMING_LANGUAGE, "aliases": ["Structured Query Language", "T-SQL", "PL/SQL"]},

    # --- frontend ---
    {"name": "React", "domain": Domain.FRONTEND, "aliases": ["React.js", "ReactJS"]},
    {"name": "Angular", "domain": Domain.FRONTEND, "aliases": ["AngularJS", "Angular2+"]},
    {"name": "Vue.js", "domain": Domain.FRONTEND, "aliases": ["Vue", "VueJS"]},
    {"name": "HTML/CSS", "domain": Domain.FRONTEND, "aliases": ["HTML5", "CSS3", "HTML", "CSS"]},
    {"name": "Next.js", "domain": Domain.FRONTEND, "aliases": ["NextJS"]},

    # --- backend ---
    {"name": "Node.js", "domain": Domain.BACKEND, "aliases": ["NodeJS", "Node"]},
    {"name": "Django", "domain": Domain.BACKEND, "aliases": ["Django REST Framework", "DRF"]},
    {"name": "Flask", "domain": Domain.BACKEND, "aliases": []},
    {"name": "FastAPI", "domain": Domain.BACKEND, "aliases": ["Fast API"]},
    {"name": "Spring Boot", "domain": Domain.BACKEND, "aliases": ["Spring", "Spring Framework"]},
    {"name": "REST API Design", "domain": Domain.BACKEND, "aliases": ["REST", "RESTful APIs", "API Design"]},
    {"name": "GraphQL", "domain": Domain.BACKEND, "aliases": []},

    # --- database ---
    {"name": "PostgreSQL", "domain": Domain.DATABASE, "aliases": ["Postgres"]},
    {"name": "MySQL", "domain": Domain.DATABASE, "aliases": ["MariaDB"]},
    {"name": "MongoDB", "domain": Domain.DATABASE, "aliases": ["Mongo", "NoSQL"]},
    {"name": "Redis", "domain": Domain.DATABASE, "aliases": ["In-memory caching"]},
    {"name": "Elasticsearch", "domain": Domain.DATABASE, "aliases": ["ELK Stack", "Elastic"]},

    # --- cloud_devops ---
    {"name": "AWS", "domain": Domain.CLOUD_DEVOPS, "aliases": ["Amazon Web Services", "EC2", "S3"]},
    {"name": "Azure", "domain": Domain.CLOUD_DEVOPS, "aliases": ["Microsoft Azure"]},
    {"name": "Google Cloud Platform", "domain": Domain.CLOUD_DEVOPS, "aliases": ["GCP"]},
    {"name": "Docker", "domain": Domain.CLOUD_DEVOPS, "aliases": ["Containerization"]},
    {"name": "Kubernetes", "domain": Domain.CLOUD_DEVOPS, "aliases": ["K8s", "Container Orchestration"]},
    {"name": "Terraform", "domain": Domain.CLOUD_DEVOPS, "aliases": ["Infrastructure as Code", "IaC"]},
    {"name": "CI/CD", "domain": Domain.CLOUD_DEVOPS, "aliases": ["Continuous Integration", "Continuous Deployment"]},
    {"name": "Linux Administration", "domain": Domain.CLOUD_DEVOPS, "aliases": ["Unix", "Shell Scripting", "Bash"]},

    # --- ml_ai ---
    {"name": "Machine Learning", "domain": Domain.ML_AI, "aliases": ["ML"]},
    {"name": "Deep Learning", "domain": Domain.ML_AI, "aliases": ["Neural Networks", "DL"]},
    {"name": "Natural Language Processing", "domain": Domain.ML_AI, "aliases": ["NLP"]},
    {"name": "Computer Vision", "domain": Domain.ML_AI, "aliases": ["CV", "Image Processing"]},
    {"name": "PyTorch", "domain": Domain.ML_AI, "aliases": []},
    {"name": "TensorFlow", "domain": Domain.ML_AI, "aliases": ["Keras"]},
    {"name": "Large Language Models", "domain": Domain.ML_AI, "aliases": ["LLM", "LLMs", "Generative AI", "GenAI"]},

    # --- data_engineering ---
    {"name": "Apache Spark", "domain": Domain.DATA_ENGINEERING, "aliases": ["Spark", "PySpark"]},
    {"name": "Apache Kafka", "domain": Domain.DATA_ENGINEERING, "aliases": ["Kafka", "Event Streaming"]},
    {"name": "ETL Pipelines", "domain": Domain.DATA_ENGINEERING, "aliases": ["ETL", "Data Pipelines"]},
    {"name": "Apache Airflow", "domain": Domain.DATA_ENGINEERING, "aliases": ["Airflow", "Workflow Orchestration"]},
    {"name": "Pandas", "domain": Domain.DATA_ENGINEERING, "aliases": ["Data Wrangling"]},

    # --- testing_qa ---
    {"name": "Unit Testing", "domain": Domain.TESTING_QA, "aliases": ["Test-Driven Development", "TDD"]},
    {"name": "Selenium", "domain": Domain.TESTING_QA, "aliases": ["Browser Automation"]},
    {"name": "Test Automation", "domain": Domain.TESTING_QA, "aliases": ["Automated Testing", "QA Automation"]},
    {"name": "Pytest", "domain": Domain.TESTING_QA, "aliases": []},

    # --- security ---
    {"name": "Application Security", "domain": Domain.SECURITY, "aliases": ["AppSec", "Secure Coding"]},
    {"name": "OAuth Authentication", "domain": Domain.SECURITY, "aliases": ["OAuth2", "OAuth 2.0", "SSO"]},
    {"name": "Penetration Testing", "domain": Domain.SECURITY, "aliases": ["Pen Testing", "Ethical Hacking"]},

    # --- tools_other ---
    {"name": "Git", "domain": Domain.TOOLS_OTHER, "aliases": ["GitHub", "GitLab", "Version Control"]},
    {"name": "Jira", "domain": Domain.TOOLS_OTHER, "aliases": ["Atlassian Jira"]},
    {"name": "Agile Scrum", "domain": Domain.TOOLS_OTHER, "aliases": ["Agile", "Scrum", "Kanban"]},
    {"name": "System Design", "domain": Domain.TOOLS_OTHER, "aliases": ["Distributed Systems Design"]},
    {"name": "Microservices Architecture", "domain": Domain.TOOLS_OTHER, "aliases": ["Microservices", "Service-Oriented Architecture"]},

    # --- soft_skill ---
    {"name": "Communication", "domain": Domain.SOFT_SKILL, "aliases": ["Written Communication", "Verbal Communication"]},
    {"name": "Leadership", "domain": Domain.SOFT_SKILL, "aliases": ["Team Leadership", "Mentoring"]},
]


# ---------------------------------------------------------------------------
# Derived lookups consumed by embeddings.py / agent_extractor.py
# ---------------------------------------------------------------------------

SKILL_NAMES: list[str] = [s["name"] for s in SKILL_TAXONOMY]

NAME_TO_DOMAIN: dict[str, str] = {s["name"]: s["domain"] for s in SKILL_TAXONOMY}

# lowercased alias/name -> canonical name, for a cheap exact-match pass before
# falling back to embedding similarity
ALIAS_TO_CANONICAL: dict[str, str] = {
    variant.lower(): s["name"]
    for s in SKILL_TAXONOMY
    for variant in [s["name"], *s["aliases"]]
}


def all_name_variants() -> list[tuple[str, str]]:
    """Returns [(canonical_name, surface_form), ...] with one row per
    canonical name AND per alias — each surface form gets its own embedding
    point rather than being diluted into one combined "name (aliases)"
    string, so a bare JD mention of the canonical name itself (e.g. "Django")
    still scores a near-exact match against its own embedding instead of
    being pulled down by unrelated alias text sharing the same vector."""
    pairs: list[tuple[str, str]] = []
    for s in SKILL_TAXONOMY:
        pairs.append((s["name"], s["name"]))
        for alias in s["aliases"]:
            pairs.append((s["name"], alias))
    return pairs
