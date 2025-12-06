# nbconvert configuration for LLM-friendly markdown output
# Usage: uv run jupyter nbconvert --to markdown --config jupyter_nbconvert_config.py --template plaintext notebook.ipynb

c.NbConvertBase.display_data_priority = [
    "text/plain",
    "text/markdown",
    "image/png",
    "image/jpeg",
    "image/svg+xml",
    "text/latex",
    "application/pdf",
    "text/html",
]

c.TemplateExporter.extra_template_basedirs = ["nbconvert_templates"]
