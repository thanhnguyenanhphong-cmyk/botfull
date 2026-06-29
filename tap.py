import telebot
from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
import requests
import json
import os
import random
import threading
import time
import string
from datetime import datetime, timedelta
from flask import Flask

TOKEN = '8978234983:AAEGEPZEv-XmN7RQT2PXgzwPTTg6_PaZrwQ'
ADMIN_ID = 7338417401
ADMIN_CONTACT = '@phong296'

BANK_BIN = 'MBBANK'
BANK_ACC = '8885010104'
BANK_NAME = 'NGUYEN CANH HOANG SON'

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Telegram đang hoạt động!"


DB_FILE = 'database.json'

auto_predict_status = {}
predict_threads = {}
feedback_state = {}
last_deposit_time = {}

def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "keys": {}, "giftcodes": {}, "pending_deposits": {}}
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"users": {}, "keys": {}, "giftcodes": {}, "pending_deposits": {}}

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

def get_user(user_id):
    user_id = str(user_id)
    if user_id not in db["users"]:
        db["users"][user_id] = {"username": "", "balance": 0, "key_expiry": None}
        save_db(db)
    return db["users"][user_id]

def update_user(user_id, **kwargs):
    user = get_user(user_id)
    for k, v in kwargs.items():
        user[k] = v
    db["users"][str(user_id)] = user
    save_db(db)

def check_active_key(user_id):
    user = get_user(user_id)
    if not user.get("key_expiry"):
        return False
    expiry = datetime.fromisoformat(user["key_expiry"])
    if datetime.now() > expiry:
        update_user(user_id, key_expiry=None)
        return False
    return True

def resolve_user(input_str):
    input_str = str(input_str).strip().replace('@', '')
    if input_str in db["users"]:
        return input_str
    for uid, info in db["users"].items():
        if info.get("username", "").lower() == input_str.lower():
            return uid
    return None

def auto_update_username(message):
    if message.from_user.username:
        update_user(message.from_user.id, username=message.from_user.username)

# Cập nhật API mới
API_URLS = {
    "Sunwin TX": "https://sun-nc01.onrender.com/predict",
    "Sunwin Sicbo": "https://sunsb.onrender.com/predict",
    "LC79 TX": "https://lctx-34eg.onrender.com/predict",
    "LC79 TX MD5": "https://lcmd5-1c2y.onrender.com/predict",
    "BetVip TX": "https://bettx-sxbw.onrender.com/predict",
    "BetVip TX MD5": "https://betmd5-6nid.onrender.com/predict",
    "68GB TX": "https://six8tx-yky8.onrender.com/predict",
    "68GB TX MD5": "https://six8md5-5srv.onrender.com/predict"
}
def kb_main(user_id):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎲 Menu Game", "💎 Thông tin")
    markup.add("💵 Nạp Tiền", "🗝️ Mua Key")
    if str(user_id) == str(ADMIN_ID):
        markup.add("👑⚙️ Admin")
    return markup
def kb_game():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎰 SUNWIN", "🎰 HITCLUB")
    markup.add("🎰 LC79", "🎰 BETVIP")
    markup.add("🎰 68GB", "🃏 BACCARAT")
    markup.add("🏠🔙 Quay Lại")
    return markup
def kb_sunwin():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎲 Sunwin TX", "🎲 Sunwin Sicbo")
    markup.add("🔙 Quay Lại")
    return markup

def kb_hitclub():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎲 Hitclub TX", "🎲 Hitclub MD5")
    markup.add("🔙 Quay Lại")
    return markup

def kb_lc79():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎲 LC79 TX", "🎲 LC79 TX MD5")
    markup.add("🔙 Quay Lại")
    return markup

def kb_betvip():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎲 BetVip TX", "🎲 BetVip TX MD5")
    markup.add("🔙 Quay Lại")
    return markup

def kb_68gb():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🎲 68GB TX", "🎲 68GB TX MD5")
    markup.add("🔙 Quay Lại")
    return markup
def kb_game_with_auto(game_name):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(f"🔴 Tắt Auto - {game_name}")
    markup.add("🏠🔙 Quay Lại")
    return markup

def kb_deposit():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("💵 50K", "💵 100K")
    markup.add("💵 200K", "💵 500K")
    markup.add("✍️ Nhập số", "🏠 Quay Lại")
    return markup

def kb_buy_key():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🗝️ 12 giờ - 15.000đ", "🗝️ 1 ngày - 30.000đ")
    markup.add("🗝️ 3 ngày - 50.000đ", "🗝️ 7 ngày - 80.000đ")
    markup.add("🗝️ 15 ngày - 130.000đ", "🗝️ 1 tháng - 170.000đ")
    markup.add("🗝️ Vĩnh viễn - 250.000đ", "🏠 Quay Lại")
    return markup

def kb_admin():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🔑 Key", "💰 Tiền")
    markup.add("🎁 Giftcode", "✅ Duyệt Nạp")
    markup.add("👥 Users", "📢 Thông báo")
    markup.add("🏠 Quay Lại")
    return markup

def kb_admin_key():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("➕ Tạo Key", "➖ Xóa Key")
    markup.add("🏠 Quay Lại Admin")
    return markup

def kb_admin_money():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("➕ Cộng Tiền", "➖ Trừ Tiền")
    markup.add("💰 Tổng Dư", "🏠 Quay Lại Admin")
    return markup

def kb_admin_giftcode():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("➕ Tạo Code", "➖ Xóa Code")
    markup.add("📋 DS Code", "🏠 Quay Lại Admin")
    return markup

def kb_cancel():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("❌ Hủy")
    return markup

def kb_admin_cancel():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🏠 Quay Lại Admin")
    return markup

def back_to_main(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    user_id = message.from_user.id
    if user_id in auto_predict_status and auto_predict_status[user_id]["active"]:
        stop_auto_predict(user_id)
    if user_id in feedback_state:
        del feedback_state[user_id]
    bot.send_message(message.chat.id, "🏡 Quay lại Menu chính", reply_markup=kb_main(message.from_user.id))

def back_admin(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    bot.send_message(message.chat.id, "👑 Bảng điều khiển Admin", reply_markup=kb_admin())

def format_game_data(data, game_name):
    def get_val(keys):
        for k in keys:
            if k in data: return data[k]
        return None

    phien_cu = get_val(['Phien', 'phien'])
    xuc_xac = ""
    xx1 = get_val(['Xuc_xac_1', 'xuc_xac_1'])
    xx2 = get_val(['Xuc_xac_2', 'xuc_xac_2'])
    xx3 = get_val(['Xuc_xac_3', 'xuc_xac_3'])
    xx_arr = get_val(['Xuc_xac', 'xuc_xac'])
    
    if xx1 and xx2 and xx3: xuc_xac = f"{xx1} - {xx2} - {xx3}"
    elif xx_arr:
        if isinstance(xx_arr, list): xuc_xac = " - ".join(map(str, xx_arr))
        else: xuc_xac = str(xx_arr)

    tong = get_val(['Tong', 'tong'])
    ket_qua = get_val(['Ket_qua', 'ket_qua'])
    phien_moi = get_val(['phien_hien_tai', 'Phien_hien_tai'])
    du_doan = get_val(['du_doan', 'Du_doan'])
    du_doan_vi = get_val(['du_doan_vi', 'dudoan_vi', 'Du_doan_vi'])
    du_doan_cl = get_val(['du_doan_chan_le'])

    # Format đẹp hơn
    msg = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"🎯 <b>{game_name.upper()}</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"📊 <b>KẾT QUẢ TRƯỚC</b>\n"
    msg += f"🔖 Phiên: <code>{phien_cu or 'N/A'}</code>\n"
    msg += f"🎲 Xúc xắc: {xuc_xac or 'N/A'}\n"
    msg += f"🧮 Tổng điểm: <b>{tong or 'N/A'}</b>\n"
    msg += f"🏆 Kết quả: <b>{ket_qua or 'N/A'}</b>\n\n"
    msg += f"🚀 <b>DỰ ĐOÁN PHIÊN TIẾP THEO</b>\n"
    msg += f"📌 Phiên: <code>{phien_moi or 'N/A'}</code>\n"
    msg += f"🔥 <b>👉 {str(du_doan).upper()} 👈</b>\n"
    
    if du_doan_vi: msg += f"📍 Vị trí: {du_doan_vi}\n"
    if du_doan_cl: msg += f"☯️ Chẵn/Lẻ: {du_doan_cl}\n"
    msg += f"\n🔄 <i>Đang theo dõi tự động...</i>"
    
    return msg

def auto_predict_worker(user_id, game_name, api_url):
    last_phien = None
    check_interval = 5
    
    while user_id in auto_predict_status and auto_predict_status[user_id]["active"]:
        try:
            req = requests.get(api_url, timeout=10)
            req.raise_for_status()
            data = req.json()
            
            phien_moi = data.get('phien_hien_tai') or data.get('Phien_hien_tai')
            
            if phien_moi and phien_moi != last_phien:
                msg = format_game_data(data, game_name)
                try:
                    bot.send_message(user_id, msg, reply_markup=kb_game_with_auto(game_name))
                    last_phien = phien_moi
                except Exception as e:
                    print(f"Lỗi gửi auto predict cho {user_id}: {e}")
                    if "blocked" in str(e).lower():
                        stop_auto_predict(user_id)
                        break
            
        except Exception as e:
            print(f"Lỗi auto predict {user_id}: {e}")
        
        time.sleep(check_interval)

def start_auto_predict(user_id, game_name, api_url):
    if user_id in auto_predict_status and auto_predict_status[user_id]["active"]:
        stop_auto_predict(user_id)
    
    auto_predict_status[user_id] = {
        "active": True,
        "game_name": game_name,
        "api_url": api_url
    }
    
    thread = threading.Thread(target=auto_predict_worker, args=(user_id, game_name, api_url))
    thread.daemon = True
    thread.start()
    predict_threads[user_id] = thread

def stop_auto_predict(user_id):
    if user_id in auto_predict_status:
        auto_predict_status[user_id]["active"] = False
        del auto_predict_status[user_id]
    if user_id in predict_threads:
        del predict_threads[user_id]

@bot.message_handler(commands=['start'])
def start(message):
    user = message.from_user
    get_user(user.id)
    update_user(user.id, username=user.username or "No_Username")

    msg = (
        "👑━━━━━━━━━━━━━━━━━━━━👑\n"
        "💎 <b>『 TOOL VIP PREMIUM 』</b> 💎\n"
        "👑━━━━━━━━━━━━━━━━━━━━👑\n\n"

        f"🎉 Xin chào <b>{user.first_name}</b>!\n"
        "✨ Chào mừng bạn đến với hệ thống dự đoán VIP.\n\n"

        "🎰 Soi cầu thuật toán đa nền tảng\n"
        "📊 Cập nhật dữ liệu theo thời gian thực\n"
        "💎 Kích hoạt VIP để mở toàn bộ tính năng\n"
        "💳 Nạp tiền tự động • Nhanh • An toàn\n"

        "👇 <b>Chọn chức năng bên dưới để bắt đầu!</b> 👇"
    )

    bot.send_message(
        message.chat.id,
        msg,
        parse_mode="HTML",
        reply_markup=kb_main(user.id)
    )
@bot.message_handler(func=lambda msg: msg.text in ["🏠 Quay Lại", "🏠 Quay Lại Game", "🏠 Quay Lại Admin", "❌ Hủy", "🏠🔙 Quay Lại"])
def handle_back_cancel(message):
    user_id = message.from_user.id
    bot.clear_step_handler_by_chat_id(message.chat.id)
    
    if user_id in auto_predict_status:
        stop_auto_predict(user_id)
    if user_id in feedback_state:
        del feedback_state[user_id]

    if "Admin" in message.text and str(user_id) == str(ADMIN_ID):
        bot.send_message(message.chat.id, "👑 <b>BẢNG ĐIỀU KHIỂN ADMIN</b>", reply_markup=kb_admin())
    else:
        bot.send_message(message.chat.id, "🏡 <b>QUAY LẠI MENU CHÍNH</b>", reply_markup=kb_main(user_id))

@bot.message_handler(func=lambda msg: msg.text == "💎 Thông tin")
def user_info(message):
    auto_update_username(message)
    user_id = message.from_user.id
    user = get_user(user_id)
    status = "🔴 Chưa có Key"
    if check_active_key(user_id):
        expiry = datetime.fromisoformat(user["key_expiry"]).strftime("%d/%m/%Y %H:%M:%S")
        status = f"🟢 Còn hạn: {expiry}"

    msg = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"👤 <b>HỒ SƠ CÁ NHÂN</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"🆔 ID: <code>{user_id}</code>\n"
    msg += f"👤 Username: @{user['username']}\n"
    msg += f"💰 Số dư: <b>{user['balance']:,} VNĐ</b>\n"
    msg += f"🔑 VIP: {status}\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    bot.send_message(message.chat.id, msg)

@bot.message_handler(func=lambda msg: msg.text == "💵 Nạp Tiền")
def deposit_menu(message):
    auto_update_username(message)
    bot.send_message(message.chat.id, "💰 <b>NẠP TIỀN</b>\nChọn số tiền:", reply_markup=kb_deposit())

@bot.message_handler(func=lambda msg: msg.text and (msg.text.startswith("💵 ") and "K" in msg.text))
def process_deposit_preset(message):
    amt_str = message.text.split()[1].replace("K", "000")
    generate_qr_direct(message, int(amt_str))

@bot.message_handler(func=lambda msg: msg.text == "✍️ Nhập số")
def process_deposit_custom(message):
    msg_sent = bot.send_message(message.chat.id, "✍️ Nhập số tiền (VND):\n(Ví dụ: 50000)", reply_markup=kb_cancel())
    bot.register_next_step_handler(msg_sent, step_generate_qr)

def step_generate_qr(message):
    if message.text in["❌ Hủy", "🏠 Quay Lại"]: return back_to_main(message)
    try:
        amount = int(message.text.replace(",", "").replace(".", ""))
        if amount < 10000:
            bot.send_message(message.chat.id, "❌ Tối thiểu 10,000đ", reply_markup=kb_deposit())
            return
        generate_qr_direct(message, amount)
    except:
        bot.send_message(message.chat.id, "❌ Số tiền không hợp lệ", reply_markup=kb_deposit())

def generate_qr_direct(message, amount):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        now = time.time()
        last = last_deposit_time.get(user_id, 0)
        if now - last < 300:
            bot.send_message(message.chat.id, "⏳ Vui lòng chờ 5 phút giữa các lần nạp tiền.", reply_markup=kb_deposit())
            return
        last_deposit_time[user_id] = now

    chat_id = str(message.chat.id)
    content = f"naptien {random.randint(10000, 99999)}"
    qr_url = f"https://qr.sepay.vn/img?acc={BANK_ACC}&bank={BANK_BIN}&amount={amount}&des={content.replace(' ', '%20')}"
    
    msg = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"🏦 <b>THANH TOÁN</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"🏦 Ngân hàng: <b>{BANK_BIN}</b>\n"
    msg += f"👤 Chủ TK: <b>{BANK_NAME}</b>\n"
    msg += f"💳 Số TK: <code>{BANK_ACC}</code>\n"
    msg += f"💰 Số tiền: <b>{amount:,} VNĐ</b>\n"
    msg += f"📝 Nội dung: <code>{content}</code>\n\n"
    msg += "⚠️ <b>HƯỚNG DẪN:</b>\n"
    msg += "1️⃣ Quét mã QR bên dưới\n"
    msg += "2️⃣ Chuyển khoản thành công\n"
    msg += "3️⃣ GỬI ẢNH BIÊN LAI VÀO ĐÂY"

    sent_msg = bot.send_photo(chat_id, qr_url, caption=msg, reply_markup=kb_cancel())
    bot.register_next_step_handler(sent_msg, receive_bill, amount, content)

def receive_bill(message, amount, content):
    if message.text in ["❌ Hủy", "🏠 Quay Lại"]:
        return back_to_main(message)

    if not message.photo:
        sent = bot.send_message(
            message.chat.id,
            "❌ Gửi lại ảnh biên lai!",
            reply_markup=kb_cancel()
        )
        bot.register_next_step_handler(sent, receive_bill, amount, content)
        return

    chat_id = str(message.chat.id)
    photo_id = message.photo[-1].file_id
    username = message.from_user.username or "No_Username"

    trans_id = f"{chat_id}_{random.randint(1000, 9999)}"

    db["pending_deposits"][trans_id] = {
        "uid": chat_id,
        "amount": amount,
        "content": content,
        "photo_id": photo_id,
        "username": username
    }
    save_db(db)

    bot.send_message(
        chat_id,
        "✅ Đã nhận ảnh! Chờ Admin duyệt nhé!",
        reply_markup=kb_main(message.chat.id)
    )

    admin_caption = (
        "🔔 <b>THÔNG BÁO GIAO DỊCH</b> 🔔\n"
        "────────────────────\n"
        f"👤 Người dùng: @{username}\n"
        f"💰 Số tiền: {amount:,} VND\n"
        f"📝 Nội dung: <code>{content}</code>\n"
        "⚙️ Trạng thái: ⏳ Chờ duyệt\n"
        "────────────────────\n"
        "👑 @Toolgamepro_bot"
    )

    inline_markup = InlineKeyboardMarkup()
    inline_markup.row(
        InlineKeyboardButton("✅ Duyệt", callback_data=f"approve_{trans_id}"),
        InlineKeyboardButton("❌ Từ chối", callback_data=f"reject_{trans_id}")
    )

    bot.send_photo(
        ADMIN_ID,
        photo_id,
        caption=admin_caption,
        parse_mode="HTML",
        reply_markup=inline_markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def handle_deposit_action(call):
    if str(call.from_user.id) != str(ADMIN_ID):
        bot.answer_callback_query(call.id, "⛔ Không có quyền!")
        return

    action, trans_id = call.data.split("_", 1)

    if trans_id not in db["pending_deposits"]:
        bot.answer_callback_query(call.id, "⚠️ Giao dịch đã xử lý!")
        return

    dep_info = db["pending_deposits"][trans_id]
    target_uid = dep_info["uid"]
    amount = dep_info["amount"]

    if action == "approve":
        user = get_user(target_uid)
        update_user(target_uid, balance=user["balance"] + amount)

        new_caption = (
            "🔔 <b>THÔNG BÁO GIAO DỊCH</b> 🔔\n"
            "────────────────────\n"
            f"👤 Người dùng: @{dep_info['username']}\n"
            f"💰 Số tiền: {amount:,} VND\n"
            f"📝 Nội dung: <code>{dep_info['content']}</code>\n"
            "⚙️ Trạng thái: ✅ Đã duyệt\n"
            "────────────────────\n"
            "👑 @Toolgamepro_bot"
        )

        bot.edit_message_caption(
            caption=new_caption,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML"
        )

        del db["pending_deposits"][trans_id]
        save_db(db)

        bot.answer_callback_query(call.id, "Đã duyệt!")

        try:
            bot.send_message(
                target_uid,
                f"🎉 NẠP TIỀN THÀNH CÔNG!\n"
                f"✅ +{amount:,} VNĐ\n"
                f"💰 Số dư: {db['users'][target_uid]['balance']:,} VNĐ"
            )
        except:
            pass

    elif action == "reject":

        new_caption = (
            "🔔 <b>THÔNG BÁO GIAO DỊCH</b> 🔔\n"
            "────────────────────\n"
            f"👤 Người dùng: @{dep_info['username']}\n"
            f"💰 Số tiền: {amount:,} VND\n"
            f"📝 Nội dung: <code>{dep_info['content']}</code>\n"
            "⚙️ Trạng thái: ❌ Đã từ chối\n"
            "────────────────────\n"
            "👑 @Toolgamepro_bot"
        )

        bot.edit_message_caption(
            caption=new_caption,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML"
        )

        del db["pending_deposits"][trans_id]
        save_db(db)

        bot.answer_callback_query(call.id, "Đã từ chối!")

        try:
            bot.send_message(
                target_uid,
                "❌ NẠP TIỀN THẤT BẠI\nBiên lai không hợp lệ. Liên hệ Admin!"
            )
        except:
            pass
@bot.message_handler(func=lambda msg: msg.text == "🗝️ Mua Key")
def buy_key_menu(message):
    auto_update_username(message)
    msg = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += "🛒 <b>BẢNG GIÁ VIP</b>\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "👉 Chọn gói bên dưới:"
    bot.send_message(message.chat.id, msg, reply_markup=kb_buy_key())

@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith("🗝️ "))
def process_buy_key(message):
    packages = {
        "🗝️ 12 giờ - 15.000đ": (0.5, 15000),
        "🗝️ 1 ngày - 30.000đ": (1, 30000),
        "🗝️ 3 ngày - 50.000đ": (3, 50000),
        "🗝️ 7 ngày - 80.000đ": (7, 80000),
        "🗝️ 15 ngày - 130.000đ": (15, 130000),
        "🗝️ 1 tháng - 170.000đ": (30, 170000),
        "🗝️ Vĩnh viễn - 250.000đ": (9999, 250000)
    }
    
    if message.text not in packages: return
    
    days, price = packages[message.text]
    user_id = str(message.chat.id)
    user = get_user(user_id)
    
    if user["balance"] < price:
        bot.send_message(message.chat.id, "❌ Số dư không đủ! Vui lòng nạp tiền.")
        return
        
    update_user(user_id, balance=user["balance"] - price)
    
    current_expiry = datetime.now()
    if user.get("key_expiry"):
        exp = datetime.fromisoformat(user["key_expiry"])
        if exp > current_expiry:
            current_expiry = exp
            
    new_expiry = current_expiry + timedelta(days=days)
    update_user(user_id, key_expiry=new_expiry.isoformat())
    
    msg = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"🎉 <b>MUA VIP THÀNH CÔNG</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"✅ Gói: <b>{days} ngày</b>\n"
    msg += f"⏰ Hạn: <b>{new_expiry.strftime('%d/%m/%Y %H:%M:%S')}</b>\n"
    msg += f"💰 Còn lại: <b>{db['users'][user_id]['balance']:,} VNĐ</b>\n\n"
    msg += f"👉 Chọn '🎮🎲 Menu Game' để bắt đầu!"
    
    bot.send_message(message.chat.id, msg, reply_markup=kb_main(user_id))

    username = message.from_user.username or "No_Username"
    admin_msg = (
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "💎 THÔNG BÁO MUA KEY 💎\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    f"👤 Khách hàng: @{username}\n"
    f"🗝 Gói VIP: {message.text}\n"
    f"💰 Thanh toán: {price:,} VNĐ\n"
    "⚙️ Trạng thái: ✅ Thành công\n"
    "━━━━━━━━━━━━━━━━━━━━━━\n"
    "👑 @Toolgamepro_bot"
)
    try:
        bot.send_message(ADMIN_ID, admin_msg)
    except:
        pass

@bot.message_handler(func=lambda msg: msg.text == "🎲 Menu Game")
def menu_game(message):
    auto_update_username(message)
    user_id = message.from_user.id
    if not check_active_key(user_id):
        bot.send_message(message.chat.id, "⛔ TÀI KHOẢN CHƯA KÍCH HOẠT VIP\nVui lòng chọn '🗝️ Mua Key'", reply_markup=kb_main(user_id))
        return
    bot.send_message(message.chat.id, "🎮 MENU GAME VIP\nChọn cổng game bên dưới:", reply_markup=kb_game())

@bot.message_handler(func=lambda msg: msg.text=="🎰 SUNWIN")
def menu_sunwin(message):
    bot.send_message(message.chat.id,"🎰 MENU SUNWIN",reply_markup=kb_sunwin())

@bot.message_handler(func=lambda msg: msg.text=="🎰 HITCLUB")
def menu_hitclub(message):
    bot.send_message(message.chat.id,"🎰 MENU HITCLUB",reply_markup=kb_hitclub())

@bot.message_handler(func=lambda msg: msg.text=="🎰 LC79")
def menu_lc79(message):
    bot.send_message(message.chat.id,"🎰 MENU LC79",reply_markup=kb_lc79())

@bot.message_handler(func=lambda msg: msg.text=="🎰 BETVIP")
def menu_betvip(message):
    bot.send_message(message.chat.id,"🎰 MENU BETVIP",reply_markup=kb_betvip())

@bot.message_handler(func=lambda msg: msg.text=="🎰 68GB")
def menu_68gb(message):
    bot.send_message(message.chat.id,"🎰 MENU 68GB",reply_markup=kb_68gb())
@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith("🎲 "))
def process_game(message):
    user_id = message.from_user.id
    if not check_active_key(user_id):
        bot.send_message(message.chat.id, "⛔ Key VIP đã hết hạn!", reply_markup=kb_main(user_id))
        return

    game_name = message.text.replace("🎲 ", "")
    api_url = API_URLS.get(game_name)
    
    if not api_url:
        return
        
    try:
        req = requests.get(api_url, timeout=10)
        req.raise_for_status()
        data = req.json()
        
        def get_val(keys):
            for k in keys:
                if k in data: return data[k]
            return None

        phien_cu = get_val(['Phien', 'phien'])
        xuc_xac = ""
        xx1 = get_val(['Xuc_xac_1', 'xuc_xac_1'])
        xx2 = get_val(['Xuc_xac_2', 'xuc_xac_2'])
        xx3 = get_val(['Xuc_xac_3', 'xuc_xac_3'])
        xx_arr = get_val(['Xuc_xac', 'xuc_xac'])
        
        if xx1 and xx2 and xx3: xuc_xac = f"{xx1} - {xx2} - {xx3}"
        elif xx_arr:
            if isinstance(xx_arr, list): xuc_xac = " - ".join(map(str, xx_arr))
            else: xuc_xac = str(xx_arr)

        tong = get_val(['Tong', 'tong'])
        ket_qua = get_val(['Ket_qua', 'ket_qua'])
        phien_moi = get_val(['phien_hien_tai', 'Phien_hien_tai'])
        du_doan = get_val(['du_doan', 'Du_doan'])
        du_doan_vi = get_val(['du_doan_vi', 'dudoan_vi', 'Du_doan_vi'])
        du_doan_cl = get_val(['du_doan_chan_le'])

        msg = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🎯 <b>{game_name.upper()}</b>\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += f"📊 <b>KẾT QUẢ TRƯỚC</b>\n"
        msg += f"🔖 Phiên: <code>{phien_cu or 'N/A'}</code>\n"
        msg += f"🎲 Xúc xắc: {xuc_xac or 'N/A'}\n"
        msg += f"🧮 Tổng điểm: <b>{tong or 'N/A'}</b>\n"
        msg += f"🏆 Kết quả: <b>{ket_qua or 'N/A'}</b>\n\n"
        msg += f"🚀 <b>DỰ ĐOÁN PHIÊN TIẾP THEO</b>\n"
        msg += f"📌 Phiên: <code>{phien_moi or 'N/A'}</code>\n"
        msg += f"🔥 <b>👉 {str(du_doan).upper()} 👈</b>\n"
        
        if du_doan_vi: msg += f"📍 Vị trí: {du_doan_vi}\n"
        if du_doan_cl: msg += f"☯️ Chẵn/Lẻ: {du_doan_cl}\n"
        msg += f"\n🔄 Nhấn lại nút game để cập nhật\n"
        msg += f"⚡ Bật auto: Chọn game lần nữa để bật chế độ tự động"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔁 Bật Auto Dự Đoán", callback_data=f"auto_{game_name}"))
        bot.send_message(message.chat.id, msg, reply_markup=markup)
            
    except requests.exceptions.RequestException:
        bot.send_message(message.chat.id, f"❌ API đang bảo trì, vui lòng thử lại sau.")
    except Exception:
        bot.send_message(message.chat.id, f"❌ Lỗi xử lý dữ liệu, vui lòng thử lại.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('auto_'))
def handle_auto_predict(call):
    user_id = call.from_user.id
    
    if not check_active_key(user_id):
        bot.answer_callback_query(call.id, "⛔ Bạn cần mua Key VIP để sử dụng tính năng này!")
        return
    
    game_name = call.data.replace('auto_', '')
    api_url = API_URLS.get(game_name)
    
    if not api_url:
        bot.answer_callback_query(call.id, "❌ Không tìm thấy API!")
        return
    
    start_auto_predict(user_id, game_name, api_url)
    
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
    bot.send_message(user_id, f"✅ Đã bật chế độ <b>Auto Dự Đoán</b> cho {game_name}\n\n"
                     f"🔄 Hệ thống sẽ tự động gửi kết quả mỗi khi có phiên mới!\n"
                     f"🔴 Nhấn '🔴 Tắt Auto - {game_name}' để tắt.",
                     reply_markup=kb_game_with_auto(game_name))
    bot.answer_callback_query(call.id, "Đã bật Auto Dự Đoán!")

@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith("🔴 Tắt Auto - "))
def turn_off_auto_predict(message):
    user_id = message.from_user.id
    game_name = message.text.replace("🔴 Tắt Auto - ", "")
    
    stop_auto_predict(user_id)
    bot.send_message(message.chat.id, f"✅ Đã tắt chế độ Auto Dự Đoán cho {game_name}",
                    reply_markup=kb_game())

@bot.message_handler(func=lambda msg: msg.text == "🃏🎰 Baccarat")
def baccarat_menu(message):
    auto_update_username(message)
    user_id = message.from_user.id
    if not check_active_key(user_id):
        bot.send_message(message.chat.id, "⛔ Cần mua Key VIP!", reply_markup=kb_main(user_id))
        return
    msg = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"🃏 <b>BACCARAT SEXY</b>\n"
    msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"🏠 Có <b>{BACCARAT_TABLES} bàn</b>\n"
    msg += "👉 Chọn bàn bên dưới:"
    bot.send_message(message.chat.id, msg, reply_markup=kb_baccarat())

@bot.message_handler(func=lambda msg: msg.text == "🔙 Quay Lại")
def back_to_game(message):
    bot.send_message(message.chat.id, "🎮 MENU GAME VIP", reply_markup=kb_game())
@bot.message_handler(func=lambda msg: msg.text and msg.text.startswith("🃏 Bàn "))
def process_baccarat(message):
    user_id = message.from_user.id
    if not check_active_key(user_id):
        bot.send_message(message.chat.id, "⛔ Key VIP đã hết hạn!", reply_markup=kb_main(user_id))
        return

    try:
        table_num = int(message.text.replace("🃏 Bàn ", ""))
        if table_num < 1 or table_num > BACCARAT_TABLES:
            return
    except:
        return

    api_url = f"{BACCARAT_API_BASE}{table_num:02d}" if table_num < 10 else f"{BACCARAT_API_BASE}{table_num}"

    try:
        req = requests.get(api_url, timeout=10)
        req.raise_for_status()
        data = req.json()

        ban = data.get('ban', 'N/A')
        phien = data.get('phien', 'N/A')
        ket_qua = data.get('ket_qua', 'N/A')
        cau = data.get('cau', 'N/A')
        phien_hien_tai = data.get('phien_hien_tai', 'N/A')
        du_doan = data.get('du_doan', 'N/A')
        do_tin_cay = data.get('do_tin_cay', 'N/A')

        msg = f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"🃏 <b>BACCARAT SEXY</b>\n"
        msg += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        msg += f"🏠 Bàn: <b>{ban}</b>\n"
        msg += f"🔖 Phiên: <code>{phien}</code>\n"
        msg += f"📜 Chuỗi: {ket_qua}\n"
        msg += f"🔮 Cầu: <b>{cau}</b>\n\n"
        msg += f"🚀 <b>DỰ ĐOÁN</b>\n"
        msg += f"📌 Phiên: <code>{phien_hien_tai}</code>\n"
        msg += f"🔥 <b>👉 {str(du_doan).upper()} 👈</b>\n"
        msg += f"📈 Tỉ lệ: <b>{do_tin_cay}</b>\n\n"
        msg += f"🔄 Nhấn lại bàn để cập nhật"

        bot.send_message(message.chat.id, msg, reply_markup=kb_baccarat())

    except requests.exceptions.RequestException:
        bot.send_message(message.chat.id, "❌ API đang bảo trì, vui lòng thử lại.", reply_markup=kb_baccarat())
    except Exception:
        bot.send_message(message.chat.id, "❌ Lỗi xử lý dữ liệu.", reply_markup=kb_baccarat())

@bot.message_handler(func=lambda msg: msg.text == "👑⚙️ Admin" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_panel(message):
    bot.send_message(message.chat.id, "👑 Bảng điều khiển Admin", reply_markup=kb_admin())

@bot.message_handler(func=lambda msg: msg.text == "🔑 Key" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_key_menu(message):
    bot.send_message(message.chat.id, "🔑 Quản lý Key VIP", reply_markup=kb_admin_key())

@bot.message_handler(func=lambda msg: msg.text == "➕ Tạo Key" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_create_key(message):
    sent = bot.send_message(message.chat.id, "Nhập ID hoặc @username người dùng:", reply_markup=kb_admin_cancel())
    bot.register_next_step_handler(sent, admin_create_key_step2)

def admin_create_key_step2(message):
    if message.text == "🏠 Quay Lại Admin":
        back_admin(message)
        return
    target = resolve_user(message.text)
    if not target:
        bot.send_message(message.chat.id, "❌ Không tìm thấy user!", reply_markup=kb_admin_key())
        return
    sent = bot.send_message(message.chat.id, "Nhập số ngày VIP:", reply_markup=kb_admin_cancel())
    bot.register_next_step_handler(sent, admin_create_key_step3, target)

def admin_create_key_step3(message, target):
    if message.text == "🏠 Quay Lại Admin":
        back_admin(message)
        return
    try:
        days = int(message.text)
        user = get_user(target)
        current_expiry = datetime.now()
        if user.get("key_expiry"):
            exp = datetime.fromisoformat(user["key_expiry"])
            if exp > current_expiry:
                current_expiry = exp
        new_expiry = current_expiry + timedelta(days=days)
        update_user(target, key_expiry=new_expiry.isoformat())
        bot.send_message(message.chat.id, f"✅ Đã cấp {days} ngày VIP cho user {target}\nHạn: {new_expiry.strftime('%d/%m/%Y %H:%M:%S')}", reply_markup=kb_admin_key())
    except:
        bot.send_message(message.chat.id, "❌ Số ngày không hợp lệ!", reply_markup=kb_admin_key())

@bot.message_handler(func=lambda msg: msg.text == "➖ Xóa Key" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_remove_key(message):
    sent = bot.send_message(message.chat.id, "Nhập ID hoặc @username người dùng:", reply_markup=kb_admin_cancel())
    bot.register_next_step_handler(sent, admin_remove_key_step2)

def admin_remove_key_step2(message):
    if message.text == "🏠 Quay Lại Admin":
        back_admin(message)
        return
    target = resolve_user(message.text)
    if not target:
        bot.send_message(message.chat.id, "❌ Không tìm thấy user!", reply_markup=kb_admin_key())
        return
    update_user(target, key_expiry=None)
    bot.send_message(message.chat.id, f"✅ Đã xóa Key VIP của user {target}", reply_markup=kb_admin_key())

@bot.message_handler(func=lambda msg: msg.text == "💰 Tiền" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_money_menu(message):
    bot.send_message(message.chat.id, "💰 Quản lý số dư", reply_markup=kb_admin_money())

@bot.message_handler(func=lambda msg: msg.text == "➕ Cộng Tiền" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_add_money(message):
    sent = bot.send_message(message.chat.id, "Nhập ID hoặc @username người dùng:", reply_markup=kb_admin_cancel())
    bot.register_next_step_handler(sent, admin_add_money_step2)

def admin_add_money_step2(message):
    if message.text == "🏠 Quay Lại Admin":
        back_admin(message)
        return
    target = resolve_user(message.text)
    if not target:
        bot.send_message(message.chat.id, "❌ Không tìm thấy user!", reply_markup=kb_admin_money())
        return
    sent = bot.send_message(message.chat.id, "Nhập số tiền cần cộng:", reply_markup=kb_admin_cancel())
    bot.register_next_step_handler(sent, admin_add_money_step3, target)

def admin_add_money_step3(message, target):
    if message.text == "🏠 Quay Lại Admin":
        back_admin(message)
        return
    try:
        amount = int(message.text)
        user = get_user(target)
        new_bal = user["balance"] + amount
        update_user(target, balance=new_bal)
        bot.send_message(message.chat.id, f"✅ Đã cộng {amount:,} VNĐ cho user {target}\nSố dư mới: {new_bal:,} VNĐ", reply_markup=kb_admin_money())
    except:
        bot.send_message(message.chat.id, "❌ Số tiền không hợp lệ!", reply_markup=kb_admin_money())

@bot.message_handler(func=lambda msg: msg.text == "➖ Trừ Tiền" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_sub_money(message):
    sent = bot.send_message(message.chat.id, "Nhập ID hoặc @username người dùng:", reply_markup=kb_admin_cancel())
    bot.register_next_step_handler(sent, admin_sub_money_step2)

def admin_sub_money_step2(message):
    if message.text == "🏠 Quay Lại Admin":
        back_admin(message)
        return
    target = resolve_user(message.text)
    if not target:
        bot.send_message(message.chat.id, "❌ Không tìm thấy user!", reply_markup=kb_admin_money())
        return
    sent = bot.send_message(message.chat.id, "Nhập số tiền cần trừ:", reply_markup=kb_admin_cancel())
    bot.register_next_step_handler(sent, admin_sub_money_step3, target)

def admin_sub_money_step3(message, target):
    if message.text == "🏠 Quay Lại Admin":
        back_admin(message)
        return
    try:
        amount = int(message.text)
        user = get_user(target)
        if user["balance"] < amount:
            bot.send_message(message.chat.id, "❌ Số dư không đủ để trừ!", reply_markup=kb_admin_money())
            return
        new_bal = user["balance"] - amount
        update_user(target, balance=new_bal)
        bot.send_message(message.chat.id, f"✅ Đã trừ {amount:,} VNĐ cho user {target}\nSố dư mới: {new_bal:,} VNĐ", reply_markup=kb_admin_money())
    except:
        bot.send_message(message.chat.id, "❌ Số tiền không hợp lệ!", reply_markup=kb_admin_money())

@bot.message_handler(func=lambda msg: msg.text == "💰 Tổng Dư" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_total_balance(message):
    total = sum(u["balance"] for u in db["users"].values())
    bot.send_message(message.chat.id, f"💰 Tổng số dư toàn hệ thống: {total:,} VNĐ", reply_markup=kb_admin_money())

@bot.message_handler(func=lambda msg: msg.text == "🎁 Giftcode" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_giftcode_menu(message):
    bot.send_message(message.chat.id, "🎁 Quản lý Giftcode", reply_markup=kb_admin_giftcode())

@bot.message_handler(func=lambda msg: msg.text == "➕ Tạo Code" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_create_giftcode(message):
    sent = bot.send_message(message.chat.id, "Chọn loại:\n1. Tiền\n2. Key VIP", reply_markup=kb_admin_cancel())
    bot.register_next_step_handler(sent, admin_create_giftcode_step2)

def admin_create_giftcode_step2(message):
    if message.text == "🏠 Quay Lại Admin":
        back_admin(message)
        return
    if message.text == "1":
        g_type = "money"
        sent = bot.send_message(message.chat.id, "Nhập số tiền thưởng:", reply_markup=kb_admin_cancel())
        bot.register_next_step_handler(sent, admin_create_giftcode_step3, g_type)
    elif message.text == "2":
        g_type = "key"
        sent = bot.send_message(message.chat.id, "Nhập số ngày VIP:", reply_markup=kb_admin_cancel())
        bot.register_next_step_handler(sent, admin_create_giftcode_step3, g_type)
    else:
        bot.send_message(message.chat.id, "❌ Lựa chọn không hợp lệ!", reply_markup=kb_admin_giftcode())
        return

def admin_create_giftcode_step3(message, g_type):
    if message.text == "🏠 Quay Lại Admin":
        back_admin(message)
        return
    try:
        value = int(message.text)
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        db["giftcodes"][code] = {"type": g_type, "value": value, "usages": 1, "used_by": []}
        save_db(db)
        bot.send_message(message.chat.id, f"✅ Tạo code thành công!\n🎟 Mã: <code>{code}</code>\n💎 Loại: {'Tiền' if g_type == 'money' else 'Key VIP'}\n📦 Giá trị: {value:,} {'VNĐ' if g_type == 'money' else 'ngày'}", reply_markup=kb_admin_giftcode(), parse_mode='HTML')
    except:
        bot.send_message(message.chat.id, "❌ Giá trị không hợp lệ!", reply_markup=kb_admin_giftcode())

@bot.message_handler(func=lambda msg: msg.text == "➖ Xóa Code" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_delete_giftcode(message):
    sent = bot.send_message(message.chat.id, "Nhập mã giftcode cần xóa:", reply_markup=kb_admin_cancel())
    bot.register_next_step_handler(sent, admin_delete_giftcode_step2)

def admin_delete_giftcode_step2(message):
    if message.text == "🏠 Quay Lại Admin":
        back_admin(message)
        return
    code = message.text.strip().upper()
    if code in db["giftcodes"]:
        del db["giftcodes"][code]
        save_db(db)
        bot.send_message(message.chat.id, f"✅ Đã xóa mã {code}", reply_markup=kb_admin_giftcode())
    else:
        bot.send_message(message.chat.id, "❌ Mã không tồn tại!", reply_markup=kb_admin_giftcode())

@bot.message_handler(func=lambda msg: msg.text == "📋 DS Code" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_list_giftcode(message):
    if not db["giftcodes"]:
        bot.send_message(message.chat.id, "📋 Chưa có giftcode nào.", reply_markup=kb_admin_giftcode())
        return
    msg = "📋 <b>DANH SÁCH GIFTCODE</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    for code, info in db["giftcodes"].items():
        type_txt = "💰 Tiền" if info["type"] == "money" else "🔑 Key VIP"
        msg += f"🎟 <code>{code}</code> - {type_txt} {info['value']:,} {'VNĐ' if info['type'] == 'money' else 'ngày'} - Còn {info.get('usages',1)} lượt\n"
    bot.send_message(message.chat.id, msg, reply_markup=kb_admin_giftcode())

@bot.message_handler(func=lambda msg: msg.text == "✅ Duyệt Nạp" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_pending_deposits(message):
    if not db["pending_deposits"]:
        bot.send_message(message.chat.id, "📭 Không có giao dịch chờ duyệt.", reply_markup=kb_admin())
        return
    for tid, info in db["pending_deposits"].items():
        admin_caption = f"🔔 <b>YÊU CẦU NẠP TIỀN</b>\n"
        admin_caption += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        admin_caption += f"👤 User: @{info['username']}\n"
        admin_caption += f"🆔 ID: <code>{info['uid']}</code>\n"
        admin_caption += f"💰 Số tiền: <b>{info['amount']:,} VNĐ</b>\n"
        admin_caption += f"📝 Nội dung: <code>{info['content']}</code>"
        inline_markup = InlineKeyboardMarkup()
        inline_markup.row(
            InlineKeyboardButton("✅ Duyệt", callback_data=f"approve_{tid}"),
            InlineKeyboardButton("❌ Từ chối", callback_data=f"reject_{tid}")
        )
        bot.send_photo(ADMIN_ID, info['photo_id'], caption=admin_caption, reply_markup=inline_markup)
    bot.send_message(message.chat.id, "✅ Đã gửi lại tất cả giao dịch chờ duyệt.", reply_markup=kb_admin())

@bot.message_handler(func=lambda msg: msg.text == "👥 Users" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_list_users(message):
    total_users = len(db["users"])
    active_keys = sum(1 for u in db["users"].values() if u.get("key_expiry") and datetime.fromisoformat(u["key_expiry"]) > datetime.now())
    msg = f"👥 <b>THỐNG KÊ USER</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    msg += f"📊 Tổng số user: {total_users}\n"
    msg += f"🔑 VIP đang hoạt động: {active_keys}\n"
    bot.send_message(message.chat.id, msg, reply_markup=kb_admin())

@bot.message_handler(func=lambda msg: msg.text == "📢 Thông báo" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_broadcast(message):
    sent = bot.send_message(message.chat.id, "✍️ Nhập nội dung thông báo:", reply_markup=kb_admin_cancel())
    bot.register_next_step_handler(sent, admin_broadcast_send)

def admin_broadcast_send(message):
    if message.text == "🏠 Quay Lại Admin":
        back_admin(message)
        return
    content = message.text
    success = 0
    fail = 0
    for uid in db["users"]:
        try:
            bot.send_message(uid, f"📢 <b>THÔNG BÁO TỪ ADMIN</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n{content}")
            success += 1
        except:
            fail += 1
    bot.send_message(message.chat.id, f"✅ Đã gửi thành công đến {success} user.\n❌ Không gửi được {fail} user.", reply_markup=kb_admin())

@bot.message_handler(func=lambda msg: msg.text == "📩 Nhắn tin" and str(msg.from_user.id) == str(ADMIN_ID))
def admin_private_message(message):
    sent = bot.send_message(message.chat.id, "Nhập ID hoặc @username người nhận:", reply_markup=kb_admin_cancel())
    bot.register_next_step_handler(sent, admin_private_message_step2)

def admin_private_message_step2(message):
    if message.text == "🏠 Quay Lại Admin":
        back_admin(message)
        return
    target = resolve_user(message.text)
    if not target:
        bot.send_message(message.chat.id, "❌ Không tìm thấy user!", reply_markup=kb_admin())
        return
    sent = bot.send_message(message.chat.id, "Nhập nội dung tin nhắn:", reply_markup=kb_admin_cancel())
    bot.register_next_step_handler(sent, admin_private_message_step3, target)

def admin_private_message_step3(message, target):
    if message.text == "🏠 Quay Lại Admin":
        back_admin(message)
        return
    try:
        bot.send_message(target, f"📩 <b>TIN NHẮN TỪ ADMIN</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n{message.text}")
        bot.send_message(message.chat.id, f"✅ Đã gửi tin nhắn đến user {target}", reply_markup=kb_admin())
    except:
        bot.send_message(message.chat.id, f"❌ Gửi thất bại! User có thể đã chặn bot.", reply_markup=kb_admin())

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    print("✅ Bot đang hoạt động...")

    # Chạy web server cho Render
    threading.Thread(target=run_web, daemon=True).start()

    # Chạy bot Telegram
    bot.infinity_polling(skip_pending=True)
