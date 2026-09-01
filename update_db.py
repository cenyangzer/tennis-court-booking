from app import app
from models import db
from sqlalchemy import text

# 在应用上下文中运行
with app.app_context():
    # 检查数据库连接
    print("开始更新数据库结构...")
    
    try:
        # 1. 为booking表添加order_no列（保留原有功能）
        result = db.session.execute(text("PRAGMA table_info(booking)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'order_no' not in columns:
            db.session.execute(text('ALTER TABLE booking ADD COLUMN order_no VARCHAR(50)'))
            db.session.commit()
            print("数据库字段order_no添加成功！")
        else:
            print("字段order_no已存在，无需添加。")
        
        # 2. 为user表添加is_active列
        result = db.session.execute(text("PRAGMA table_info(user)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'is_active' not in columns:
            db.session.execute(text('ALTER TABLE user ADD COLUMN is_active BOOLEAN DEFAULT 1'))
            db.session.commit()
            print("数据库字段is_active添加成功！")
        else:
            print("字段is_active已存在，无需添加。")
        
        # 3. 为booking表添加refund_amount列（用于退款功能）
        result = db.session.execute(text("PRAGMA table_info(booking)"))
        columns = [row[1] for row in result.fetchall()]
        
        if 'refund_amount' not in columns:
            db.session.execute(text('ALTER TABLE booking ADD COLUMN refund_amount FLOAT DEFAULT 0.0'))
            db.session.commit()
            print("数据库字段refund_amount添加成功！")
        else:
            print("字段refund_amount已存在，无需添加。")
        
        # 4. 创建场地时段可用性表
        result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='court_availability'"))
        if not result.fetchone():
            db.session.execute(text('''
                CREATE TABLE court_availability (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    court_id INTEGER NOT NULL,
                    date DATE NOT NULL,
                    start_time TIME NOT NULL,
                    end_time TIME NOT NULL,
                    is_available BOOLEAN DEFAULT 1,
                    booking_id INTEGER,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (court_id) REFERENCES court (id),
                    FOREIGN KEY (booking_id) REFERENCES booking (id)
                )
            '''))
            db.session.commit()
            print("场地时段可用性表创建成功！")
        else:
            print("场地时段可用性表已存在，无需创建。")
            
    except Exception as e:
        db.session.rollback()
        print(f"数据库更新出错: {e}")
    finally:
        db.session.close()
    
    print("数据库更新操作完成。")