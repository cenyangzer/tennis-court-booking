from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, EmailField, IntegerField, FloatField, TextAreaField, BooleanField, DateTimeField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, NumberRange, ValidationError
from datetime import datetime, timedelta
from models import User, Court, Booking

class LoginForm(FlaskForm):
    """登录表单"""
    username = StringField('用户名', validators=[DataRequired(), Length(min=3, max=50)])
    password = PasswordField('密码', validators=[DataRequired()])
    remember_me = BooleanField('记住我')
    submit = SubmitField('登录')

class RegistrationForm(FlaskForm):
    """注册表单"""
    username = StringField('用户名', validators=[DataRequired(), Length(min=3, max=50)])
    email = EmailField('邮箱', validators=[DataRequired(), Email(), Length(max=100)])
    phone = StringField('手机号', validators=[Length(max=20)])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password', message='两次输入的密码必须一致')])
    submit = SubmitField('注册')
    
    def validate_username(self, username):
        """验证用户名是否已存在"""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('该用户名已被使用，请选择其他用户名。')
    
    def validate_email(self, email):
        """验证邮箱是否已存在"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('该邮箱已被注册，请使用其他邮箱。')

class BookingForm(FlaskForm):
    """预约表单"""
    court_id = SelectField('选择场地', coerce=int, validators=[DataRequired()])
    # 使用字符串字段接收datetime-local格式的数据
    start_time_str = StringField('开始时间', validators=[DataRequired()])
    end_time_str = StringField('结束时间', validators=[DataRequired()])
    submit = SubmitField('提交预约')
    
    # 用于存储转换后的datetime对象
    _start_time = None
    _end_time = None
    
    @property
    def start_time(self):
        """获取转换后的开始时间"""
        return self._start_time
    
    @property
    def end_time(self):
        """获取转换后的结束时间"""
        return self._end_time
    
    def __init__(self, *args, **kwargs):
        super(BookingForm, self).__init__(*args, **kwargs)
        # 加载可用场地
        self.court_id.choices = [(court.id, court.name) for court in Court.query.filter_by(status=True).all()]
    
    def validate(self, extra_validators=None):
        """验证预约信息"""
        # 先执行基础验证，确保所有字段都有值
        if not super().validate(extra_validators):
            return False
        
        try:
            # 1. 转换时间字符串为datetime对象
            # 支持多种格式，增强兼容性
            start_str = self.start_time_str.data
            end_str = self.end_time_str.data
            
            # 尝试多种格式解析
            time_formats = [
                '%Y-%m-%dT%H:%M',    # datetime-local格式
                '%Y-%m-%d %H:%M',    # 普通格式
                '%Y-%m-%d %H:%M:%S', # 带秒的格式
                '%Y-%m-%d %H:%M:%S.%f' # 带毫秒的格式
            ]
            
            # 解析开始时间
            self._start_time = None
            for fmt in time_formats:
                try:
                    self._start_time = datetime.strptime(start_str, fmt)
                    break
                except ValueError:
                    continue
            
            if self._start_time is None:
                self.start_time_str.errors.append('开始时间格式不正确，请使用有效的日期时间格式')
                return False
            
            # 解析结束时间
            self._end_time = None
            for fmt in time_formats:
                try:
                    self._end_time = datetime.strptime(end_str, fmt)
                    break
                except ValueError:
                    continue
            
            if self._end_time is None:
                self.end_time_str.errors.append('结束时间格式不正确，请使用有效的日期时间格式')
                return False
            
            # 2. 验证开始时间不能早于当前时间（允许有5分钟的误差，避免网络延迟问题）
            current_time = datetime.now()
            if self._start_time < current_time - timedelta(minutes=5):
                self.start_time_str.errors.append('开始时间不能早于当前时间')
                return False
            
            # 3. 验证结束时间不能早于开始时间
            if self._end_time <= self._start_time:
                self.end_time_str.errors.append('结束时间必须晚于开始时间')
                return False
            
            # 4. 检查预约时长是否合理（最长4小时）
            duration = (self._end_time - self._start_time).total_seconds() / 3600
            if duration > 4:
                self.end_time_str.errors.append('单次预约时长不能超过4小时')
                return False
            
            # 5. 检查时间是否在开放时间范围内（9:00-22:00）
            opening_hour = 9
            closing_hour = 22
            
            # 检查开始时间的小时部分
            if self._start_time.hour < opening_hour or self._start_time.hour >= closing_hour:
                self.start_time_str.errors.append('预约开始时间必须在开放时间内（9:00-22:00）')
                return False
            
            # 检查结束时间的小时部分
            if self._end_time.hour < opening_hour:
                self.end_time_str.errors.append('预约结束时间必须在开放时间内（9:00-22:00）')
                return False
            
            # 特殊情况处理：结束时间可以是22:00，但不能超过22:00
            if self._end_time.hour > closing_hour or (self._end_time.hour == closing_hour and self._end_time.minute > 0):
                self.end_time_str.errors.append('预约结束时间不能超过22:00')
                return False
            
            # 6. 检查时间冲突
            overlapping_bookings = Booking.query.filter(
                Booking.court_id == self.court_id.data,
                Booking.status.in_(['pending', 'confirmed']),
                Booking.start_time < self._end_time,
                Booking.end_time > self._start_time
            ).first()
            
            if overlapping_bookings:
                self.start_time_str.errors.append('该时间段已被预约，请选择其他时间')
                return False
                
        except Exception as e:
            # 提供更详细的错误信息
            self.start_time_str.errors.append(f'时间处理过程中出现错误: {str(e)}')
            return False
        
        return True

class ReviewForm(FlaskForm):
    """评价表单"""
    rating = SelectField('评分', coerce=int, choices=[(1, '1星'), (2, '2星'), (3, '3星'), (4, '4星'), (5, '5星')], validators=[DataRequired()])
    comment = TextAreaField('评价内容', validators=[Length(max=500)])
    submit = SubmitField('提交评价')

class UserProfileForm(FlaskForm):
    """用户资料编辑表单"""
    username = StringField('用户名', validators=[DataRequired(), Length(min=3, max=50)])
    email = EmailField('邮箱', validators=[DataRequired(), Email(), Length(max=100)])
    phone = StringField('手机号', validators=[Length(max=20)])
    submit = SubmitField('保存修改')
    
    def validate_username(self, username):
        """验证用户名是否已被其他用户使用"""
        # 使用当前登录用户ID进行验证，避免导入current_user
        from flask import session
        user = User.query.filter_by(username=username.data).first()
        if user and user.id != int(session.get('user_id')):
            raise ValidationError('该用户名已被使用，请选择其他用户名。')

class PasswordChangeForm(FlaskForm):
    """密码修改表单"""
    current_password = PasswordField('当前密码', validators=[DataRequired()])
    new_password = PasswordField('新密码', validators=[DataRequired(), Length(min=6)])
    confirm_new_password = PasswordField('确认新密码', validators=[DataRequired(), EqualTo('new_password', message='两次输入的新密码必须一致')])
    submit = SubmitField('修改密码')

class UserForm(FlaskForm):
    """管理员编辑用户表单"""
    username = StringField('用户名', validators=[DataRequired(), Length(min=3, max=50)])
    email = EmailField('邮箱', validators=[DataRequired(), Email(), Length(max=100)])
    phone = StringField('手机号', validators=[Length(max=20)])
    is_admin = BooleanField('管理员权限')
    submit = SubmitField('保存修改')
    
    def validate_username(self, username):
        """验证用户名是否已被其他用户使用"""
        # 这个验证会在视图函数中处理，避免重复检查
    
    def validate_email(self, email):
        """验证邮箱是否已被其他用户使用"""
        # 使用当前登录用户ID进行验证，避免导入current_user
        from flask import session
        user = User.query.filter_by(email=email.data).first()
        if user and user.id != int(session.get('user_id')):
            raise ValidationError('该邮箱已被使用，请使用其他邮箱。')

class AddUserForm(FlaskForm):
    """管理员添加用户表单"""
    username = StringField('用户名', validators=[DataRequired(), Length(min=3, max=50)])
    email = EmailField('邮箱', validators=[DataRequired(), Email(), Length(max=100)])
    phone = StringField('手机号', validators=[Length(max=20)])
    password = PasswordField('密码', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('确认密码', validators=[DataRequired(), EqualTo('password', message='两次输入的密码必须一致')])
    is_admin = BooleanField('管理员权限')
    submit = SubmitField('添加用户')
    
    def validate_username(self, username):
        """验证用户名是否已存在"""
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('该用户名已被使用，请选择其他用户名。')
    
    def validate_email(self, email):
        """验证邮箱是否已存在"""
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('该邮箱已被注册，请使用其他邮箱。')

class CourtForm(FlaskForm):
    """场地管理表单（管理员使用）"""
    name = StringField('场地名称', validators=[DataRequired(), Length(max=50)])
    type = StringField('场地类型', validators=[Length(max=20)])
    description = TextAreaField('场地描述')
    price_per_hour = FloatField('每小时价格', validators=[DataRequired(), NumberRange(min=0)])
    image = FileField('场地图片')
    status = BooleanField('是否可用', default=True)
    submit = SubmitField('保存')

class NoticeForm(FlaskForm):
    """公告管理表单（管理员使用）"""
    title = StringField('公告标题', validators=[DataRequired(), Length(max=100)])
    content = TextAreaField('公告内容', validators=[DataRequired()])
    is_active = BooleanField('是否发布', default=True)
    submit = SubmitField('发布公告')