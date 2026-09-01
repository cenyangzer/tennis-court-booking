from flask import Flask
from config import config
from models import db
from flask_wtf.csrf import CSRFProtect
from routes import init_routes
import os
from datetime import datetime

csrf = CSRFProtect()

def create_app(config_name=None):
    """创建Flask应用实例"""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # 添加上下文处理器，提供当前时间和round函数
    @app.context_processor
    def inject_now():
        return {'now': datetime.now(), 'round': round}

    # 初始化数据库
    db.init_app(app)

    # 启用全局CSRF保护（所有POST请求需携带csrf_token）
    csrf.init_app(app)
    
    # 初始化路由
    init_routes(app)
    
    # 创建必要的目录
    from utils import create_directory
    create_directory(app.config['UPLOAD_FOLDER'])
    
    return app

app = create_app()

# 创建数据库表
@app.cli.command('init-db')
def init_db():
    """初始化数据库"""
    with app.app_context():
        db.create_all()
        
        # 创建默认管理员账户
        from models import User
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@example.com',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print('管理员账户已创建: 用户名 admin, 密码 admin123')
        
        # 创建默认场地
        from models import Court
        if Court.query.count() == 0:
            courts = [
                {'name': '场地1', 'type': '硬地', 'description': '标准硬地球场，适合各级别玩家', 'price_per_hour': 60.0},
                {'name': '场地2', 'type': '硬地', 'description': '标准硬地球场，配备专业照明', 'price_per_hour': 60.0},
                {'name': '场地3', 'type': '红土', 'description': '专业红土场地，国际赛事标准', 'price_per_hour': 80.0},
                {'name': '场地4', 'type': '草地', 'description': '高品质草地，适合高级玩家', 'price_per_hour': 100.0}
            ]
            
            for court_data in courts:
                court = Court(**court_data)
                db.session.add(court)
            
            db.session.commit()
            print('默认场地已创建')
        
        # 创建示例公告
        from models import Notice
        if Notice.query.count() == 0:
            notice = Notice(
                title='欢迎使用网球馆预约系统',
                content='本系统提供便捷的场地预约服务，用户可以在线预约场地、管理个人预约记录。如有任何问题，请联系客服。',
                is_active=True
            )
            db.session.add(notice)
            db.session.commit()
            print('示例公告已创建')
        
        print('数据库初始化完成')

if __name__ == '__main__':
    # 在开发环境中运行应用
    app.run(debug=True, host='0.0.0.0', port=5000)