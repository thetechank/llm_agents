# AI Workshop Demo Code

This repository folder contains code that was demostrated in the AI Workshop

The code is python and thus you need to have a python environment.

As you might know the pain with python env, it is best to use a python package manager or version manager.

[UV](https://docs.astral.sh/uv/) is presently state of the art and used in many production systems.

This folder was setup with UV. Feel free to use other package managers but UV is no-brainer at the moment

There is requirements.txt that helps if you want to use normal pip.

## Disclaimers

- Do not commit your OpenAI Keys by accident.
- use the .env.example for example

## UV commands

```python
uv init
uv sync
```

This creates a python environment and install the stuff. Then you can run python files withj `uv run`
For notebooks select the right kernel pointing to the correct virtual env. It will be `.venv` in the current folder
