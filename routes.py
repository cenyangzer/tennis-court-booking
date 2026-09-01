from flask import Flask, render_template, redirect, url_for, flash, request, session, jsonify, current_app
import os
from werkzeug.utils import secure_filename
from datetime import datetime
from models import db, User, Court, Booking, Review, Notice, CourtAvailability
from forms import LoginForm, RegistrationForm, BookingForm, ReviewForm, UserProfileForm, CourtForm, NoticeForm, UserForm, AddUserForm, PasswordChangeForm
from utils import login_required, admin_required, get_current_user, calculate_booking_cost, format_datetime, format_price, get_status_text, allowed_file
import uuid  # 用于生成支付订单号

def init_routes(app):
    """初始化所有路由"""
    
    @app.route('/')
    def index():
        """首页"""
        # 从数据库中查询所有状态为“可用”的场地（Court）
        # status=True 表示该场地当前处于开放/可用状态
        courts = Court.query.filter_by(status=True).all()
        notices = Notice.query.filter_by(is_active=True).order_by(Notice.created_at.desc()).limit(3).all()
        return render_template('index.html', courts=courts, notices=notices)
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """登录页面"""
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user and user.check_password(form.password.data):
                # 检查用户是否激活
                if not user.is_active:
                    flash('账户已被禁用，请联系管理员', 'danger')
                    return redirect(url_for('login'))
                session['user_id'] = user.id
                session['username'] = user.username
                session['is_admin'] = user.is_admin
                flash('登录成功', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            flash('用户名或密码错误', 'danger')
        return render_template('login.html', form=form)
    
    @app.route('/logout')
    def logout():
        """退出登录"""
        session.clear()
        flash('已退出登录', 'info')
        return redirect(url_for('index'))
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """注册页面"""
        form = RegistrationForm()
        if form.validate_on_submit():
            user = User(
                username=form.username.data,
                email=form.email.data,
                phone=form.phone.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('注册成功，请登录', 'success')
            return redirect(url_for('login'))
        return render_template('register.html', form=form)
    
    @app.route('/courts')
    def courts():
        """场地列表页面"""
        courts = Court.query.all()
        return render_template('courts.html', courts=courts)
    
    @app.route('/court/<int:court_id>')
    def court_detail(court_id):
        """场地详情页面"""
        court = Court.query.get_or_404(court_id)
        reviews = Review.query.filter_by(court_id=court_id).order_by(Review.created_at.desc()).all()
        return render_template('court_detail.html', court=court, reviews=reviews)
    
    @app.route('/booking', methods=['GET', 'POST'])
    @login_required
    def booking():
        """预约页面"""
        # 获取URL中的场地ID参数
        court_id = request.args.get('court_id', type=int)
        # 创建表单，如果有场地ID参数则传入
        form = BookingForm()
        # 如果有场地ID参数，设置为表单的默认值
        if court_id:
            form.court_id.data = court_id
        if form.validate_on_submit():
            # 计算费用（使用转换后的时间属性）
            total_amount = calculate_booking_cost(form.court_id.data, form.start_time, form.end_time)
            
            # 创建预约记录
            booking = Booking(
                user_id=session['user_id'],
                court_id=form.court_id.data,
                start_time=form.start_time,
                end_time=form.end_time,
                total_amount=total_amount
            )
            
            db.session.add(booking)
            db.session.commit()
            
            flash('预约成功！请等待确认', 'success')
            return redirect(url_for('user_bookings'))
        return render_template('booking.html', form=form)
    
    @app.route('/user/bookings')
    @login_required
    def user_bookings():
        """用户预约列表"""
        user = get_current_user()
        bookings = Booking.query.filter_by(user_id=user.id).order_by(Booking.created_at.desc()).all()
        return render_template('user_bookings.html', bookings=bookings)
    
    @app.route('/payment/<int:booking_id>', methods=['GET', 'POST'])
    @login_required
    def payment_page(booking_id):
        """支付页面"""
        user = get_current_user()
        booking = Booking.query.get_or_404(booking_id)
        
        # 检查是否是用户自己的预约且状态允许支付
        if booking.user_id != user.id:
            flash('无权为此预约进行支付', 'danger')
            return redirect(url_for('user_bookings'))
        
        # 检查预约状态是否允许支付（已确认或已完成但未支付）
        if booking.status not in ['confirmed', 'completed'] or booking.payment_status != 'unpaid':
            flash('该预约状态不允许进行支付', 'warning')
            return redirect(url_for('user_bookings'))
        
        # 支付方式列表（使用模拟支付方式）
        payment_methods = ['支付宝', '微信支付', '银行卡支付']
        
        return render_template('payment.html', booking=booking, payment_methods=payment_methods)
        
    @app.route('/booking/cancel/<int:booking_id>')
    @login_required
    def user_cancel_booking(booking_id):
        """用户取消预约（支持2小时内取消收取30%费用）"""
        user = get_current_user()
        booking = Booking.query.get_or_404(booking_id)
        
        # 检查是否是用户自己的预约
        if booking.user_id != user.id:
            flash('无权取消此预约', 'danger')
            return redirect(url_for('user_bookings'))
        
        # 检查预约状态是否允许取消（只能取消待确认和已确认的预约）
        if booking.status not in ['pending', 'confirmed']:
            flash('该预约状态不允许取消', 'warning')
            return redirect(url_for('user_bookings'))
        
        current_time = datetime.now()
        # 计算时间差（小时）
        time_diff_hours = (booking.start_time - current_time).total_seconds() / 3600
        # 打印调试信息
        print(f"当前时间: {current_time}")
        print(f"预约开始时间: {booking.start_time}")
        print(f"时间差: {time_diff_hours}小时")
        
        # 更新状态为已取消
        booking.status = 'canceled'
        
        # 检查是否已支付，如果已支付则处理退款逻辑
        if booking.payment_status == 'paid':
            # 判断是否在预约开始前2小时内
            if time_diff_hours < 2:
                # 2小时内取消，收取30%费用，退还70%
                refund_amount = booking.total_amount * 0.7
                booking.refund_amount = refund_amount
                booking.payment_status = 'refunded'
                flash(f'预约已取消，因在2小时内取消，收取30%费用，退还{format_price(refund_amount)}', 'warning')
            else:
                # 2小时外取消，全额退款
                booking.refund_amount = booking.total_amount
                booking.payment_status = 'refunded'
                flash('预约已取消，全额退款', 'success')
        else:
            flash('预约已取消', 'success')
        
        db.session.commit()
        return redirect(url_for('user_bookings'))
    
    @app.route('/process_payment/<int:booking_id>', methods=['POST'])
    @login_required
    def process_payment(booking_id):
        """处理支付请求"""
        user = get_current_user()
        booking = Booking.query.get_or_404(booking_id)
        
        # 检查权限和状态
        if booking.user_id != user.id or booking.status not in ['confirmed', 'completed'] or booking.payment_status != 'unpaid':
            flash('支付请求无效', 'danger')
            return redirect(url_for('user_bookings'))
        
        # 获取支付方式
        payment_method = request.form.get('payment_method')
        
        # 生成支付订单号
        order_no = f"ORDER-{uuid.uuid4().hex[:10].upper()}"
        
        # 这里模拟支付处理，实际项目中应调用真实的支付API
        # 模拟支付成功
        try:
            # 更新支付状态
            booking.payment_status = 'paid'
            booking.order_no = order_no  # 存储订单号（需要在model中添加此字段）
            db.session.commit()
            
            flash('支付成功！感谢您的预约', 'success')
            return redirect(url_for('user_bookings'))
        except Exception as e:
            db.session.rollback()
            flash('支付处理失败，请稍后重试', 'danger')
            return redirect(url_for('payment_page', booking_id=booking_id))
    
    @app.route('/user/profile', methods=['GET', 'POST'])
    @login_required
    def user_profile():
        """用户个人资料页面"""
        user = get_current_user()
        form = UserProfileForm(obj=user)
        password_form = PasswordChangeForm()
        
        if form.validate_on_submit():
            user.username = form.username.data
            user.email = form.email.data
            user.phone = form.phone.data
            db.session.commit()
            session['username'] = user.username
            flash('个人资料已更新', 'success')
            return redirect(url_for('user_profile'))
        
        return render_template('user_profile.html', form=form, password_form=password_form)
    
    @app.route('/user/change-password', methods=['POST'])
    @login_required
    def user_change_password():
        """修改密码"""
        user = get_current_user()
        form = PasswordChangeForm()
        
        if form.validate_on_submit():
            # 验证当前密码是否正确
            if not user.check_password(form.current_password.data):
                form.current_password.errors.append('当前密码错误')
                return render_template('user_profile.html', form=UserProfileForm(obj=user), password_form=form)
            
            # 更新密码
            user.set_password(form.new_password.data)
            db.session.commit()
            flash('密码已成功修改', 'success')
            return redirect(url_for('user_profile'))
        
        # 表单验证失败，返回个人资料页面
        return render_template('user_profile.html', form=UserProfileForm(obj=user), password_form=form)
    
    @app.route('/review/<int:booking_id>', methods=['GET', 'POST'])
    @login_required
    def add_review(booking_id):
        """添加评价"""
        booking = Booking.query.get_or_404(booking_id)
        user = get_current_user()
        
        # 检查是否是用户自己的预约，且状态为已完成
        if booking.user_id != user.id or booking.status != 'completed':
            flash('无权对此预约进行评价', 'danger')
            return redirect(url_for('user_bookings'))
        
        # 检查是否已经评价过
        existing_review = Review.query.filter_by(booking_id=booking_id).first()
        if existing_review:
            flash('您已经评价过此预约', 'warning')
            return redirect(url_for('user_bookings'))
        
        form = ReviewForm()
        if form.validate_on_submit():
            review = Review(
                user_id=user.id,
                court_id=booking.court_id,
                booking_id=booking_id,
                rating=form.rating.data,
                comment=form.comment.data
            )
            db.session.add(review)
            db.session.commit()
            flash('评价提交成功', 'success')
            return redirect(url_for('user_bookings'))
        
        return render_template('add_review.html', form=form, booking=booking)
    
    # 管理员相关路由
    @app.route('/admin/dashboard')
    @admin_required
    def admin_dashboard():
        """管理员仪表盘"""
        # 统计信息
        total_users = User.query.count()
        total_courts = Court.query.count()
        total_bookings = Booking.query.count()
        pending_bookings = Booking.query.filter_by(status='pending').count()
        
        # 今日预约
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())
        today_bookings = Booking.query.filter(Booking.start_time >= today_start, Booking.start_time <= today_end).count()
        
        return render_template('admin/dashboard.html', 
                            total_users=total_users,
                            total_courts=total_courts,
                            total_bookings=total_bookings,
                            pending_bookings=pending_bookings,
                            today_bookings=today_bookings)
    
    @app.route('/admin/users')
    @admin_required
    def admin_users():
        """管理员查看用户列表"""
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        
        # 创建查询
        query = User.query
        
        # 应用筛选条件
        username = request.args.get('username')
        if username:
            query = query.filter(User.username.like(f'%{username}%'))
            
        email = request.args.get('email')
        if email:
            query = query.filter(User.email.like(f'%{email}%'))
            
        role = request.args.get('role')
        if role == 'admin':
            query = query.filter(User.is_admin == True)
        elif role == 'user':
            query = query.filter(User.is_admin == False)
        
        # 分页查询
        users = query.paginate(page=page, per_page=10, error_out=False)
        
        return render_template('admin/users.html', users=users)
    
    @app.route('/admin/user/add', methods=['GET', 'POST'])
    @admin_required
    def admin_add_user():
        """管理员添加用户"""
        form = AddUserForm()
        
        if form.validate_on_submit():
            # 创建新用户
            user = User(
                username=form.username.data,
                email=form.email.data,
                phone=form.phone.data,
                is_admin=form.is_admin.data
            )
            # 设置密码
            user.set_password(form.password.data)
            
            # 保存到数据库
            db.session.add(user)
            db.session.commit()
            
            flash('用户添加成功', 'success')
            return redirect(url_for('admin_users'))
        
        return render_template('admin/add_user.html', form=form)
    
    @app.route('/admin/courts', methods=['GET', 'POST'])
    @admin_required
    def admin_courts():
        """管理员管理场地"""
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        
        # 创建查询
        query = Court.query
        
        # 应用筛选条件
        name = request.args.get('name')
        if name:
            query = query.filter(Court.name.like(f'%{name}%'))
            
        court_type = request.args.get('type')
        if court_type:
            # 确保类型匹配正确（前端提交的可能是中文，需要对应到数据库中的值）
            type_mapping = {
                'hard': '硬地',
                'clay': '红土', 
                'grass': '草地',
                'indoor': '室内'
            }
            # 查找映射值，如果没有找到则使用原值
            mapped_type = type_mapping.get(court_type, court_type)
            query = query.filter(Court.type == mapped_type)
            
        status = request.args.get('status')
        if status:
            # 将字符串状态转换为布尔值
            if status == 'available':
                query = query.filter(Court.status == True)
            elif status == 'unavailable':
                query = query.filter(Court.status == False)
        
        # 分页查询
        courts = query.paginate(page=page, per_page=10, error_out=False)
        
        form = CourtForm()
        
        if form.validate_on_submit():
            court = Court(
                name=form.name.data,
                type=form.type.data,
                description=form.description.data,
                price_per_hour=form.price_per_hour.data,
                status=form.status.data
            )
            db.session.add(court)
            db.session.commit()
            flash('场地添加成功', 'success')
            return redirect(url_for('admin_courts'))
        
        return render_template('admin/courts.html', courts=courts, form=form)
    
    @app.route('/admin/court/edit/<int:court_id>', methods=['GET', 'POST'])
    @admin_required
    def admin_edit_court(court_id):
        """编辑场地信息"""
        court = Court.query.get_or_404(court_id)
        form = CourtForm(obj=court)
        
        if form.validate_on_submit():
            # 处理文件上传
            if 'image' in request.files and request.files['image'].filename:
                image = request.files['image']
                # 校验文件类型
                if not allowed_file(image.filename, app.config['ALLOWED_EXTENSIONS']):
                    flash('不支持的图片格式，仅支持 png/jpg/jpeg/gif', 'danger')
                    return render_template('admin/edit_court.html', form=form, court=court)
                # 生成带时间戳的唯一文件名，防止覆盖
                filename = secure_filename(image.filename)
                filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                # 确保上传目录存在
                upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'courts')
                os.makedirs(upload_dir, exist_ok=True)
                # 保存文件
                image_path = os.path.join(upload_dir, filename)
                image.save(image_path)
                # 更新场地图片路径（模板按 uploads/ + image_url 拼接）
                court.image_url = f'courts/{filename}'
            
            form.populate_obj(court)
            db.session.commit()
            flash('场地信息已更新', 'success')
            return redirect(url_for('admin_courts'))
        
        return render_template('admin/edit_court.html', form=form, court=court)
    
    @app.route('/admin/court/set_status/<int:court_id>/<status>')
    @admin_required
    def admin_set_court_status(court_id, status):
        """设置场地状态"""
        court = Court.query.get_or_404(court_id)
        # 将字符串状态转换为布尔值
        if status.lower() == 'available' or status.lower() == 'true':
            court.status = True
        elif status.lower() == 'unavailable' or status.lower() == 'false':
            court.status = False
        else:
            # 默认为不可用
            court.status = False
        db.session.commit()
        flash('场地状态已更新', 'success')
        return redirect(url_for('admin_courts'))
    
    @app.route('/admin/court/delete/<int:court_id>')
    @admin_required
    def admin_delete_court(court_id):
        """删除场地"""
        court = Court.query.get_or_404(court_id)
        
        # 删除与该场地相关的评价记录
        Review.query.filter_by(court_id=court_id).delete()
        
        # 删除与该场地相关的预约记录
        Booking.query.filter_by(court_id=court_id).delete()
        
        # 删除与该场地相关的时段可用性记录
        CourtAvailability.query.filter_by(court_id=court_id).delete()
        
        db.session.delete(court)
        db.session.commit()
        flash('场地已删除', 'success')
        return redirect(url_for('admin_courts'))
    
    @app.route('/admin/user/edit/<int:user_id>', methods=['GET', 'POST'])
    @admin_required
    def admin_edit_user(user_id):
        """编辑用户信息"""
        user = User.query.get_or_404(user_id)
        form = UserForm(obj=user)
        
        if form.validate_on_submit():
            # 单独更新字段，避免populate_obj可能尝试设置不存在的字段
            user.username = form.username.data
            user.email = form.email.data
            user.phone = form.phone.data
            user.is_admin = form.is_admin.data
            db.session.commit()
            flash('用户信息已更新', 'success')
            return redirect(url_for('admin_users'))
        
        return render_template('admin/edit_user.html', form=form, user=user)
    
    @app.route('/admin/user/deactivate/<int:user_id>')
    @admin_required
    def admin_deactivate_user(user_id):
        """禁用用户"""
        user = User.query.get_or_404(user_id)
        user.is_active = False
        db.session.commit()
        flash('用户已禁用', 'success')
        return redirect(url_for('admin_users'))
    
    @app.route('/admin/user/activate/<int:user_id>')
    @admin_required
    def admin_activate_user(user_id):
        """启用用户"""
        user = User.query.get_or_404(user_id)
        user.is_active = True
        db.session.commit()
        flash('用户已启用', 'success')
        return redirect(url_for('admin_users'))
    
    @app.route('/admin/user/delete/<int:user_id>')
    @admin_required
    def admin_delete_user(user_id):
        """删除用户"""
        user = User.query.get_or_404(user_id)
        # 确保不删除管理员用户
        if user.is_admin:
            flash('不能删除管理员用户', 'danger')
            return redirect(url_for('admin_users'))
        
        # 删除相关的评价记录
        Review.query.filter_by(user_id=user_id).delete()
        
        # 删除相关的预约记录
        Booking.query.filter_by(user_id=user_id).delete()
        
        # 删除用户
        db.session.delete(user)
        db.session.commit()
        flash('用户已删除', 'success')
        return redirect(url_for('admin_users'))
    
    @app.route('/admin/bookings')
    @admin_required
    def admin_bookings():
        """管理员查看所有预约"""
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        
        # 创建查询
        query = Booking.query.order_by(Booking.created_at.desc())
        
        # 应用筛选条件
        booking_id = request.args.get('booking_id')
        if booking_id:
            query = query.filter(Booking.id == booking_id)
            
        username = request.args.get('username')
        if username:
            query = query.join(User).filter(User.username.like(f'%{username}%'))
            
        court_id = request.args.get('court_id', type=int)
        if court_id:
            query = query.filter(Booking.court_id == court_id)
            
        status = request.args.get('status')
        if status:
            query = query.filter(Booking.status == status)
        
        # 分页查询
        bookings = query.paginate(page=page, per_page=10, error_out=False)
        
        # 获取所有场地用于筛选
        courts = Court.query.all()
        
        return render_template('admin/bookings.html', bookings=bookings, courts=courts)
    
    @app.route('/admin/booking/confirm/<int:booking_id>')
    @admin_required
    def admin_confirm_booking(booking_id):
        """确认预约"""
        booking = Booking.query.get_or_404(booking_id)
        booking.status = 'confirmed'
        
        # 生成订单号
        order_no = datetime.now().strftime('%Y%m%d%H%M%S') + str(booking_id).zfill(4)
        booking.order_no = order_no
        
        db.session.commit()
        flash('预约已确认', 'success')
        return redirect(url_for('admin_bookings'))
    
    @app.route('/admin/booking/cancel/<int:booking_id>')
    @admin_required
    def admin_cancel_booking(booking_id):
        """取消预约（支持2小时内取消收取30%费用）"""
        booking = Booking.query.get_or_404(booking_id)
        current_time = datetime.now()
        # 计算时间差（小时）
        time_diff_hours = (booking.start_time - current_time).total_seconds() / 3600
        # 打印调试信息
        print(f"当前时间: {current_time}")
        print(f"预约开始时间: {booking.start_time}")
        print(f"时间差: {time_diff_hours}小时")
        
        # 更新状态为已取消
        booking.status = 'canceled'
        
        # 检查是否已支付，如果已支付则处理退款逻辑
        if booking.payment_status == 'paid':
            # 判断是否在预约开始前2小时内
            if time_diff_hours < 2:
                # 2小时内取消，收取30%费用，退还70%
                refund_amount = booking.total_amount * 0.7
                booking.refund_amount = refund_amount
                booking.payment_status = 'refunded'
                flash(f'预约已取消，因在2小时内取消，收取30%费用，退还{format_price(refund_amount)}', 'warning')
            else:
                # 2小时外取消，全额退款
                booking.refund_amount = booking.total_amount
                booking.payment_status = 'refunded'
                flash('预约已取消，全额退款', 'success')
        else:
            flash('预约已取消', 'success')
        
        db.session.commit()
        return redirect(url_for('admin_bookings'))
    
    @app.route('/admin/booking/complete/<int:booking_id>')
    @admin_required
    def admin_complete_booking(booking_id):
        """完成预约"""
        booking = Booking.query.get_or_404(booking_id)
        booking.status = 'completed'
        db.session.commit()
        flash('预约已标记为完成', 'success')
        return redirect(url_for('admin_bookings'))
        
    @app.route('/admin/payment/<int:booking_id>', methods=['GET', 'POST'])
    @admin_required
    def admin_payment_page(booking_id):
        """管理员支付页面"""
        booking = Booking.query.get_or_404(booking_id)
        
        # 检查预约状态是否允许支付（已确认或已完成但未支付）
        if booking.status not in ['confirmed', 'completed'] or booking.payment_status != 'unpaid':
            flash('该预约状态不允许进行支付', 'warning')
            return redirect(url_for('admin_bookings'))
        
        # 支付方式列表（使用模拟支付方式）
        payment_methods = ['支付宝', '微信支付', '银行卡支付']
        
        return render_template('payment.html', booking=booking, payment_methods=payment_methods, is_admin=True)
    
    @app.route('/admin/process_payment/<int:booking_id>', methods=['POST'])
    @admin_required
    def admin_process_payment(booking_id):
        """管理员处理支付请求"""
        booking = Booking.query.get_or_404(booking_id)
        
        # 检查状态
        if booking.status not in ['confirmed', 'completed'] or booking.payment_status != 'unpaid':
            flash('支付请求无效', 'danger')
            return redirect(url_for('admin_bookings'))
        
        # 获取支付方式
        payment_method = request.form.get('payment_method')
        
        # 生成支付订单号
        order_no = f"ORDER-{uuid.uuid4().hex[:10].upper()}"
        
        # 这里模拟支付处理，实际项目中应调用真实的支付API
        # 模拟支付成功
        try:
            # 更新支付状态
            booking.payment_status = 'paid'
            booking.order_no = order_no
            db.session.commit()
            
            flash('支付成功！', 'success')
            return redirect(url_for('admin_bookings'))
        except Exception as e:
            db.session.rollback()
            flash('支付处理失败，请稍后重试', 'danger')
            return redirect(url_for('admin_payment_page', booking_id=booking_id))
    
    @app.route('/admin/reviews')
    @admin_required
    def admin_reviews():
        """管理员查看所有评价"""
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        
        # 创建查询
        query = Review.query.order_by(Review.created_at.desc())
        
        # 应用筛选条件
        username = request.args.get('username')
        if username:
            query = query.join(User).filter(User.username.like(f'%{username}%'))
            
        court_id = request.args.get('court_id', type=int)
        if court_id:
            query = query.filter(Review.court_id == court_id)
            
        rating = request.args.get('rating', type=int)
        if rating:
            query = query.filter(Review.rating == rating)
        
        # 分页查询
        reviews = query.paginate(page=page, per_page=10, error_out=False)
        
        # 获取所有场地用于筛选
        courts = Court.query.all()
        
        return render_template('admin/reviews.html', reviews=reviews, courts=courts)
    
    @app.route('/admin/review/edit/<int:review_id>', methods=['GET', 'POST'])
    @admin_required
    def admin_edit_review(review_id):
        """管理员编辑评价"""
        review = Review.query.get_or_404(review_id)
        form = ReviewForm(obj=review)
        
        if form.validate_on_submit():
            review.rating = form.rating.data
            review.comment = form.comment.data
            db.session.commit()
            flash('评价内容已更新', 'success')
            return redirect(url_for('admin_reviews'))
        
        return render_template('admin/edit_review.html', form=form, review=review)
    
    @app.route('/admin/review/delete/<int:review_id>')
    @admin_required
    def admin_delete_review(review_id):
        """管理员删除评价"""
        review = Review.query.get_or_404(review_id)
        db.session.delete(review)
        db.session.commit()
        flash('评价已删除', 'success')
        return redirect(url_for('admin_reviews'))
    
    @app.route('/admin/notices', methods=['GET', 'POST'])
    @admin_required
    def admin_notices():
        """管理员管理公告"""
        notices = Notice.query.order_by(Notice.created_at.desc()).all()
        form = NoticeForm()
        
        if form.validate_on_submit():
            notice = Notice(
                title=form.title.data,
                content=form.content.data,
                is_active=form.is_active.data
            )
            db.session.add(notice)
            db.session.commit()
            flash('公告发布成功', 'success')
            return redirect(url_for('admin_notices'))
        
        return render_template('admin/notices.html', notices=notices, form=form)
    
    @app.route('/notices', methods=['GET', 'POST'])
    def notices():
        """查看所有公告"""
        all_notices = Notice.query.filter_by(is_active=True).order_by(Notice.created_at.desc()).all()
        form = NoticeForm()  # 初始化表单对象以避免模板错误
        
        # 如果有表单提交，检查用户是否为管理员
        if request.method == 'POST' and form.validate_on_submit():
            # 检查用户是否登录且是管理员
            user = get_current_user()
            if not user or not user.is_admin:
                flash('您没有权限添加公告', 'danger')
                return redirect(url_for('notices'))
            # 由于我们已经在模板中隐藏了表单，这里主要是防止直接通过API提交
            flash('请通过管理员界面添加公告', 'info')
            return redirect(url_for('notices'))
            
        return render_template('admin/notices.html', notices=all_notices, form=form)
    
    @app.route('/notice/<int:notice_id>')
    def notice_detail(notice_id):
        """公告详情"""
        notice = Notice.query.get_or_404(notice_id)
        return render_template('notice_detail.html', notice=notice)
        
    # 全局上下文处理器
    @app.context_processor
    def inject_user():
        """将用户信息注入到所有模板中"""
        user = get_current_user()
        return dict(current_user=user)
    
    @app.context_processor
    def utility_processor():
        """注入工具函数到模板"""
        from utils import format_datetime, format_price, get_status_text, truncate_decimal
        return {
            'format_datetime': format_datetime,
            'format_price': format_price,
            'get_status_text': get_status_text,
            'truncate_decimal': truncate_decimal
        }