from datetime import datetime
from flask import Flask, jsonify, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'zlt-x28-super-secret-key-change-it'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///modem_shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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
    status = db.Column(db.String(20), default='در انتظار بررسی')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class UserData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))
    total_gb = db.Column(db.Float, default=50.0)
    used_gb = db.Column(db.Float, default=0.0)
    days_left = db.Column(db.Integer, default=30)
    signal = db.Column(db.String(50), default='-78 dBm (عالی)')

with app.app_context():
    db.create_all()
    if not UserData.query.filter_by(username='user123').first():
        default_user = UserData(username='user123', password='123', total_gb=50.0, used_gb=15.5, days_left=20)
        db.session.add(default_user)
        db.session.commit()

    if not Package.query.first():
        default_packages = [
            ('daily', 'بسته ۱ روزه', '۱ گیگابایت', '۱۵,۰۰۰', 'بسته اقتصادی روزانه مناسب کارهای سبک', 'اقتصادی'),
            ('daily', 'بسته ۱ روزه', '۲ گیگابایت', '۲۰,۰۰۰', 'سرعت فوق‌العاده مناسب وب‌گردی', 'پرفروش'),
            ('daily', 'بسته ۱ روزه', '۳ گیگابایت', '۳۰,۰۰۰', 'حجم مطلوب برای استفاده یک روزه', 'استاندارد'),
            ('daily', 'بسته ۱ روزه ویژه', '۵ گیگابایت', '۴۵,۰۰۰', 'همراه با ۱۰٪ تخفیف ویژه مصرف روزانه', 'تخفیف‌دار 10%'),
            ('weekly', 'بسته ۷ روزه استاندارد', '۵ گیگابایت', '۵۰,۰۰۰', 'مقرون‌به‌صرفه برای یک هفته کار', 'اقتصادی'),
            ('weekly', 'بسته ۷ روزه پرطرفدار', '۷ گیگابایت', '۷۰,۰۰۰', 'مناسب برای استریم متوسط', 'پرفروش'),
            ('weekly', 'بسته ۷ روزه حرفه‌ای', '۹ گیگابایت', '۹۰,۰۰۰', 'حجم مناسب برای بالاترین سرعت', 'پیشنهاد ما'),
            ('monthly', 'بسته ۳۰ روزه استاندارد', '۵ گیگابایت', '۶۵,۰۰۰', 'بسته پایه ماهانه برای اتصال دائمی', 'اقتصادی'),
            ('monthly', 'بسته ۳۰ روزه متوسط', '۱۰ گیگابایت', '۱۳۰,۰۰۰', 'مناسب برای کاربران کم‌مصرف', 'متوسط'),
            ('monthly', 'بسته ۳۰ روزه سنگین', '۵۰ گیگابایت', '۶۰۰,۰۰۰', 'حجم بالا برای ترافیک کاری', 'پرفروش'),
            ('monthly', 'بسته شبانه ماهانه VIP', 'نامحدود (۲ تا ۹ صبح)', '۱۲۰,۰۰۰', 'مخصوص دانلودهای ساعات شبانه', 'شبانه VIP'),
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
    return render_template('index.html', packages=pkgs_dict)

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
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
    return jsonify({'success': False, 'message': 'نام کاربری یا رمز عبور اشتباه است.'})

@app.route('/api/order', methods=['POST'])
def submit_order():
    data = request.json
    new_order = Order(username=data.get('username'), package_name=data.get('packageName'), price=data.get('price'))
    db.session.add(new_order)
    db.session.commit()
    return jsonify({'success': True, 'message': 'سفارش شما با موفقیت ثبت شد و به ادمین ارسال گردید.'})

# --- پنل ادمین ---
@app.route('/admin', methods=['GET', 'POST'])
def admin_panel():
    if request.method == 'POST':
        # بررسی نام کاربری و رمز عبور جدید ادمین
        if request.form.get('username') == 'admin' and request.form.get('password') == 'Khani_1396':
            session['is_admin'] = True
        else:
            return render_template('admin_login.html', error='نام کاربری یا رمز عبور اشتباه است')

    if session.get('is_admin'):
        orders = Order.query.order_by(Order.created_at.desc()).all()
        packages = Package.query.all()
        users = UserData.query.all()
        return render_template('admin_dashboard.html', orders=orders, packages=packages, users=users)
    
    return render_template('admin_login.html')

@app.route('/admin/update_price/<int:pkg_id>', methods=['POST'])
def update_price(pkg_id):
    if not session.get('is_admin'): return redirect(url_for('admin_panel'))
    pkg = Package.query.get_or_404(pkg_id)
    pkg.price = request.form.get('price')
    pkg.tag = request.form.get('tag')
    db.session.commit()
    return redirect(url_for('admin_panel'))

@app.route('/admin/update_user/<int:user_id>', methods=['POST'])
def update_user(user_id):
    if not session.get('is_admin'): return redirect(url_for('admin_panel'))
    user = UserData.query.get_or_404(user_id)
    user.total_gb = float(request.form.get('total_gb', user.total_gb))
    user.used_gb = float(request.form.get('used_gb', user.used_gb))
    user.days_left = int(request.form.get('days_left', user.days_left))
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
    app.run(debug=True)