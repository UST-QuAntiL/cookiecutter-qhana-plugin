from pathlib import Path
from shlex import join
from typing import List

from dotenv import load_dotenv
from invoke import task
from invoke.runners import Result

load_dotenv(".flaskenv")
load_dotenv(".env")


# FIXME change this name after renaming the flask template package!
MODULE_NAME = "flask_template"


@task
def doc(c, format_="html", all_=False, color=True):
    """Build the documentation.

    Args:
        c (Context): task context
        format_ (str, optional): the format to build. Defaults to "html".
        all (bool, optional): build all files new. Defaults to False.
        color (bool, optional): color output. Defaults to True.
    """
    cmd = ["sphinx-build", "-b", format_]
    if all_:
        cmd.append("-a")
    if color:
        cmd.append("--color")
    else:
        cmd.append("--no-color")
    cmd += [".", "_build"]
    with c.cd(str(Path("./docs"))):
        c.run(join(cmd), echo=True)


@task
def browse_doc(c):
    """Open the documentation in the browser.

    Args:
        c (Context): task context
    """
    index_path = Path("./docs/_build/html/index.html")
    if not index_path.exists():
        doc(c)

    print(f"Open: file://{index_path.resolve()}")
    import webbrowser

    webbrowser.open_new_tab(str(index_path.resolve()))


@task
def doc_index(c, filter_=""):
    """Search the index of referencable sphinx targets in the documentation.

    Args:
        c (Context): task context
        filter_ (str, optional): an optional filter string. Defaults to "".
    """
    inv_path = Path("./docs/_build/html/objects.inv")
    if not inv_path.exists():
        doc(c)

    if filter_:
        filter_ = filter_.lower()

    with c.cd(str(Path("./docs"))):
        output: Result = c.run(
            join(["python", "-m", "sphinx.ext.intersphinx", "_build/html/objects.inv"]),
            echo=True,
            hide="stdout",
        )
        print(
            "".join(
                l
                for l in output.stdout.splitlines(True)
                if (l and not l[0].isspace()) or (not filter_) or (filter_ in l.lower())
            ),
        )


{%- if cookiecutter.use_poetry == 'y' %}
@task()
def update_dependencies(c):
    """Update dependencies that are derived from the pyproject.toml dependencies (e.g. doc dependencies).

    Args:
        c (Context): task context
    """
    c.run(
        join(
            [
                "poetry",
                "export",
                "--dev",
                "--format",
                "requirements.txt",
                "--output",
                str(Path("./docs/requirements.txt")),
            ]
        ),
        echo=True,
        hide="err",
        warn=True,
    )
{%- endif %}

