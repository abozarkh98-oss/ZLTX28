from datetime import datetime, timedelta
import os
from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'zlt-x28-ultimate-secure-production-key-9999'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///modem_shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

@app.before_request
def make_session_permanent():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=7)

# --- دیتابیس مدل‌ها ---
class Package(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(20))
    name = db.Column(db.String(100))
    data_amount = db.Column(db.String(50))
    price = db.Column(db.String(50))
    desc = db.Column(db.String(200))
    tag = db.Column(db.String(50))

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    package_name = db.Column(db.String(100))
    price = db.Column(db.String(50))
    status = db.Column(db.String(20), default='در انتظار بررسی') # در انتظار بررسی، تایید شد، رد شد
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))
    total_gb = db.Column(db.Float, default=50.0)
    used_gb = db.Column(db.Float, default=15.5)
    days_left = db.Column(db.Integer, default=20)
    signal = db.Column(db.String(50), default='-78 dBm (عالی)')

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50))
    message = db.Column(db.Text)
    sender = db.Column(db.String(20)) # 'user' یا 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BroadcastMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    target_user = db.Column(db.String(50), default='ALL') # 'ALL' برای همگانی یا نام کاربری خاص
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    if not UserData.query.filter_by(username='user123').first():
        default_user = UserData(username='user123', password='123', total_gb=50.0, used_gb=15.5, days_left=20)
        db.session.add(default_user)
        db.session.commit()

    if not Package.query.first():
        default_packages = [
            ('daily', 'بسته ۱ روزه', '۱ گیگابایت', '۱۵,۰۰۰', 'بسته اقتصادی روزانه مناسب کارهای سبک', 'اقتصادی'),
            ('daily', 'بسته ۱ روزه ویژه', '۵ گیگابایت', '۴۵,۰۰۰', 'همراه با ۱۰٪ تخفیف ویژه مصرف روزانه', 'تخفیف‌دار 10%'),
            ('weekly', 'بسته ۷ روزه استاندارد', '۵ گیگابایت', '۵۰,۰۰۰', 'مقرون‌به‌صرفه برای یک هفته کار', 'اقتصادی'),
            ('weekly', 'بسته ۷ روزه پرطرفدار', '۷ گیگابایت', '۷۰,۰۰۰', 'مناسب برای استریم متوسط', 'پرفروش'),
            ('monthly', 'بسته ۳۰ روزه استاندارد', '۵ گیگابایت', '۶۵,۰۰۰', 'بسته پایه ماهانه برای اتصال دائمی', 'اقتصادی'),
            ('monthly', 'بسته ۳۰ روزه سنگین', '۵۰ گیگابایت', '۶۰۰,۰۰۰', 'حجم بالا برای ترافیک کاری', 'پرفروش'),
        ]
        for p in default_packages:
            db.session.add(Package(category=p[0], name=p[1], data_amount=p[2], price=p[3], desc=p[4], tag=p[5]))
        db.session.commit()

@app.route('/')
def index():
    packages = Package.query.all()
    pkgs_dict = {'daily': [], 'weekly': [], 'monthly': []}
    for p in packages:
        pkgs_dict[p.category].append({
            'id': p.id, 'name': p.name, 'data': p.data_amount, 'price': p.price, 'desc': p.desc, 'tag': p.tag
        })
    online_count = 19
    broadcasts = BroadcastMessage.query.order_by(BroadcastMessage.created_at.desc()).limit(5).all()
    return render_template('index.html', packages=pkgs_dict, online_count=online_count, broadcasts=broadcasts)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # بررسی دقیق وجود کاربر در دیتابیس (جلوگیری از ورود یوزرهای الکی)
    user = UserData.query.filter_by(username=username, password=password).first()
    if user:
        remaining = round(user.total_gb - user.used_gb, 2)
        percent = int((user.used_gb / user.total_gb) * 100) if user.total_gb > 0 else 0
        return jsonify({
            'success': True,
            'username': user.username,
            'total': user.total_gb,
            'used': user.used_gb,
            'remaining': remaining,
            'percent': percent,
            'days': user.days_left,
            'signal': user.signal
        })
    return jsonify({
        'success': False, 
        'message': '❌ یوزرنیم یا پسورد اشتباه یا وجود ندارد! لطفا از ادمین درخواست اکانت کنید.'
    })

@app.route('/api/order', methods=['POST'])
def submit_order():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # اعتبارسنجی سخت‌گیرانه موقع ثبت سفارش
    user = UserData.query.filter_by(username=username, password=password).first()
    if not user:
        return jsonify({
            'success': False, 
            'message': '❌ یوزرنیم یا پسورد اشتباه یا وجود ندارد! لطفا از ادمین درخواست اکانت کنید.'
        })
    
    new_order = Order(username=username, package_name=data.get('packageName'), price=data.get('price'))
    db.session.add(new_order)
    db.session.commit()
    return jsonify({'success': True, 'message': 'سفارش شما با موفقیت ثبت شد و در انتظار تایید ادمین است. ✅'})

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    data = request.json
    username = data.get('username')
    message = data.get('message')
    if username and message:
        chat = ChatMessage(username=username, message=message, sender='user')
        db.session.add(chat)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/api/get_chats/<username>')
def get_chats(username):
    chats = ChatMessage.query.filter_by(username=username).order_by(ChatMessage.created_at.asc()).all()
    return jsonify([{'sender': c.sender, 'message': c.message, 'time': c.created_at.strftime('%H:%M')} for c in chats])

# --- پنل ادمین ---
@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == 'Khani_1396':
            session['is_admin'] = True
        else:
            return render_template('admin_login.html', error='نام کاربری یا رمز عبور اشتباه است')

    if session.get('is_admin'):
        orders = Order.query.order_by(Order.created_at.desc()).all()
        packages = Package.query.all()
        users = UserData.query.all()
        chats = ChatMessage.query.order_by(ChatMessage.created_at.desc()).all()
        online_count = 19
        return render_template('admin_dashboard.html', orders=orders, packages=packages, users=users, chats=chats, online_count=online_count)
    
    return render_template('admin_login.html')

@app.route('/admin/order_action/<int:order_id>/<action>')
def order_action(order_id, action):
    if not session.get('is_admin'): return redirect(url_for('admin_panel'))
    order = Order.query.get_or_404(order_id)
    if action == 'accept':
        order.status = 'تایید شد ✅'
        # افزایش حجم کاربر به صورت خودکار پس از تایید
        user = UserData.query.filter_by(username=order.username).first()
        if user:
            user.total_gb += 10.0 # فرض افزودن ۱۰ گیگ به عنوان هدیه بسته
    else:
        order.status = 'رد شد ❌'
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/broadcast', methods=['POST'])
def send_broadcast():
    if not session.get('is_admin'): return redirect(url_for('admin_panel'))
    target = request.form.get('target_user', 'ALL')
    msg = request.form.get('message')
    if msg:
        b = BroadcastMessage(target_user=target, message=msg)
        db.session.add(b)
        db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/add_user', methods=['POST'])
def add_user():
    if not session.get('is_admin'): return redirect(url_for('admin_panel'))
    new_u = UserData(
        username=request.form.get('username'),
        password=request.form.get('password'),
        total_gb=float(request.form.get('total_gb', 50)),
        used_gb=0.0,
        days_left=30
    )
    db.session.add(new_u)
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_panel'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
