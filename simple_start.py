"""网球馆预约系统一键启动脚本

功能：检查依赖 -> 初始化数据库 -> 启动服务器
"""
import os
import sys
import subprocess


def main():
    print("Starting Tennis Court Booking System...")

    # 设置环境变量
    os.environ["FLASK_APP"] = "app.py"

    # 创建必要目录
    os.makedirs(os.path.join("static", "uploads", "courts"), exist_ok=True)
    os.makedirs("instance", exist_ok=True)
    print("Directories created")

    # 仅在依赖缺失时安装
    try:
        import flask  # noqa: F401
        import flask_sqlalchemy  # noqa: F401
        print("Dependencies OK")
    except ImportError:
        print("Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    # 初始化数据库（通过 flask CLI，保证与应用逻辑一致）
    print("Initializing database...")
    result = subprocess.run(
        [sys.executable, "-m", "flask", "init-db"],
        env={**os.environ, "FLASK_APP": "app.py"},
    )
    if result.returncode == 0:
        print("Database initialized successfully")
    else:
        print("Database initialization failed, please check the output above.")

    # 启动服务器
    print("\n===================================")
    print("System is starting")
    print("===================================")
    print("Access at: http://localhost:5000")
    print("Admin account: admin/admin123")
    print("Press Ctrl+C to stop the server\n")

    from app import app
    app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    main()
