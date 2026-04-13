# Multimodal_Ninja_Fruit
Game developed by DVD Project Blue team.

### Set up environment

To create an environment with all needed dependencies create conda env, uv env or venv with:
```bash
# create and activate venv (POSIX)
python -m venv .venv
source .venv/bin/activate

# (Windows PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

In you env run:
```bash
pip install -e .
```

### How to start the game

Open a terminal, change to the project's directory, and run the command below to launch the game:

```bash
python run_game.py
```

**Note for systems where `python` refers to Python 2.x**

This project requires Python 3. On some older systems the `python` command invokes Python 2 (e.g., 2.7). If `python --version` shows `Python 2.x`, start the game with:

```bash
python3 run_game.py
```

### How to run Vosk listener part

Install system dependency (Linux):

```bash
sudo apt update
sudo apt install -y portaudio19-dev
```