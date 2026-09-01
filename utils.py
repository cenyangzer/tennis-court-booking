import os
from datetime import datetime, timedelta
from functools import wraps
from flask import flash, redirect, url_for, session, request
from werkzeug.utils import secure_filename
from models import User, Booking, Court

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

# 保存上传的文件
def save_uploaded_file(file, upload_folder, allowed_extensions):
    """保存上传的文件并返回文件名"""
    if file and allowed_file(file.filename, allowed_extensions):
        create_directory(upload_folder)
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        filename = f"{timestamp}_{filename}"
        file.save(os.path.join(upload_folder, filename))
        return filename
    return None

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

# 检查时间是否冲突
def is_time_slot_available(court_id, start_time, end_time, exclude_booking_id=None):
    """检查时间段是否可用"""
    query = Booking.query.filter(
        Booking.court_id == court_id,
        Booking.status.in_(['pending', 'confirmed']),
        Booking.start_time < end_time,
        Booking.end_time > start_time
    )
    
    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)
    
    return query.first() is None

# 获取今天开始和结束时间
def get_today_range():
    """获取今天的开始和结束时间"""
    today = datetime.now().date()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())
    return start_of_day, end_of_day

# 获取本周开始和结束时间
def get_week_range():
    """获取本周的开始和结束时间"""
    today = datetime.now()
    # 获取本周一
    start_of_week = today - timedelta(days=today.weekday())
    start_of_week = datetime.combine(start_of_week.date(), datetime.min.time())
    # 获取本周日
    end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return start_of_week, end_of_week

# 获取本月开始和结束时间
def get_month_range():
    """获取本月的开始和结束时间"""
    today = datetime.now()
    start_of_month = datetime(today.year, today.month, 1)
    # 获取下个月的第一天，然后减去一天
    if today.month == 12:
        end_of_month = datetime(today.year + 1, 1, 1) - timedelta(seconds=1)
    else:
        end_of_month = datetime(today.year, today.month + 1, 1) - timedelta(seconds=1)
    return start_of_month, end_of_month

# 生成日期选择器的时间段选项
def generate_time_slots():
    """生成时间段选项（9:00-22:00，每小时一个时间段）"""
    slots = []
    for hour in range(9, 23):
        time_str = f"{hour:02d}:00"
        slots.append((time_str, time_str))
    return slots

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

# 截断小数，不进行四舍五入
def truncate_decimal(number, decimals=2):
    """截断小数，不进行四舍五入"""
    factor = 10 ** decimals
    return int(number * factor) / factor

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