#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
venv_dir="${LINUXCUE_VENV_DIR:-${HOME}/.local/share/linuxcue/venv}"
launcher_dir="${HOME}/.local/bin"
launcher_path="${launcher_dir}/linuxcue"

mkdir -p "$(dirname "$venv_dir")"
python -m venv --system-site-packages "$venv_dir"
source "$venv_dir/bin/activate"
if [ -f "$venv_dir/pyvenv.cfg" ]; then
  python - <<'PY'
from pathlib import Path
import os
cfg = Path(os.environ["VIRTUAL_ENV"]) / "pyvenv.cfg"
text = cfg.read_text(encoding="utf-8")
lines = []
seen = False
for line in text.splitlines():
    if line.startswith("include-system-site-packages"):
        lines.append("include-system-site-packages = true")
        seen = True
    else:
        lines.append(line)
if not seen:
    lines.append("include-system-site-packages = true")
cfg.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
fi
python -m pip install --upgrade pip
python -m pip install -e "$repo_root[hid]"

if ! python -c "import PySide6" >/dev/null 2>&1; then
  echo "Warning: PySide6/Qt is not available."
  echo "Install the QML GUI dependency on CachyOS with: sudo pacman -S --needed pyside6 qt6-declarative"
  echo "Then rerun this installer."
fi
if command -v easyeffects >/dev/null 2>&1 && [ ! -d /usr/lib/lv2/lsp-plugins.lv2 ]; then
  echo "Warning: EasyEffects is installed but Linux Studio Plugins are missing."
  echo "Install Virtuoso EQ backend plugins on CachyOS with: sudo pacman -S --needed lsp-plugins-lv2"
fi

mkdir -p "$launcher_dir"
cat > "$launcher_path" <<EOF
#!/usr/bin/env bash
exec "$venv_dir/bin/linuxcue" "\$@"
EOF
chmod +x "$launcher_path"

echo "Development install complete."
echo "Virtual environment: $venv_dir"
echo "Launcher: $launcher_path"
echo "Install udev rules with: bash \"$repo_root/scripts/install-udev-rules.sh\""
echo "Start with: $launcher_path gui"
echo "Fish shell activation: source \"$venv_dir/bin/activate.fish\""
echo "Bash/Zsh activation: source \"$venv_dir/bin/activate\""
