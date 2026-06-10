"""
启动本地 HTTP 服务器 + Cloudflare Tunnel，提供公网 HTTPS 访问。

用法:
  python serve_reports.py --dir <报告目录> [--port 8899]

核心设计（Windows 进程存活保证）:
  1. HTTP 服务器以 DETACHED_PROCESS 启动 → 脱离父进程作业对象，shell 关闭后继续运行
  2. cloudflared 以 DETACHED_PROCESS 启动，stdout 重定向到日志文件
  3. 脚本轮询日志文件获取 trycloudflare URL（最长 30s）
  4. 保存链接 → 脚本退出，两个子进程持续在后台运行

终止方法:
  taskkill /F /IM python.exe  (子进程)
  taskkill /F /IM cloudflared.exe
"""
import argparse
import subprocess
import os
import sys
import time
import re
import json
from datetime import datetime


# Windows 进程脱离标志：子进程不随父进程会话结束而被杀
if sys.platform == 'win32':
    DETACHED_FLAGS = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
else:
    DETACHED_FLAGS = 0


def start_http_server_detached(directory, port):
    """以完全脱离的独立进程启动 HTTP 服务器。返回 Popen 对象。"""
    server_script = (
        f"import http.server, socketserver, sys, os\n"
        f"os.chdir(r'{directory}')\n"
        f"class Q(http.server.SimpleHTTPRequestHandler):\n"
        f"    def log_message(self, *a): pass\n"
        f"socketserver.TCPServer.allow_reuse_address = True\n"
        f"with socketserver.TCPServer(('', {port}), Q) as httpd:\n"
        f"    httpd.serve_forever()\n"
    )

    proc = subprocess.Popen(
        [sys.executable, '-c', server_script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=DETACHED_FLAGS,
    )
    print(f"[HTTP] 本地服务器已启动: http://localhost:{port}  (pid={proc.pid})")
    return proc


def start_cloudflared_detached(directory, port):
    """
    以脱离进程启动 cloudflared，stdout+stderr 写入日志文件。
    返回 (Popen, log_file_path)。
    """
    cf_log = os.path.join(directory, '.cf_tunnel.log')
    # 清空旧日志
    with open(cf_log, 'w') as f:
        f.write('')

    cf_log_fh = open(cf_log, 'a')

    try:
        proc = subprocess.Popen(
            ['cloudflared', 'tunnel', '--url', f'http://localhost:{port}', '--no-autoupdate'],
            stdout=cf_log_fh,
            stderr=subprocess.STDOUT,
            creationflags=DETACHED_FLAGS,
        )
    except FileNotFoundError:
        cf_log_fh.close()
        print("[错误] 未安装 cloudflared。安装方法:")
        print("  winget install cloudflare.cloudflared")
        print("  或: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/")
        return None, None
    finally:
        cf_log_fh.close()

    print(f"[CF] 启动 Cloudflare Tunnel (pid={proc.pid})...")
    return proc, cf_log


def poll_for_tunnel_url(log_file, timeout=30):
    """轮询日志文件，等待 cloudflared 输出 trycloudflare URL。返回 URL 或 None。"""
    url_pattern = re.compile(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com')
    deadline = time.time() + timeout

    last_size = 0
    while time.time() < deadline:
        try:
            current_size = os.path.getsize(log_file)
        except OSError:
            time.sleep(0.5)
            continue

        if current_size > last_size:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                f.seek(last_size)
                new_content = f.read()

            for line in new_content.splitlines():
                line = line.strip()
                if line:
                    print(f"  [CF] {line}")
                match = url_pattern.search(line)
                if match:
                    return match.group(0)

            last_size = current_size

        time.sleep(0.5)

    return None


def list_served_files(directory):
    """列出目录下所有可访问的 .html / .md / .txt / .json 文件"""
    files = []
    for root, dirs, filenames in os.walk(directory):
        # 跳过隐藏文件
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for fn in filenames:
            if fn.startswith('.'):
                continue
            if fn.endswith(('.html', '.md', '.txt', '.json')):
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, directory).replace('\\', '/')
                files.append(rel)
    return sorted(files)


def find_main_page(directory):
    """查找主页面：优先 consolidated-reports.html"""
    for c in ['consolidated-reports.html', 'index.html']:
        path = os.path.join(directory, c)
        if os.path.exists(path):
            return c
    for f in os.listdir(directory):
        if f.endswith('.html') and 'consolidated' in f:
            return f
    for f in os.listdir(directory):
        if f.endswith('.html'):
            return f
    return None


def generate_index_redirect(directory):
    """生成 index.html 重定向到 consolidated-reports.html"""
    main_page = find_main_page(directory)
    if not main_page or main_page == 'index.html':
        return
    index_html = f'''<!DOCTYPE html>
<html><head>
<meta http-equiv="refresh" content="0;url={main_page}">
<title>Redirecting...</title>
</head><body>
<p>Redirecting to <a href="{main_page}">{main_page}</a>...</p>
</body></html>'''
    path = os.path.join(directory, 'index.html')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(index_html)
    print(f"[OK] index.html -> {main_page}")


def save_links(directory, tunnel_url, files):
    """保存链接到 tunnel_links.json 和 tunnel_links.txt"""
    main_page = find_main_page(directory) or 'consolidated-reports.html'
    main_url = f"{tunnel_url}/{main_page}"
    links = {
        "base": tunnel_url,
        "main_page": main_url,
        "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "files": {}
    }
    for f in files:
        links["files"][f] = f"{tunnel_url}/{f}"

    # JSON
    json_path = os.path.join(directory, 'tunnel_links.json')
    with open(json_path, 'w', encoding='utf-8') as fh:
        json.dump(links, fh, ensure_ascii=False, indent=2)
    print(f"[OK] 链接 JSON: {json_path}")

    # TXT
    txt_path = os.path.join(directory, 'tunnel_links.txt')
    with open(txt_path, 'w', encoding='utf-8') as fh:
        fh.write(f"Cloudflare Tunnel\n")
        fh.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        fh.write(f"{'='*60}\n\n")
        fh.write(f">>> 主页面 (交互式仪表盘): {main_url}\n\n")
        fh.write(f"所有文件:\n")
        for fname, url in links["files"].items():
            fh.write(f"  {fname}: {url}\n")
    print(f"[OK] 链接文本: {txt_path}")

    return links


def main():
    parser = argparse.ArgumentParser(description='启动报告服务器 + Cloudflare Tunnel')
    parser.add_argument('--dir', required=True, help='报告目录')
    parser.add_argument('--port', type=int, default=8899, help='本地端口 (默认 8899)')
    parser.add_argument('--no-serve', action='store_true', help='仅生成 index.html 重定向')
    parser.add_argument('--timeout', type=int, default=30, help='等待 Tunnel URL 的超时秒数')
    args = parser.parse_args()

    directory = os.path.abspath(args.dir)
    if not os.path.isdir(directory):
        print(f"[错误] 目录不存在: {directory}")
        sys.exit(1)

    # 生成 index.html 重定向
    generate_index_redirect(directory)

    # 列出文件
    files = list_served_files(directory)
    main_page = find_main_page(directory) or '(none)'
    print(f"\n[INFO] 报告目录: {directory}")
    print(f"[INFO] 主页面: {main_page}")
    print(f"[INFO] 可访问文件: {len(files)} 个")

    if args.no_serve:
        print("[INFO] --no-serve 模式，跳过服务器启动")
        return

    # ─── 1. 启动 HTTP 服务器（DETACHED，脱离父进程） ───
    http_proc = start_http_server_detached(directory, args.port)
    time.sleep(1)

    if http_proc.poll() is not None:
        print("[错误] HTTP 服务器启动失败（进程已退出）")
        sys.exit(1)

    # ─── 2. 启动 cloudflared（DETACHED，输出到日志文件） ───
    cf_proc, cf_log = start_cloudflared_detached(directory, args.port)

    if cf_proc is None:
        # cloudflared 未安装
        # 终止 HTTP 服务器
        http_proc.terminate()
        sys.exit(1)

    # ─── 3. 轮询日志文件获取 URL ───
    print(f"[INFO] 等待 Cloudflare Tunnel URL（最长 {args.timeout}s）...")
    tunnel_url = poll_for_tunnel_url(cf_log, timeout=args.timeout)

    if not tunnel_url:
        print(f"[错误] {args.timeout}s 内未获取到 Cloudflare Tunnel URL")
        print(f"[提示] 日志文件: {cf_log}")
        print(f"[提示] HTTP 服务器 pid={http_proc.pid} 仍在运行")
        print(f"[提示] 可手动检查: curl http://localhost:{args.port}/")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"[OK] 公网访问链接: {tunnel_url}")
    print(f"{'='*60}\n")

    # ─── 4. 保存链接 ───
    links = save_links(directory, tunnel_url, files)

    # ─── 5. 输出汇总并退出（子进程继续运行） ───
    print(f"\n[汇总] 公网访问:")
    print(f"  >>> 仪表盘主页面: {links['main_page']}")
    print(f"  基础 URL:         {tunnel_url}")
    print(f"\n[进程] HTTP server pid={http_proc.pid}  |  cloudflared pid={cf_proc.pid}")
    print(f"[提示] 两个进程已脱离父进程，关闭本终端后仍继续运行")
    print(f"[提示] 停止服务:")
    print(f"  taskkill /F /PID {http_proc.pid}")
    print(f"  taskkill /F /PID {cf_proc.pid}")
    print(f"\n[OK] 链接文件:")
    print(f"  {os.path.join(directory, 'tunnel_links.json')}")
    print(f"  {os.path.join(directory, 'tunnel_links.txt')}")
    print(f"\n[OK] 脚本退出，服务继续运行。")


if __name__ == '__main__':
    main()
