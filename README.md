# Cookiecutter for QHAna Plugins

[Cookiecutter](https://github.com/cookiecutter/cookiecutter) template for a new QHAna plugin.

Documentation: <https://cookiecutter-pypackage.readthedocs.io/>


## Installing Cookiecutter

Using pip:

```bash
pip install -U cookiecutter
```

Using [pipx](https://pypa.github.io/pipx/):

```bash
pipx install cookiecutter
```

## Instantiating This Template

 1. Go to the directory where you want to create the new project folder.
 2. Instantiate the cookiecutter template
    ```bash
    cookiecutter gh:UST-QuAntiL/cookiecutter-qhana-plugin
    ```
    Answer the question prompts.
 3. Cd into the created project folder
 4. Run `git init` to initialize a git repository in the project folder
 5. Commit initial template
 6. Create a new and *empty* GitHub repository online and follow the instructions for uploading an existing local git repository


### Generated Files

The template generates a plugin skeleton in two variants:

 1. A single file python module for smaller plugin implementations.
 2. A python package for plugins that require more code.

Delete the variant you don't want to use!
