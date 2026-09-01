from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

# 初始化数据库
db = SQLAlchemy()

class User(db.Model):
    """用户模型"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    phone = db.Column(db.String(20))
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)  # 用户是否激活
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关联预约记录
    bookings = db.relationship('Booking', backref='user', lazy=True)
    
    def set_password(self, password):
        """设置密码（加密）"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Court(db.Model):
    """场地模型"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(20))  # 如：硬地、红土、草地
    description = db.Column(db.Text)
    price_per_hour = db.Column(db.Float, nullable=False)
    status = db.Column(db.Boolean, default=True)  # True表示可用
    image_url = db.Column(db.String(200))
    
    # 关联预约记录
    bookings = db.relationship('Booking', backref='court', lazy=True)
    # 关联场地时段可用性
    availabilities = db.relationship('CourtAvailability', backref='court', lazy=True)
    
    def __repr__(self):
        return f'<Court {self.name}>'

class Booking(db.Model):
    """预约模型"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    court_id = db.Column(db.Integer, db.ForeignKey('court.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, canceled, completed
    created_at = db.Column(db.DateTime, default=datetime.now)
    payment_status = db.Column(db.String(20), default='unpaid')  # unpaid, paid, refunded
    order_no = db.Column(db.String(50))  # 支付订单号
    refund_amount = db.Column(db.Float, default=0.0)  # 实际退款金额
    
    def __repr__(self):
        return f'<Booking {self.id} - User {self.user_id} - Court {self.court_id}>'

class Review(db.Model):
    """评价模型"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    court_id = db.Column(db.Integer, db.ForeignKey('court.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5星
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    # 关联
    user = db.relationship('User', backref='reviews')
    court = db.relationship('Court', backref='reviews')
    booking = db.relationship('Booking', backref='review')
    
    def __repr__(self):
        return f'<Review {self.id} - Rating {self.rating}>'
        
class CourtAvailability(db.Model):
    """场地时段可用性模型"""
    id = db.Column(db.Integer, primary_key=True)
    court_id = db.Column(db.Integer, db.ForeignKey('court.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_available = db.Column(db.Boolean, default=True)  # True表示可用
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    def __repr__(self):
        return f'<CourtAvailability Court {self.court_id} - {self.date} {self.start_time}-{self.end_time}>'

class Notice(db.Model):
    """公告模型"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    is_active = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<Notice {self.title}>'