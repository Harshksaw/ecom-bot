# ecom-bot

## Setup Instructions

### Check if uv is installed
```bash
uv --version
```

### Install uv (if not installed)
```bash
pip install uv
```

### Check uv location
```python
import shutil
print(shutil.which("uv"))
```

### Initialize a new project
```bash
uv init <my-project-name>
```

### List available Python versions
```bash
uv python list
```

### Create virtual environment
```bash
uv venv env --python 3.10
```

### Activate virtual environment
```bash
source env/bin/activate
```

### Package management
```bash
# List installed packages
uv pip list

# Install a package
uv pip install <package-name>

# Install from requirements.txt
uv pip install -r requirements.txt
```

### Run the project
```bash
python main.py
```