#!/usr/bin/env bash
set -uo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/.venv"
PID_FILE="$APP_DIR/fpbrowser2api.pid"
LOG_FILE="$APP_DIR/fpbrowser2api.out"

echo "========================================="
echo "  fpbrowser2api 一键启动脚本"
echo "========================================="

# ─── 代理配置 ───
export http_proxy="http://127.0.0.1:7897"
export https_proxy="http://127.0.0.1:7897"
export ALL_PROXY="http://127.0.0.1:7897"
echo "[*] 已启用代理: 127.0.0.1:7897"

# ─── 0. 确保 Python 3.10 可用 ───
PYTHON_BIN=""
if command -v python3.10 >/dev/null 2>&1; then
  PYTHON_BIN="python3.10"
elif [[ -x "/opt/homebrew/bin/python3.10" ]]; then
  PYTHON_BIN="/opt/homebrew/bin/python3.10"
elif [[ -x "/usr/local/bin/python3.10" ]]; then
  PYTHON_BIN="/usr/local/bin/python3.10"
else
  echo "[*] 未找到 Python 3.10，正在通过 Homebrew 安装..."
  if ! command -v brew >/dev/null 2>&1; then
    echo "[✗] 未找到 Homebrew，请先安装: https://brew.sh"
    echo ""
    echo "按回车键退出..."
    read -r
    exit 1
  fi
  brew install python@3.10
  if [[ -x "/opt/homebrew/bin/python3.10" ]]; then
    PYTHON_BIN="/opt/homebrew/bin/python3.10"
  elif [[ -x "/usr/local/bin/python3.10" ]]; then
    PYTHON_BIN="/usr/local/bin/python3.10"
  else
    echo "[✗] 安装后仍找不到 python3.10，请手动检查"
    echo ""
    echo "按回车键退出..."
    read -r
    exit 1
  fi
fi
echo "[✓] 使用 Python: $PYTHON_BIN ($($PYTHON_BIN --version))"

# ─── 1. 进程管理：杀掉旧进程 ───
kill_old_process() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE")"
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      echo "[*] 检测到旧进程 (pid=$pid)，正在停止..."
      kill "$pid" 2>/dev/null || true
      for _ in $(seq 1 10); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
      done
      if kill -0 "$pid" 2>/dev/null; then
        echo "[*] 优雅停止超时，强制杀掉进程"
        kill -9 "$pid" 2>/dev/null || true
      fi
      echo "[✓] 旧进程已停止"
    fi
    rm -f "$PID_FILE"
  fi

  # 额外检查：按端口杀残留进程
  local port_pid
  port_pid="$(lsof -ti:8000 2>/dev/null || true)"
  if [[ -n "$port_pid" ]]; then
    echo "[*] 端口 8000 被占用 (pid=$port_pid)，正在释放..."
    kill "$port_pid" 2>/dev/null || true
    sleep 1
  fi
}

# ─── 2. 创建虚拟环境 & 安装依赖 ───
setup_deps() {
  # 检查 venv 是否存在且版本正确
  if [[ -d "$VENV_DIR" ]]; then
    local current_ver
    current_ver="$("$VENV_DIR/bin/python" --version 2>/dev/null || echo "")"
    if [[ "$current_ver" != *"3.10"* ]]; then
      echo "[*] 虚拟环境 Python 版本不匹配，重新创建..."
      rm -rf "$VENV_DIR"
    fi
  fi

  if [[ ! -d "$VENV_DIR" ]]; then
    echo "[*] 创建 Python 3.10 虚拟环境..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  echo "[*] 安装 Python 依赖..."
  "$VENV_DIR/bin/pip" install -q --upgrade pip
  "$VENV_DIR/bin/pip" install -q -r "$APP_DIR/requirements.txt"
  echo "[✓] 依赖安装完成"
}

# ─── 3. 启动服务 ───
start_server() {
  cd "$APP_DIR"
  : > "$LOG_FILE"

  echo "[*] 启动 fpbrowser2api..."
  nohup "$VENV_DIR/bin/python" main.py >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"

  sleep 2
  local pid
  pid="$(cat "$PID_FILE")"
  if kill -0 "$pid" 2>/dev/null; then
    echo "[✓] 启动成功 (pid=$pid)"
    echo "[✓] 服务地址: http://localhost:8000"
    echo "[✓] 日志文件: $LOG_FILE"
  else
    echo "[✗] 启动失败，查看日志:"
    tail -20 "$LOG_FILE"
    exit 1
  fi
}

# ─── 执行 ───
kill_old_process
setup_deps
start_server

echo "========================================="
echo "  启动完毕！按 Ctrl+C 不会停止后台服务"
echo "  停止服务: ./fpbrowser2api_service.sh stop"
echo "========================================="

echo ""
echo "按回车键退出..."
read -r
