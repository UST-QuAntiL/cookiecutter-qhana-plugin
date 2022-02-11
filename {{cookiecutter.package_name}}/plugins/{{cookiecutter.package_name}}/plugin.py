from textwrap import dedent
from typing import Any, Mapping, Optional, List, Dict, Tuple

from flask import Flask

from qhana_plugin_runner.util.plugins import QHAnaPluginBase, plugin_identifier

# plugin identifying constants (in extra module to avoid circular dependencies)
_plugin_name = "{{cookiecutter.plugin_identifier}}"
__version__ = "{{cookiecutter.plugin_version}}"
_identifier = plugin_identifier(_plugin_name, __version__) # full identifier including version


# just importing the plugin class creates the plugin instance in {{cookiecutter.base_classname}}.instance
class {{cookiecutter.base_classname}}(QHAnaPluginBase):
    """{{cookiecutter.description}}"""

    name = _plugin_name
    version = __version__

    def __init__(self, app: Optional[Flask]) -> None:
        super().__init__(app)

    def get_api_blueprint(self):
        from .api import PLUGIN_BLP # import blueprint only after plugin instance was created
        return PLUGIN_BLP

    def get_requirements(self):
        return dedent("""# place your plugin requirements in here
        """)
