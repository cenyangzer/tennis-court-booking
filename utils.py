import os
from datetime import datetime
from functools import wraps
from flask import flash, redirect, url_for, session, request
from models import User, Court

# 用于创建目录
def create_directory(directory_path):
    """创建目录（如果不存在）"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

# 检查文件扩展名是否允许
def allowed_file(filename, allowed_extensions):
    """检查文件是否为允许的类型"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

# 计算两个时间之间的小时差
def calculate_hours(start_time, end_time):
    """计算两个时间之间的小时数"""
    duration = end_time - start_time
    return duration.total_seconds() / 3600

# 计算预约费用
def calculate_booking_cost(court_id, start_time, end_time):
    """计算预约费用"""
    court = Court.query.get_or_404(court_id)
    hours = calculate_hours(start_time, end_time)
    return round(court.price_per_hour * hours, 2)

# 装饰器：检查用户是否登录
def login_required(f):
    """确保用户已登录的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# 装饰器：检查用户是否为管理员
def admin_required(f):
    """确保用户是管理员的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login', next=request.url))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('没有权限访问此页面', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# 获取当前登录用户
def get_current_user():
    """获取当前登录的用户对象"""
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None

# 格式化日期时间显示
def format_datetime(dt, format_str='%Y-%m-%d %H:%M'):
    """格式化日期时间显示（系统内统一使用本地时间存储）"""
    if isinstance(dt, datetime):
        return dt.strftime(format_str)
    return dt

# 格式化价格显示
def format_price(price):
    """格式化价格显示"""
    return f"¥{price:.2f}"

# 获取状态的中文显示
def get_status_text(status):
    """获取状态的中文显示"""
    status_map = {
        'pending': '待确认',
        'confirmed': '已确认',
        'canceled': '已取消',
        'completed': '已完成',
        'unpaid': '未支付',
        'paid': '已支付',
        'refunded': '已退款'
    }
    return status_map.get(status, status)
