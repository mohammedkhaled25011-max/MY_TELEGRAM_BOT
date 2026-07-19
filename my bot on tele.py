import os
import asyncio
import random
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError

# ====== إعدادات البوت والـ API (تعدلها حسب معلوماتك) ======
API_ID = 37749928
API_HASH = "c1731ed103dfe4ed1d8458f1cfce422a"
BOT_TOKEN = "8961257926:AAFuqfcyuAV0rFnH-xo5G2xWmPcA02vftcc"

# اسم الملف النصي لحفظ الجلسات
SESSIONS_FILE = "sessions.txt"

# مراحل حوار الربط
GET_PHONE, GET_CODE, GET_PASSWORD = range(3)

# مصفوفة الكلمات مالت السبام الخاصة بك
spam_messages = [ 
    "يا ابن الضايعه يا اخو المنيوكه ي ابن الزق",
    "يا ابن المنيوكه ي ابن المعرسه ي دلخ",
    "شرايك تاكل زقان امك و تسمع يا ابن الشرموطه",
    "انا بحط جزمتي ف طيز امك ي ابن الخرا ي مسكين ي ابن المومسه",
    "الله يحرق رحم امك ي ابن الخرا ي ابن الضايعه ي اخو القحبه ي ورع الشرموطه تفو على امك",
    "تفو على خرق امك ي ابن المسكينه بلطش امك كفوف ي ابن الخرا ي مديث لعن الله رحم امك الخرا",
    "طيب وجه امك مثير للشفقه ي ابن القحبه ي مسكين ي اخو الشرموطه كس أم امك ي ابن الخرا ي ابن الضايعه",
    "بخصوص دعست وجه امك ي ابن الخرا وانت للحين ساكت يلعن طيز ام امك بس ي ابن الخرا ي مسكين",
    "بنحر رقبه امك ي ابن الخرا امام انظارك ي مديث ي ورع القحبه كس ام امك بجزمتي ي ابن الزقان كس اختك بس",
    "ترا بنيك كس ام امك ي ابن الخرا لا تسولف يلعن كس ام امك ي ابن الخرا ي مسكين ي ولد العاهره ي ابن الافريقيه يععع",
    "الله يلعن رحم امك ي ابن المسكين بفجر ف طيز امك ي ابن الخرا ي ابن الهايشه ي ابن المومسه تفوو على الي رباك ي مسكين",
    "طيب ترا صفقت كس ام امك ي ابن الزنا ي مسكين ليه ما ترد الله يلعن امك بس ي ابن الخرا",
    "يا كلب يا ابن الزانيه صفعت امك يعني كس اختك ي ابن الخرا",
    "ب اصفق كس ام امك صحصح يلعن امك",
    "يا مسكين يا ابن العاهره ي ابن الافريقيه كس ام امك",
    "يا حمار يابن المنيوكه كس امك يا مهان يا ابن المصخرة انيك امك يا جرار",
    "وش فيك يابن المنيوكه أنت كس امك و ي مصخره ي ابن الحيوانه",
    "الو ي اخو الشرموطه وش رأي امك ترد علي الحين ي قواد يابن العاهر ي ديوث",
    "انت تبيني انيك امك وادعسها ي ابن القحبه سامع كس امك ياكس صدر امك",
    "ي ابن القحبه وشفيك ياديوث ياولد الضعيفه ي ابن القحبه ؟",
    "ديوث انت الله يلعن طيز امك بس ي مديث ي مسكين"
]

RUNNING_USERS = {}

# ====================================================
# أولاً: وظائف حفظ واسترجاع الجلسات من الملف النصي
# ====================================================

def save_session_to_file(user_id, session_str):
    if not is_user_saved(user_id):
        with open(SESSIONS_FILE, "a", encoding="utf-8") as f:
            f.write(f"{user_id}|||{session_str}\n")

def is_user_saved(user_id):
    if not os.path.exists(SESSIONS_FILE):
        return False
    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith(f"{user_id}|||"):
                return True
    return False

# ====================================================
# ثانياً: كود الـ Userbot والـ Workers المطور
# ====================================================

async def auto_messages_worker(owner_id):
    user_data = RUNNING_USERS.get(owner_id)
    if not user_data:
        return

    client = user_data['client']
    while user_data['enabled'] and user_data['target_chat']:
        try:
            if not client.is_connected():
                print(f"🔄 إعادة اتصال تلقائي للحساب المعلق: {owner_id}")
                await client.connect()

            current_speed = user_data.get('speed', 0.1)
            
            # إذا اكو ريبلاي يرد على رسالة الضحية، وإذا ماكو يرسل عام
            if user_data['last_reply_id']:
                await client.send_message(user_data['target_chat'], random.choice(spam_messages),
                                          reply_to=user_data['last_reply_id'])
            else:
                await client.send_message(user_data['target_chat'], random.choice(spam_messages))
            
            await asyncio.sleep(current_speed)
        except Exception as e:
            print(f"Error sending spam for {owner_id}: {e}")
            await asyncio.sleep(0.5)

async def handle_user_messages(event, owner_id):
    user_data = RUNNING_USERS.get(owner_id)
    if not user_data:
        return

    sender_id = event.sender_id
    text = event.text.strip() if event.text else ""
    client = user_data['client']

    # 1. كود الكتم المستقل تماماً (يعتمد على muted_user المخصص له فقط)
    if user_data['delete_enabled'] and user_data['muted_user'] is not None and event.chat_id == user_data['target_chat']:
        if sender_id == user_data['muted_user']:
            try:
                if not client.is_connected():
                    await client.connect()
                await client.delete_messages(event.chat_id, event.id, revoke=True)
            except Exception as e:
                print(f"Error deleting: {e}")

    # 2. تحديث الـ last_reply_id للتسطير بالريبلاي إذا كان مستهدف شخص معين
    if user_data['enabled'] and event.chat_id == user_data['target_chat'] and user_data['target_user'] is not None:
        if sender_id == user_data['target_user']:
            user_data['last_reply_id'] = event.id

    if event.out or sender_id == owner_id:
        if text == "بنيك امك":
            user_data['target_chat'] = event.chat_id
            user_data['enabled'] = True
            
            # فحص إذا چان الأمر مرسل بريبلاي أو شات عام
            if event.is_reply:
                replied = await event.get_reply_message()
                user_data['target_user'] = replied.sender_id
                user_data['last_reply_id'] = replied.id
            else:
                # شات عام بدون استهداف شخص محدد بالردود، وما يأثر ع الكتم
                user_data['target_user'] = None
                user_data['last_reply_id'] = None

            if user_data['task'] is not None:
                user_data['task'].cancel()
            user_data['task'] = asyncio.create_task(auto_messages_worker(owner_id))

        elif text.startswith("s ") or text.startswith("س "):
            parts = text.split()
            if len(parts) > 1:
                try:
                    new_speed = float(parts[1])
                    if new_speed < 0.02:
                        new_speed = 0.02  
                    elif new_speed > 60.0:
                        new_speed = 60.0  
                    
                    user_data['speed'] = new_speed
                    print(f"⚡ تم تحديث السرعة لـ {owner_id} إلى: {new_speed} ثانية")
                except ValueError:
                    pass
            await event.delete()

        # إيقاف التسطير فقط بدون تصفير أو لمس إعدادات الكتم
        elif text == "صفقت امك":
            user_data['enabled'] = False
            if user_data['task']:
                user_data['task'].cancel()
                user_data['task'] = None

        # تفعيل الكتم المستقل على متغير منفصل
        elif text == "بنعالي":
            if not event.is_reply:
                return
            replied = await event.get_reply_message()
            user_data['muted_user'] = replied.sender_id
            user_data['target_chat'] = event.chat_id
            user_data['delete_enabled'] = True

        # إلغاء الكتم المستقل
        elif text == "تكلم":
            user_data['delete_enabled'] = False
            user_data['muted_user'] = None

def setup_userbot_events(client, owner_id):
    client.add_event_handler(
        lambda event: handle_user_messages(event, owner_id),
        events.NewMessage
    )

# ====================================================
# ثالثاً: كود البوت الرسمي مع تصفير حوار التسجيل فقط
# ====================================================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('phone', None)
    context.user_data.pop('phone_code_hash', None)
    context.user_data.pop('temp_client', None)

    chat_id = update.message.chat_id

    if is_user_saved(chat_id):
        await update.message.reply_text("✅ حسابك مفعّل ومربوط مسبقاً بالخلفية! يمكنك استخدام أوامرك مباشرة.")
        return ConversationHandler.END

    await update.message.reply_text(
        "أهلاً بك في سورس دانا\n\n"
        "يرجى إرسال رقم هاتفك لتفعيل السورس على حسابك (مع رمز الدولة)\n"
        "مثال: `+9665XXXXXXXX`"
    )
    return GET_PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    if phone.startswith('/'):
        return await handle_interruption(update, context)

    context.user_data['phone'] = phone
    await update.message.reply_text("⏳ جاري الاتصال وإرسال كود التحقق...")

    client = TelegramClient(StringSession(), API_ID, API_HASH)
    await client.connect()
    context.user_data['temp_client'] = client

    try:
        send_code_req = await client.send_code_request(phone)
        context.user_data['phone_code_hash'] = send_code_req.phone_code_hash
        await update.message.reply_text("✅ تم إرسال كود التحقق. يرجى تزويدي بالكود:")
        return GET_CODE
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ أثناء إرسال الكود:\n`{e}`\n\nأعد إرسال الرقم بشكل صحيح أو اكتب إلغاء للبدء من جديد:")
        return GET_PHONE

async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().replace(" ", "")
    if code.startswith('/'):
        return await handle_interruption(update, context)

    chat_id = update.message.chat_id
    client = context.user_data.get('temp_client')
    phone = context.user_data.get('phone')
    phone_code_hash = context.user_data.get('phone_code_hash')

    if not client:
        await update.message.reply_text("❌ حدث خطأ في الجلسة، يرجى إعادة إرسال /start من جديد.")
        return ConversationHandler.END

    try:
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        me = await client.get_me()
        await finalize_userbot_login(chat_id, me.id, client, update)
        return ConversationHandler.END
    except SessionPasswordNeededError:
        await update.message.reply_text("🔐 حسابك محمي بالتحقق بخطوتين.\nيرجى إرسال الباسورد الخاص بحسابك:")
        return GET_PASSWORD
    except Exception as e:
        await update.message.reply_text(f"❌ الكود غير صحيح أو منتهي الصلاحية. أعد إرساله (أو أرسل الغاء للبدء من جديد):")
        return GET_CODE

async def get_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    if password.startswith('/'):
        return await handle_interruption(update, context)

    chat_id = update.message.chat_id
    client = context.user_data.get('temp_client')

    if not client:
        await update.message.reply_text("❌ حدث خطأ في الجلسة، يرجى إعادة إرسال /start من جديد.")
        return ConversationHandler.END

    try:
        await client.sign_in(password=password)
        me = await client.get_me()
        await finalize_userbot_login(chat_id, me.id, client, update)
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text("❌ الباسورد غير صحيح. أعد إرسال الباسورد المظبوط:")
        return GET_PASSWORD

async def handle_interruption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == '/start':
        return await start_command(update, context)
    else:
        return await cancel(update, context)

async def finalize_userbot_login(chat_id, real_user_id, client, update):
    session_str = client.session.save()
    save_session_to_file(real_user_id, session_str)

    RUNNING_USERS[real_user_id] = {
        'client': client,
        'enabled': False,
        'delete_enabled': False,
        'target_user': None,
        'muted_user': None,  # المتغير الجديد المنفصل للكتم
        'target_chat': None,
        'last_reply_id': None,
        'speed': 0.1,  
        'task': None
    }

    setup_userbot_events(client, real_user_id)
    asyncio.create_task(client.run_until_disconnected())

    await update.message.reply_text("🔥 مبروك! تم ربط حسابك وتفعيل سورس دانا بنجاح.\n\n"
                                    "📜 قائمة التعليمات والأوامر الخاصة بك الحين:\n"
                                    "━━━━━━━━━━━━━━━━━━\n"
                                    "[أوامر التسطير ]:\n"
                                    "🔹 سوّي ريبلاي على الضحية ويمديك بدون ريبلاي واكتب: `بنيك امك` (يبدأ التسطير التلقائي بسرعته الأساسية 0.1 ثانية).\n"
                                    "🔹 لإيقاف التسطير بأي وقت اكتب: `صفقت امك`.\n\n"

                                    "[أوامر التحكم بالسرعة]:\n"
                                    "🔹 اكتب الأمر `s` أو `س` ومعه رقم الثواني لتغيير السرعة مباشرة بدون ريبلاي.\n"
                                    "   • مثال للطيران: `s 0.02` (أقل حد مسموح به للسرعة).\n"
                                    "   • مثال للتهدئة: `s 60` (أعلى حد مسموح به لتبطئ الرسائل).\n\n"

                                    "[أوامر الكتم وحذف الرسائل]:\n"
                                    "🔹 سوّي ريبلاي على الضحية واكتب: `بنعالي` (أي رسالة يرسلها الضحية تنمسح فوراً وينكتم الشخص).\n"
                                    "🔹 لإلغاء الكتم والسماح له يسولف اكتب فالشات: `تكلم`.\n"
                                    "━━━━━━━━━━━━━━━━━━\n"
                                    "💡 ملاحظة: جميع أوامر السرعة والـ s تختفي فوراً من الشاشة تلقائياً بعد كتابتها حتى ما تخرب شكل الشات.")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("⚠️ تم إلغاء العملية وتصفير المعلق بالخلفية. ارسل /start للبدء من جديد.")
    return ConversationHandler.END

# ====================================================
# رابعاً: دالة إعادة تشغيل الحسابات تلقائياً وصائد الأخطاء لـ Railway
# ====================================================
async def load_saved_sessions():
    if not os.path.exists(SESSIONS_FILE):
        return

    print("🔄 جاري إعادة تشغيل الحسابات المحفوظة بالخلفية...")
    with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "|||" not in line:
                continue

            try:
                user_id_str, session_str = line.split("|||", 1)
                real_user_id = int(user_id_str)

                client = TelegramClient(StringSession(session_str), API_ID, API_HASH)
                await client.connect()

                if await client.is_user_authorized():
                    RUNNING_USERS[real_user_id] = {
                        'client': client,
                        'enabled': False,
                        'delete_enabled': False,
                        'target_user': None,
                        'muted_user': None,  # تصفير متغير الكتم المنفصل عند الإقلاع
                        'target_chat': None,
                        'last_reply_id': None,
                        'speed': 0.1,  
                        'task': None
                    }
                    setup_userbot_events(client, real_user_id)
                    asyncio.create_task(client.run_until_disconnected())
                    print(f"✅ تم إعادة تشغيل حساب المستخدم: {real_user_id}")
            except Exception as e:
                print(f"Error loading saved session: {e}")

async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"🚨 صائد الأخطاء لقط مشكلة: {context.error}")

# ====================================================
# خامساً: الـ Main وموقع الإقلاع الرئيسي
# ====================================================
if __name__ == '__main__':
    print("🚀 جاري تشغيل بوت تليجرام الخدمي المطور...")
    app = Application.builder().token(BOT_TOKEN).read_timeout(30).write_timeout(30).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            GET_PHONE: [CommandHandler("start", start_command), MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            GET_CODE: [CommandHandler("start", start_command), MessageHandler(filters.TEXT & ~filters.COMMAND, get_code)],
            GET_PASSWORD: [CommandHandler("start", start_command), MessageHandler(filters.TEXT & ~filters.COMMAND, get_password)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            MessageHandler(filters.Regex('^(الغاء|إلغاء|تصفير)$'), cancel)
        ],
        allow_reentry=True  
    )
    
    app.add_handler(conv_handler)
    app.add_error_handler(global_error_handler)

    async def on_startup(application: Application):
        await load_saved_sessions()

    app.post_init = on_startup
    app.run_polling()
