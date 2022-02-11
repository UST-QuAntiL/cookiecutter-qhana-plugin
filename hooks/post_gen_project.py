import re

from json import loads
from pathlib import Path
from urllib import request
from http.client import HTTPResponse
from textwrap import wrap
from datetime import date

# the cookiecutter configuration
config = loads('''{{cookiecutter|jsonify}}''')

# url to the json data of spdx
spdx_licenses_json = "https://raw.githubusercontent.com/spdx/license-list-data/master/json/licenses.json"

def remove_unused_files():
    """Remove files that are not used because of the template configuration."""
    poetry = config["use_poetry"].lower().startswith("y")
    flake8 = config["use_flake8"].lower().startswith("y")
    vscode = config["configure_vscode"].lower().startswith("y")

    to_remove = []
    if poetry:
        to_remove.extend([Path("requirements.txt"), Path("dev-requirements.txt")])
    if not flake8:
        to_remove.append(Path(".flake8"))
    if not vscode:
        to_remove.append(Path(".vscode"))

    path: Path
    for path in to_remove:
        if not path.exists():
            continue
        if path.is_file():
            path.unlink(True)
        elif path.is_dir():
            for p in path.iterdir():
                p.unlink(True)
            path.rmdir()

def add_instance_path():
    """Add the current folder as instance path."""
    instance_path = Path(".") / Path("instance")
    with Path(".env").open("at") as env:
        env.writelines([
            "# configure the instance path to be inside the project folder",
            f"QHANA_PLUGIN_RUNNER_INSTANCE_FOLDER={instance_path.resolve()}",
            ""
        ])

def save_license_detail(license_):
    """Save the license text downloaded from SPDX as LICENSE."""
    if license_["isDeprecatedLicenseId"]:
        print("\n\nThe chosen license is marked as deprecated!!!\n\n")
    license_detail: HTTPResponse
    with request.urlopen(license_["detailsUrl"], timeout=15) as license_detail, Path("LICENSE").open("wt") as license_file:
        if license_detail.status != 200:
            print("Could not fetch license detail information. Aborting")
        detail_json = loads(license_detail.read().decode("utf-8"))
        text = (
            detail_json["licenseText"]
                .replace("<year>", str(date.today().year))
                .replace("<copyright holders>", config["full_name"])
        )

        wrapped_lines = []
        for paragraph in text.splitlines():
            wrapped = wrap(paragraph, width=80, break_long_words=False, break_on_hyphens=False, drop_whitespace=False, expand_tabs=False, replace_whitespace=False)
            indent = ""
            for i, l in enumerate(wrapped):
                if i == 0:
                    # grab indent from first line
                    match = re.match(r"^\s+", l)
                    if match:
                        indent = match.string
                else:
                    # remove a single space from following lines if it is not followed by more spaces
                    # also add current indent to the line
                    wrapped_lines.append(indent + re.sub(r"^ (?! )", "", l))

        license_file.writelines(wrapped_lines)

def check_license():
    """Check license and download the license file."""
    licenses: HTTPResponse
    with request.urlopen(spdx_licenses_json, timeout=15) as licenses:
        if licenses.status != 200:
            print("Could not fetch license information. Aborting")
        licenses_json = loads(licenses.read().decode("utf-8"))
        matching = [l for l in licenses_json["licenses"] if l["licenseId"] == config["plugin_license"]]
        if not matching:
            print(f"Could not match license config['plugin_license'] to an SPDX license id.")
            return
        if len(matching) > 1:
            print(f"Found more than one matching license for config['plugin_license'].")
            return
        save_license_detail(matching[0])

if __name__=="__main__":
    remove_unused_files()
    add_instance_path()
    check_license()
