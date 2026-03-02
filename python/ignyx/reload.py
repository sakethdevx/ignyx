def run_with_reload(
    app_module: str, app_attr: str = "app", host: str = "0.0.0.0", port: int = 8000
) -> None:
    """
    Run the Ignyx application with hot reload enabled.
    """
    try:
        import watchfiles
    except ImportError:
        raise ImportError("Hot reload requires watchfiles: pip install ignyx[reload]")

    import subprocess
    import sys

    print("🔄 Ignyx hot reload enabled — watching *.py files")
    cmd = [
        sys.executable,
        "-c",
        f"import importlib; m = importlib.import_module('{app_module}'); "
        f"getattr(m, '{app_attr}').run(host='{host}', port={port})",
    ]
    proc: subprocess.Popen[bytes] | None = None

    def start() -> None:
        nonlocal proc
        if proc:
            proc.terminate()
        proc = subprocess.Popen(cmd)

    start()
    try:
        for changes in watchfiles.watch(".", watch_filter=watchfiles.PythonFilter()):
            print("🔄 Change detected, reloading...")
            start()
    except KeyboardInterrupt:
        if proc:
            proc.terminate()
