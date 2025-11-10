from setuptools import setup, find_packages

setup(
    name="{{project-name}}",
    version="0.1.0",
    description="{{ProjectDescription}}",
    author="{{AuthorName}}",
    packages=find_packages(),
    install_requires=[
        "pydantic>=2.0.0",
        "jinja2>=3.1.0",
        "pyyaml>=6.0",
        "python-frontmatter>=1.0.0",
        "pathspec>=0.11.0",
    ],
    entry_points={
        "console_scripts": [
            "{{project-name}}={{project_name}}.cli.main:main",
        ],
    },
    python_requires=">=3.9",
)
