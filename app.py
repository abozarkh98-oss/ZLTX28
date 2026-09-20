from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# دیتابیس فرضی کاربران برای تست سیستم لاگین و پنل
users_db = {
    "user123": {
        "password": "123",
        "username": "user123",
        "total": 50,
        "used": 18.4,
        "remaining": 31.6,
        "days": 14,
        "signal": "4.5G عالی",
        "percent": 36,
        "private_message": "لطفاً جهت تمدید بسته ماهانه از طریق پنل اقدام کنید."
    }
}

# چت‌های کاربران
chats_db = {
    "user123": [
        {"is_admin": True, "message": "سلام! چطور می‌توانیم کمک‌تان کنیم؟"},
        {"is_admin": False, "message": "سلام، بسته من کی فعال میشه؟"}
    ]
}

@app.route('/')
def index():
    # اینجا نام فایل جدید شما تنظیم شده است تا مشکل کش حل شود
    return render_template('index_new.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if username in users_db and users_db[username]['password'] == password:
        user_data = users_db[username].copy()
        user_data['success'] = True
        return jsonify(user_data)
    else:
        return jsonify({
            "success": False,
            "message": "نام کاربری یا رمز عبور اشتباه است!"
        })

@app.route('/api/order', methods=['POST'])
def api_order():
    data = request.get_json()
    username = data.get('username')
    package_name = data.get('packageName')
    price = data.get('price')

    if username in users_db:
        return jsonify({
            "success": True,
            "message": f"بسته {package_name} با موفقیت برای شما ثبت شد. مبلغ: {price} تومان"
        })
    else:
        return jsonify({
            "success": False,
            "message": "لطفاً ابتدا وارد حساب کاربری خود شوید."
        })

@app.route('/api/chat/get/<username>', methods=['GET'])
def get_chat(username):
    chats = chats_db.get(username, [])
    return jsonify({"success": True, "chats": chats})

@app.route('/api/chat/send', methods=['POST'])
def send_chat():
    data = request.get_json()
    username = data.get('username')
    message = data.get('message')
    is_admin = data.get('isAdmin', False)

    if username not in chats_db:
        chats_db[username] = []
    
    chats_db[username].append({"is_admin": is_admin, "message": message})
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
