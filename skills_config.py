"""Static skill taxonomy, recommendations, and job matrix."""

# Raw GitHub language/keyword -> canonical skill id
SKILL_MAP = {
    # Languages
    "python": "python", "javascript": "javascript", "typescript": "typescript",
    "java": "java", "go": "go", "rust": "rust", "c++": "cpp", "c": "c",
    "c#": "csharp", "ruby": "ruby", "php": "php", "swift": "swift",
    "kotlin": "kotlin", "scala": "scala", "shell": "bash", "dockerfile": "docker",
    "html": "html", "css": "css", "r": "r", "lua": "lua", "dart": "dart",
    # Frameworks / tools (README / package.json keywords)
    "react": "react", "vue": "vue", "angular": "angular", "next": "nextjs",
    "nuxt": "nuxt", "django": "django", "flask": "flask", "fastapi": "fastapi",
    "express": "express", "spring": "spring", "rails": "rails", "laravel": "laravel",
    "docker": "docker", "kubernetes": "kubernetes", "k8s": "kubernetes",
    "aws": "aws", "gcp": "gcp", "azure": "azure", "terraform": "terraform",
    "ansible": "ansible", "postgres": "postgresql", "postgresql": "postgresql",
    "mysql": "mysql", "mongodb": "mongodb", "redis": "redis",
    "graphql": "graphql", "pytorch": "pytorch", "tensorflow": "tensorflow",
    "pandas": "pandas", "numpy": "numpy", "scikit": "sklearn",
}

# Skill -> suggested next skills
SKILL_LEADS_TO = {
    "python":     ["fastapi", "django", "pytorch", "sklearn"],
    "javascript": ["typescript", "react", "nodejs", "nextjs"],
    "typescript": ["react", "nextjs", "nodejs"],
    "react":      ["nextjs", "typescript", "graphql"],
    "java":       ["spring", "kubernetes", "scala"],
    "go":         ["kubernetes", "docker", "grpc"],
    "docker":     ["kubernetes", "terraform", "aws"],
    "kubernetes": ["terraform", "aws", "sre"],
    "django":     ["postgresql", "redis", "fastapi"],
    "fastapi":    ["postgresql", "redis", "docker"],
    "pytorch":    ["tensorflow", "sklearn", "mlops"],
    "aws":        ["terraform", "kubernetes", "serverless"],
}

# Job titles -> required skills + salary band
JOB_MATRIX = [
    ("Backend Engineer",    ["python", "django", "postgresql", "docker"],    "$105K-$145K"),
    ("Frontend Engineer",   ["javascript", "react", "typescript", "css"],    "$95K-$130K"),
    ("Full Stack Engineer", ["javascript", "react", "nodejs", "postgresql"], "$110K-$148K"),
    ("DevOps / SRE",        ["docker", "kubernetes", "terraform", "linux"],  "$120K-$160K"),
    ("Data Scientist",      ["python", "pandas", "sklearn", "pytorch"],      "$110K-$155K"),
    ("ML Engineer",         ["python", "pytorch", "tensorflow", "docker"],   "$125K-$170K"),
    ("Cloud Architect",     ["aws", "terraform", "kubernetes", "docker"],    "$140K-$185K"),
    ("Mobile Engineer",     ["swift", "kotlin", "react"],                    "$105K-$145K"),
    ("Platform Engineer",   ["kubernetes", "go", "docker", "terraform"],     "$135K-$175K"),
]

# Canonical skill id -> brand color
LANG_COLOR = {
    "python": "#3572A5", "javascript": "#f1e05a", "typescript": "#3178c6",
    "java": "#b07219", "go": "#00ADD8", "rust": "#dea584", "cpp": "#f34b7d",
    "c": "#555555", "csharp": "#178600", "ruby": "#701516", "php": "#4F5D95",
    "swift": "#FA7343", "kotlin": "#7F52FF", "html": "#e34c26", "css": "#563d7c",
    "shell": "#89e051", "bash": "#89e051", "docker": "#2496ED",
}

# Fallback palette when a skill has no brand color
PALETTE = [
    "#00ffcc", "#00ccff", "#7c3aed", "#f59e0b",
    "#10b981", "#3b82f6", "#ec4899", "#f97316",
]
