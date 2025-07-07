import logging
import random
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime
import razorpay
from twilio.rest import Client

# === CONFIGURATION ===
API_TOKEN = "7624030034:AAGDh8KGZgMaZfIaC82QAodoKsftNJi2_-8"
ADMIN_ID = 7289622549
RAZORPAY_KEY_ID = "rzp_live_SoweuPU2b0UJDl"
RAZORPAY_KEY_SECRET = "7typeA29UPiN7CU9ApeI5tfg"
TWILIO_ACCOUNT_SID = "AC5c5e5daaa0b0d7aece6808a60781bb81"
TWILIO_AUTH_TOKEN = "c10b0e4b90b96184e54a068170a673b8"
TWILIO_PHONE_NUMBER = "+15674062449"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

user_data = {}
pending_approval = {}
awaiting_decline_reason_for = None

# === ADMIN KEYBOARD ===
def get_admin_inline_keyboard(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✅ Accept", callback_data=f"accept:{user_id}"),
         InlineKeyboardButton("❌ Decline", callback_data=f"decline:{user_id}")]
    ])

# === PDF INVOICE GENERATION ===
def generate_invoice_pdf(order, invoice_number):
    file_path = f"invoice_{invoice_number}.pdf"
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4

    try:
        c.drawImage("logo.jpg", 50, height - 100, width=100, preserveAspectRatio=True, mask='auto')
    except:
        pass

    c.setFont("Helvetica-Bold", 20)
    c.drawString(160, height - 50, "KarmaGully Poster Invoice")
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 120, f"Invoice No: {invoice_number}")
    c.drawString(50, height - 140, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    y = height - 180
    fields = [
        ("Name", order["name"]),
        ("Poster Size", order["size"]),
        ("Price", f"₹{order['price']}"),
        ("Address", order["address"]),
        ("Pincode", order["pincode"]),
        ("State", order["state"]),
        ("Country", order["country"]),
        ("Mobile", order["mobile"]),
        ("Email", order["email"]),
        ("Status", "Confirmed"),
    ]
    for label, value in fields:
        c.drawString(50, y, f"{label}: {value}")
        y -= 20

    y -= 20
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Thank you for purchasing from KarmaGully!")
    c.setFont("Helvetica", 12)
    y -= 20
    c.drawString(50, y, "If you liked the product, please leave a review on karmagully.in")
    y -= 20
    c.drawString(50, y, "Follow us:")
    c.drawString(70, y - 20, "Instagram: https://instagram.com/karmagully/")
    c.drawString(70, y - 40, "Facebook: https://facebook.com/share/171drG6tr4/")
    c.drawString(70, y - 60, "YouTube: https://youtube.com/@karmagully")
    c.drawString(70, y - 80, "Telegram: https://t.me/karmagully")
    c.save()
    return file_path

# === START ===
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id] = {'step': 'awaiting_design'}
    await message.reply("👋 Welcome to *KarmaGully Custom Poster Bot!*\n\nPlease upload your *design image* for the metal poster.", parse_mode="Markdown")

# === PHOTO HANDLER ===
@dp.message_handler(content_types=types.ContentType.PHOTO)
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    step = user_data.get(user_id, {}).get('step')
    if step == 'awaiting_design':
        user_data[user_id]['photo'] = message.photo[-1].file_id
        user_data[user_id]['step'] = 'awaiting_size'
        await message.reply("📏 Choose your *poster size*:\n1️⃣ 8x11.7 inches\n2️⃣ 11.7x15.7 inches\n\nType 1 or 2.", parse_mode="Markdown")

    elif step == 'awaiting_payment_screenshot':
        user_data[user_id]['payment'] = message.photo[-1].file_id
        user_data[user_id]['step'] = 'under_review'
        data = user_data[user_id]
        pending_approval[str(user_id)] = data

        await message.reply("✅ *Payment screenshot received!*\nYour order is now being reviewed.", parse_mode="Markdown")
        await bot.send_photo(ADMIN_ID, data['photo'], caption="🖼 Design Image")
        await bot.send_photo(ADMIN_ID, data['payment'], caption="💳 Payment Screenshot")
        await bot.send_message(ADMIN_ID,
            f"🚚 *New Order!*\n\n"
            f"👤 Name: {data['name']}\n"
            f"📏 Size: {data['size']}\n"
            f"💰 Price: ₹{data['price']}\n"
            f"📞 Mobile: {data['mobile']}\n"
            f"🏠 Address: {data['address']}\n"
            f"📮 Pincode: {data['pincode']}\n"
            f"🌍 State: {data['state']}\n"
            f"🌐 Country: {data['country']}\n"
            f"📧 Email: {data['email']}\n"
            f"🆔 Telegram ID: {user_id}",
            parse_mode="Markdown",
            reply_markup=get_admin_inline_keyboard(user_id))

# === SIZE SELECTION ===
@dp.message_handler(lambda m: m.text in ['1', '2'])
async def handle_size(m: types.Message):
    user_id = m.from_user.id
    step = user_data.get(user_id, {}).get('step')
    if step != 'awaiting_size': return
    size = '8x11.7 inches' if m.text == '1' else '11.7x15.7 inches'
    price = 659 if m.text == '1' else 899
    user_data[user_id].update({'size': size, 'price': price, 'step': 'awaiting_name'})
    await m.reply(f"✅ Poster size selected: *{size}*\n💰 Price: ₹{price}\n\nEnter your *Full Name*:", parse_mode="Markdown")

# === TEXT INPUT HANDLER ===
@dp.message_handler()
async def handle_text(m: types.Message):
    global awaiting_decline_reason_for
    user_id = m.from_user.id
    text = m.text
    step = user_data.get(user_id, {}).get('step')

    if m.from_user.id == ADMIN_ID and awaiting_decline_reason_for:
        declined_uid = awaiting_decline_reason_for
        awaiting_decline_reason_for = None
        await bot.send_message(declined_uid, f"❌ *Your order was declined.*\nReason: {text}", parse_mode="Markdown")
        pending_approval.pop(str(declined_uid), None)
        await m.reply("✅ Reason sent to customer.")
        return

    fields = [
        ('awaiting_name', 'name', "📞 Enter your *Mobile Number*:"),
        ('awaiting_mobile', 'mobile', "🏠 Enter your *Full Address*:"),
        ('awaiting_address', 'address', "📮 Enter your *Pincode*:"),
        ('awaiting_pincode', 'pincode', "🌍 Enter your *State*:"),
        ('awaiting_state', 'state', "🌐 Enter your *Country*:"),
        ('awaiting_country', 'country', "📧 Enter your *Email Address*:")
    ]

    for current_step, key, next_msg in fields:
        if step == current_step:
            user_data[user_id][key] = text
            if current_step == 'awaiting_country':
                user_data[user_id]['step'] = 'awaiting_email'
            else:
                user_data[user_id]['step'] = fields[fields.index((current_step, key, next_msg)) + 1][0]
            await m.reply(next_msg, parse_mode="Markdown")
            return

    if step == 'awaiting_email':
        user_data[user_id]['email'] = text
        user_data[user_id]['step'] = 'awaiting_payment_screenshot'
        name = user_data[user_id]['name']
        email = user_data[user_id]['email']
        mobile = user_data[user_id]['mobile']
        price = user_data[user_id]['price']
        try:
            payment_link = razorpay_client.payment_link.create({
                "amount": price * 100,
                "currency": "INR",
                "accept_partial": False,
                "description": f"Custom Poster Order - {name}",
                "customer": {
                    "name": name,
                    "email": email,
                    "contact": mobile
                },
                "notify": {
                    "sms": True,
                    "email": True
                },
                "reminder_enable": True
            })

            await m.reply(
                f"💳 Please *pay ₹{price}* using the link below:\n{payment_link['short_url']}\n\n"
                "After payment, *send the payment screenshot* here.",
                parse_mode="Markdown")
        except Exception as e:
            await m.reply("⚠️ Failed to generate payment link. Please try again later.")
            print(f"[Razorpay Error] {e}")
    elif step == 'under_review':
        await m.reply("🕵️‍♂️ Your order is under review by the admin. Please wait.")
    else:
        await m.reply("❗ Please follow the instructions or type /start to begin again.")

# === ADMIN DECISION HANDLER ===
@dp.callback_query_handler(lambda c: c.data.startswith("accept") or c.data.startswith("decline"))
async def handle_admin_decision(callback_query: types.CallbackQuery):
    global awaiting_decline_reason_for
    data = callback_query.data
    admin_id = callback_query.from_user.id

    if admin_id != ADMIN_ID:
        await callback_query.answer("You're not authorized.", show_alert=True)
        return

    action, user_id = data.split(":")
    user_id = int(user_id)
    if str(user_id) not in pending_approval:
        await callback_query.answer("Order already processed.", show_alert=True)
        return

    order = pending_approval.pop(str(user_id))

    if action == "accept":
        invoice_number = f"INV{random.randint(100000,999999)}"
        pdf_path = generate_invoice_pdf(order, invoice_number)

        await bot.send_message(user_id, "🎉 *Your order has been accepted!* We'll start processing it.", parse_mode="Markdown")
        await bot.send_document(user_id, open(pdf_path, "rb"), caption=f"💾 *Invoice*: {invoice_number}", parse_mode="Markdown")
        await bot.send_document(ADMIN_ID, open(pdf_path, "rb"), caption=f"📄 *Invoice for {order['name']}*", parse_mode="Markdown")

        try:
            message = twilio_client.messages.create(
                body=f"Hi {order['name']}, your KarmaGully order has been confirmed! Invoice: {invoice_number}. Thank you!",
                from_=TWILIO_PHONE_NUMBER,
                to="+91" + order['mobile']
            )
            print("SMS sent:", message.sid)
        except Exception as e:
            print("SMS Error:", e)

        os.remove(pdf_path)

    elif action == "decline":
        awaiting_decline_reason_for = user_id
        await bot.send_message(ADMIN_ID, "✏️ Please enter the reason for declining this order.")

# === RUN BOT ===
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
