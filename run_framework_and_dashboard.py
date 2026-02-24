import os
import sys
import subprocess
import time


def main() -> None:
    """Lanza el framework (CLI) y el dashboard de Streamlit al mismo tiempo.

    - Arranca Streamlit en segundo plano.
    - Luego arranca simple_trading_app con la CLI interactiva en primer plano.
    """
    project_root = os.path.dirname(os.path.abspath(__file__))
    python_exe = sys.executable  # Usa el mismo intérprete/venv con el que se ejecuta este script

    env = os.environ.copy()
    # Asegura que el proyecto esté en PYTHONPATH por si se ejecuta desde otro directorio
    env["PYTHONPATH"] = project_root + os.pathsep + env.get("PYTHONPATH", "")

    # Comando para Streamlit
    streamlit_cmd = [
        python_exe,
        "-m",
        "streamlit",
        "run",
        os.path.join(project_root, "streamlit_app.py"),
        "--server.address",
        "0.0.0.0",
        "--server.port",
        "8501",
    ]

    print("Lanzando dashboard de Streamlit en segundo plano...")
    try:
        streamlit_proc = subprocess.Popen(
            streamlit_cmd,
            cwd=project_root,
            env=env,
        )
    except Exception as e:
        print(f"No se pudo iniciar Streamlit: {e}")
        streamlit_proc = None

    # Dar unos segundos para que Streamlit arranque
    time.sleep(3)

    # Comando para el framework principal (CLI)
    framework_cmd = [
        python_exe,
        os.path.join(project_root, "simple_trading_app.py"),
    ]

    print("Lanzando framework de trading (CLI)...")
    try:
        subprocess.call(framework_cmd, cwd=project_root, env=env)
    finally:
        # Si se cierra la CLI, intentamos cerrar también Streamlit
        if streamlit_proc and streamlit_proc.poll() is None:
            print("Cerrando servidor de Streamlit...")
            try:
                streamlit_proc.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    main()
