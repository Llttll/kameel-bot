#!/usr/bin/env python3
"""
بوت قسم الأمن - كميل
Security Department Telegram Bot
"""

import json
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
    ApplicationHandlerStop,
)

# ─── الإعدادات ────────────────────────────────────────────────────────────────
BOT_TOKEN = "8478999240:AAGHK7aSH2rz_3doNM6uJLStfXxRUWICe1c"   # ← ضع توكن البوت هنا
ADMINS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admins.json")
SERIAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "serial.json")

def get_next_serial() -> int:
    serial = 0
    if os.path.exists(SERIAL_FILE):
        try:
            with open(SERIAL_FILE, "r") as f:
                data = json.load(f)
                serial = data.get("last_serial", 0)
        except Exception:
            pass
    serial += 1
    try:
        with open(SERIAL_FILE, "w") as f:
            json.dump({"last_serial": serial}, f)
    except Exception as e:
        logger.error(f"Failed to save serial: {e}")
    return serial

def get_msg_content(msg) -> str:
    if msg.text:
        return msg.text
    elif msg.caption:
        return msg.caption
    elif msg.photo:
        return "صورة 🖼️"
    elif msg.voice:
        return "بصمة صوتية 🎤"
    elif msg.video:
        return "فيديو 🎬"
    elif msg.document:
        return "ملف 📄"
    elif msg.audio:
        return "مقطع صوتي 🎵"
    return "مرفق 📎"

# ─── إدارة الإدمنات (متعدد) ──────────────────────────────────────────────────
def load_admins() -> set:
    """تحميل قائمة الإدمنات من الملف."""
    if os.path.exists(ADMINS_FILE):
        try:
            with open(ADMINS_FILE, "r") as f:
                return set(json.load(f))
        except (json.JSONDecodeError, TypeError):
            pass
    return set()

def save_admins(admins: set):
    """حفظ قائمة الإدمنات إلى الملف."""
    with open(ADMINS_FILE, "w") as f:
        json.dump(list(admins), f)

def is_admin(user_id: int) -> bool:
    """التحقق هل المستخدم إدمن."""
    return user_id in load_admins()

# الإدمن الأصلي (الرئيسي) — لا يمكن حذفه
MASTER_ADMIN_ID = 1029158230

# تأكد من وجود الإدمن الرئيسي في الملف عند بدء التشغيل
def init_admins():
    admins = load_admins()
    if MASTER_ADMIN_ID not in admins:
        admins.add(MASTER_ADMIN_ID)
        save_admins(admins)

# ─── تتبع الرسائل للرد ──────────────────────────────────────────────────────
# قاموس: { (admin_chat_id, admin_msg_id): (user_chat_id, serial) }
# يربط رسالة الإشعار المُرسلة للإدمن بمعرّف المستخدم الأصلي ورقم الطلب
message_to_user_map: dict[tuple[int, int], tuple[int, int|None]] = {}

# ─── تتبع المحادثات المباشرة ─────────────────────────────────────────────────
# قاموس: { user_chat_id: serial_number } — المستخدمون الذين هم حالياً في محادثة مباشرة
active_chats: dict[int, int|bool] = {}

# مرجع للـ ConversationHandler لتغيير حالة المستخدم برمجياً
conv_handler: ConversationHandler | None = None

# ─── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── حالات المحادثة ──────────────────────────────────────────────────────────
(
    MAIN_MENU,
    # نموذج الباج
    BADGE_NAME, BADGE_MIL_NUM, BADGE_UNIT, BADGE_PROBLEM,
    # قائمة التخويل
    VEHICLE_AUTH_MENU,
    # نموذج التخويل
    VA_NAME, VA_MIL_NUM, VA_UNIT, VA_NOTES,
    # نموذج البرقيات
    TG_NAME, TG_VEH_TYPE, TG_COLOR, TG_FROM_TO, TG_DATE,
    # مقترح / مشكلة
    SUGGESTION,
) = range(16)

# ─── النصوص الثابتة ──────────────────────────────────────────────────────────
WELCOME = (
    "🔐 *السلام عليكم ورحمة الله وبركاته*\n\n"
    "مرحبا، أنا *كميل* أحد أفراد قسم الأمن\n"
    "أسعى لخدمتكم، تفضل بكل سرور 🫡\n\n"
    "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    "🏛️ *مرحبا بك في قسم (الأمن)*\n\n"
    "اختر ما تريد لخدمتك بسهولة مطلقة\n\n"
    "في حال لديك مشكلة اضغط :\n\n"
    "1️⃣  الباج (الهوية)\n"
    "2️⃣  التخويل الخاص بالعجلات\n"
    "3️⃣  البرقيات\n"
    "4️⃣  لديك مقترح أو مشكلة"
)

DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━"

# ─── لوحات المفاتيح ───────────────────────────────────────────────────────────
def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1️⃣  الباج (الهوية)", callback_data="badge")],
        [InlineKeyboardButton("2️⃣  التخويل الخاص بالعجلات", callback_data="vauth")],
        [InlineKeyboardButton("3️⃣  البرقيات", callback_data="telegram")],
        [InlineKeyboardButton("4️⃣  مقترح أو مشكلة", callback_data="suggest")],
    ])

def kb_back():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="home")]
    ])

def kb_end_chat():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔚 إنهاء المحادثة", callback_data="end_chat")]
    ])

def kb_vauth():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄  تجديد",          callback_data="va_تجديد")],
        [InlineKeyboardButton("📋  إصدار",           callback_data="va_إصدار")],
        [InlineKeyboardButton("✏️  تغيير الأسماء",   callback_data="va_تغيير_الأسماء")],
        [InlineKeyboardButton("❓  لديك مشكلة أخرى", callback_data="va_مشكلة_أخرى")],
        [InlineKeyboardButton("🔙  رجوع",            callback_data="home")],
    ])

# ─── مساعد: إرسال أو تعديل رسالة ────────────────────────────────────────────
async def send_or_edit(update: Update, text: str, markup=None):
    """يعمل سواء كان الاستدعاء من callback أو من رسالة نصية."""
    if update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=markup, parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text, reply_markup=markup, parse_mode="Markdown"
        )

# ─── مساعد: إشعار جميع الإدمنات ──────────────────────────────────────────────
async def notify_admins(context: ContextTypes.DEFAULT_TYPE, user, text: str, forward_msg_ids: list = None, serial: int = None):
    """إرسال إشعار لجميع الإدمنات وتتبع الرسائل للرد."""
    admins = load_admins()
    if not admins:
        return
    mention = f"@{user.username}" if user.username else user.first_name
    serial_text = f" [طلب #{serial}]" if serial else ""
    msg = (
        f"🔔 *طلب جديد*{serial_text} من {mention} (ID: `{user.id}`)\n\n"
        f"{text}\n\n"
        f"💬 _للرد على المستخدم، قم بالرد على هذه الرسالة (Reply)_"
    )
    for admin_id in admins:
        try:
            sent = await context.bot.send_message(
                chat_id=admin_id, text=msg, parse_mode="Markdown"
            )
            # تخزين الربط: رسالة الإشعار ← المستخدم الأصلي
            message_to_user_map[(admin_id, sent.message_id)] = (user.id, serial)
            
            # إرسال المرفقات إن وجدت
            if forward_msg_ids:
                for f_msg_id in forward_msg_ids:
                    try:
                        sent_fwd = await context.bot.copy_message(
                            chat_id=admin_id,
                            from_chat_id=user.id,
                            message_id=f_msg_id
                        )
                        message_to_user_map[(admin_id, sent_fwd.message_id)] = (user.id, serial)
                    except Exception as e:
                        logger.error(f"Failed to copy media msg {f_msg_id} to {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Admin notify failed for {admin_id}: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# شاشة البداية
# ═══════════════════════════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # إزالة المستخدم من المحادثات المباشرة عند العودة للقائمة
    user_id = update.effective_user.id
    if user_id in active_chats:
        del active_chats[user_id]
    context.user_data.clear()
    await send_or_edit(update, WELCOME, kb_main())
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════════════════════
# القائمة الرئيسية
# ═══════════════════════════════════════════════════════════════════════════════
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()

    context.user_data.pop("media_msgs", None)

    match q.data:
        case "badge":
            await q.edit_message_text(
                f"🪪 *الباج (الهوية)*\n{DIVIDER}\n\n"
                "*1️⃣  الاسم الثلاثي:*\nأرسل اسمك الثلاثي كاملاً 👇",
                parse_mode="Markdown",
            )
            return BADGE_NAME

        case "vauth":
            await q.edit_message_text(
                f"🚗 *(التخاويل)*\n{DIVIDER}\n\n"
                "اختر نوع الطلب:\n\n"
                "1️⃣  تجديد\n2️⃣  إصدار\n3️⃣  تغيير الأسماء\n4️⃣  لديك مشكلة أخرى",
                reply_markup=kb_vauth(),
                parse_mode="Markdown",
            )
            return VEHICLE_AUTH_MENU

        case "telegram":
            await q.edit_message_text(
                f"📨 *البرقيات*\n{DIVIDER}\n\n"
                "*1️⃣  بأمرة (الاسم الثلاثي):*\nأرسل الاسم الثلاثي 👇",
                parse_mode="Markdown",
            )
            return TG_NAME

        case "suggest":
            await q.edit_message_text(
                f"💡 *مقترح أو مشكلة*\n{DIVIDER}\n\n"
                "اكتب مقترحك أو مشكلتك وسيتم إيصالها للمسؤولين 👇",
                parse_mode="Markdown",
            )
            return SUGGESTION

        case "home" | _:
            return await start(update, context)

# ═══════════════════════════════════════════════════════════════════════════════
# نموذج الباج
# ═══════════════════════════════════════════════════════════════════════════════
async def badge_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["b_name"] = get_msg_content(update.message)
    if not update.message.text:
        context.user_data.setdefault("media_msgs", []).append(update.message.message_id)
    await update.message.reply_text(
        "✅ تم.\n\n*2️⃣  الرقم العسكري:*\nأرسل رقمك العسكري 👇",
        parse_mode="Markdown",
    )
    return BADGE_MIL_NUM

async def badge_mil_num(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["b_mil"] = get_msg_content(update.message)
    if not update.message.text:
        context.user_data.setdefault("media_msgs", []).append(update.message.message_id)
    await update.message.reply_text(
        "✅ تم.\n\n*3️⃣  الوحدة / الفوج / القسم:*\nأرسل اسم وحدتك 👇",
        parse_mode="Markdown",
    )
    return BADGE_UNIT

async def badge_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["b_unit"] = get_msg_content(update.message)
    if not update.message.text:
        context.user_data.setdefault("media_msgs", []).append(update.message.message_id)
    await update.message.reply_text(
        "✅ تم.\n\n*4️⃣  ما هية المشكلة؟*\nاشرح مشكلتك بالتفصيل 👇",
        parse_mode="Markdown",
    )
    return BADGE_PROBLEM

async def badge_problem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["b_prob"] = get_msg_content(update.message)
    if not update.message.text:
        context.user_data.setdefault("media_msgs", []).append(update.message.message_id)
    
    d = context.user_data
    serial = get_next_serial()

    summary = (
        f"✅ *تم استلام طلبك بنجاح!*\n"
        f"🔖 *رقم الطلب:* `#{serial}`\n\n"
        f"📋 *ملخص طلب الباج (الهوية):*\n{DIVIDER}\n"
        f"👤 الاسم الثلاثي : {d.get('b_name')}\n"
        f"🔢 الرقم العسكري : {d.get('b_mil')}\n"
        f"🏛️ الوحدة / الفوج : {d.get('b_unit')}\n"
        f"❗ المشكلة : {d.get('b_prob')}\n"
        f"{DIVIDER}\n📩 سيتم التواصل معك في أقرب وقت ممكن 🫡"
    )
    await update.message.reply_text(summary, reply_markup=kb_back(), parse_mode="Markdown")
    await notify_admins(context, update.effective_user, summary, d.get("media_msgs"), serial)
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════════════════════
# قائمة وشاشة التخويل
# ═══════════════════════════════════════════════════════════════════════════════
async def vauth_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()

    if q.data == "home":
        return await start(update, context)

    va_type = q.data.replace("va_", "").replace("_", " ")
    context.user_data["va_type"] = va_type

    await q.edit_message_text(
        f"🚗 *التخويل — {va_type}*\n{DIVIDER}\n\n"
        "*1️⃣  الاسم الثلاثي:*\nأرسل اسمك الثلاثي كاملاً 👇",
        parse_mode="Markdown",
    )
    return VA_NAME

async def va_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["va_name"] = get_msg_content(update.message)
    if not update.message.text:
        context.user_data.setdefault("media_msgs", []).append(update.message.message_id)
    await update.message.reply_text(
        "✅ تم.\n\n*2️⃣  الرقم العسكري:*\nأرسل رقمك العسكري 👇",
        parse_mode="Markdown",
    )
    return VA_MIL_NUM

async def va_mil_num(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["va_mil"] = get_msg_content(update.message)
    if not update.message.text:
        context.user_data.setdefault("media_msgs", []).append(update.message.message_id)
    await update.message.reply_text(
        "✅ تم.\n\n*3️⃣  الوحدة / الفوج / القسم:*\nأرسل اسم وحدتك 👇",
        parse_mode="Markdown",
    )
    return VA_UNIT

async def va_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["va_unit"] = get_msg_content(update.message)
    if not update.message.text:
        context.user_data.setdefault("media_msgs", []).append(update.message.message_id)
    await update.message.reply_text(
        "✅ تم.\n\n*4️⃣  ملاحظات إضافية / تفاصيل الطلب:*\nأضف أي تفاصيل 👇",
        parse_mode="Markdown",
    )
    return VA_NOTES

async def va_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["va_notes"] = get_msg_content(update.message)
    if not update.message.text:
        context.user_data.setdefault("media_msgs", []).append(update.message.message_id)
        
    d = context.user_data
    serial = get_next_serial()

    summary = (
        f"✅ *تم استلام طلبك بنجاح!*\n"
        f"🔖 *رقم الطلب:* `#{serial}`\n\n"
        f"🚗 *ملخص طلب التخويل:*\n{DIVIDER}\n"
        f"📌 نوع الطلب : {d.get('va_type')}\n"
        f"👤 الاسم الثلاثي : {d.get('va_name')}\n"
        f"🔢 الرقم العسكري : {d.get('va_mil')}\n"
        f"🏛️ الوحدة / الفوج : {d.get('va_unit')}\n"
        f"📝 الملاحظات : {d.get('va_notes')}\n"
        f"{DIVIDER}\n📩 سيتم التواصل معك في أقرب وقت ممكن 🫡"
    )
    await update.message.reply_text(summary, reply_markup=kb_back(), parse_mode="Markdown")
    await notify_admins(context, update.effective_user, summary, d.get("media_msgs"), serial)
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════════════════════
# نموذج البرقيات
# ═══════════════════════════════════════════════════════════════════════════════
async def tg_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["tg_name"] = get_msg_content(update.message)
    if not update.message.text:
        context.user_data.setdefault("media_msgs", []).append(update.message.message_id)
    await update.message.reply_text(
        "✅ تم.\n\n*2️⃣  نوع العجلة:*\nأرسل نوع العجلة 👇",
        parse_mode="Markdown",
    )
    return TG_VEH_TYPE

async def tg_veh_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["tg_veh"] = get_msg_content(update.message)
    if not update.message.text:
        context.user_data.setdefault("media_msgs", []).append(update.message.message_id)
    await update.message.reply_text(
        "✅ تم.\n\n*3️⃣  اللون والموديل:*\nأرسل لون وموديل العجلة 👇",
        parse_mode="Markdown",
    )
    return TG_COLOR

async def tg_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["tg_color"] = get_msg_content(update.message)
    if not update.message.text:
        context.user_data.setdefault("media_msgs", []).append(update.message.message_id)
    await update.message.reply_text(
        "✅ تم.\n\n*4️⃣  من وإلى:*\nأرسل الوجهة (من أين وإلى أين) 👇",
        parse_mode="Markdown",
    )
    return TG_FROM_TO

async def tg_from_to(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["tg_route"] = get_msg_content(update.message)
    if not update.message.text:
        context.user_data.setdefault("media_msgs", []).append(update.message.message_id)
    await update.message.reply_text(
        "✅ تم.\n\n*5️⃣  التاريخ:*\nأرسل تاريخ البرقية 👇",
        parse_mode="Markdown",
    )
    return TG_DATE

async def tg_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["tg_date"] = get_msg_content(update.message)
    if not update.message.text:
        context.user_data.setdefault("media_msgs", []).append(update.message.message_id)
        
    d = context.user_data
    serial = get_next_serial()

    summary = (
        f"✅ *تم استلام البرقية بنجاح!*\n"
        f"🔖 *رقم الطلب:* `#{serial}`\n\n"
        f"📨 *ملخص البرقية:*\n{DIVIDER}\n"
        f"👤 بأمرة (الاسم) : {d.get('tg_name')}\n"
        f"🚗 نوع العجلة : {d.get('tg_veh')}\n"
        f"🎨 اللون والموديل : {d.get('tg_color')}\n"
        f"📍 من وإلى : {d.get('tg_route')}\n"
        f"📅 التاريخ : {d.get('tg_date')}\n"
        f"{DIVIDER}\n📩 سيتم التواصل معك في أقرب وقت ممكن 🫡"
    )
    await update.message.reply_text(summary, reply_markup=kb_back(), parse_mode="Markdown")
    await notify_admins(context, update.effective_user, summary, d.get("media_msgs"), serial)
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════════════════════
# مقترح / مشكلة
# ═══════════════════════════════════════════════════════════════════════════════
async def suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = get_msg_content(update.message)
    media = [update.message.message_id] if not update.message.text else []
    serial = get_next_serial()
    
    await update.message.reply_text(
        f"✅ *شكراً لك!*\n\n"
        f"🔖 *رقم الطلب:* `#{serial}`\n"
        f"💡 تم استلام مقترحك/مشكلتك وسيتم إيصالها للمسؤولين.\n"
        f"{DIVIDER}\n📩 سيتم التواصل معك في أقرب وقت ممكن 🫡",
        reply_markup=kb_back(),
        parse_mode="Markdown",
    )
    await notify_admins(
        context,
        update.effective_user,
        f"💡 *مقترح / مشكلة:*\n{DIVIDER}\n{text}",
        media,
        serial
    )
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════════════════════
# زر العودة من أي حالة
# ═══════════════════════════════════════════════════════════════════════════════
async def go_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await start(update, context)

# ═══════════════════════════════════════════════════════════════════════════════
# المحادثة المباشرة — رسائل المستخدم للإدمن
# ═══════════════════════════════════════════════════════════════════════════════
async def live_chat_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    في وضع المحادثة المباشرة: يُرسل كل ما يكتبه المستخدم إلى جميع الإدمنات.
    """
    user = update.effective_user
    mention = f"@{user.username}" if user.username else user.first_name
    serial = active_chats.get(user.id)
    
    serial_text = f" [طلب #{serial}]" if isinstance(serial, int) else ""

    admin_text = (
        f"💬 *محادثة مباشرة{serial_text}* من {mention} (ID: `{user.id}`):\n"
        f"↩️ _للرد، قم بالرد على هذه الرسالة (Reply)_ | 🔚 _لإنهاء المحادثة: /end `{user.id}`_"
    )

    admins = load_admins()
    for admin_id in admins:
        try:
            sent_header = await context.bot.send_message(
                chat_id=admin_id, text=admin_text, parse_mode="Markdown"
            )
            sent_copy = await context.bot.copy_message(
                chat_id=admin_id,
                from_chat_id=user.id,
                message_id=update.message.message_id
            )
            # Both header and copy can be replied to by the admin
            message_to_user_map[(admin_id, sent_header.message_id)] = (user.id, serial if isinstance(serial, int) else None)
            message_to_user_map[(admin_id, sent_copy.message_id)] = (user.id, serial if isinstance(serial, int) else None)
        except Exception as e:
            logger.error(f"Live chat forward to admin {admin_id} failed: {e}")

async def intercept_live_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعترض رسائل المستخدم إذا كان في محادثة مباشرة."""
    if update.effective_user and update.effective_user.id in active_chats:
        await live_chat_user(update, context)
        raise ApplicationHandlerStop

async def end_chat_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عند ضغط المستخدم زر إنهاء المحادثة."""
    q = update.callback_query
    await q.answer()
    user_id = update.effective_user.id
    if user_id in active_chats:
        del active_chats[user_id]
    # إبلاغ الإدمنات
    admins = load_admins()
    mention = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
    for admin_id in admins:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=f"🔚 *{mention}* (ID: `{user_id}`) أنهى المحادثة المباشرة.",
                parse_mode="Markdown",
            )
        except Exception:
            pass
    
    await q.edit_message_text("🔚 *تم إنهاء المحادثة المباشرة.*", parse_mode="Markdown")
    raise ApplicationHandlerStop

async def cmd_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    أمر /end — يستخدمه المستخدم لإنهاء المحادثة المباشرة.
    أو الإدمن لإنهاء محادثة مستخدم معين: /end <user_id>
    """
    user_id = update.effective_user.id

    # إذا كان المرسل إدمن مع معرّف مستخدم
    if is_admin(user_id) and context.args:
        try:
            target_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ الرجاء إدخال رقم صحيح.")
            return

        if target_user_id in active_chats:
            del active_chats[target_user_id]
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=(
                        f"🔚 *تم إنهاء المحادثة المباشرة من قبل المسؤول.*\n\n"
                        f"شكراً لتواصلك معنا 🫡\n"
                        f"أرسل /start للعودة للقائمة الرئيسية."
                    ),
                    parse_mode="Markdown",
                )
            except Exception:
                pass
            await update.message.reply_text(
                f"✅ تم إنهاء المحادثة مع المستخدم `{target_user_id}`.",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(
                f"ℹ️ المستخدم `{target_user_id}` ليس في محادثة مباشرة حالياً.",
                parse_mode="Markdown",
            )
        return

    # إذا كان المرسل مستخدم عادي في محادثة مباشرة
    if user_id in active_chats:
        del active_chats[user_id]
        # إبلاغ الإدمنات
        admins = load_admins()
        mention = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name
        for admin_id in admins:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"🔚 *{mention}* (ID: `{user_id}`) أنهى المحادثة المباشرة.",
                    parse_mode="Markdown",
                )
            except Exception:
                pass
        await update.message.reply_text(
            "🔚 *تم إنهاء المحادثة المباشرة.*\n\n"
            "شكراً لتواصلك معنا 🫡\n"
            "أرسل /start للعودة للقائمة الرئيسية.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "ℹ️ لا توجد محادثة مباشرة حالياً.\n"
            "أرسل /start للعودة للقائمة الرئيسية.",
        )

# ═══════════════════════════════════════════════════════════════════════════════
# أوامر إدارة الإدمنات
# ═══════════════════════════════════════════════════════════════════════════════
async def cmd_addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إضافة إدمن جديد. الاستخدام: /addadmin <chat_id>"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ ليس لديك صلاحية لهذا الأمر.")
        return
    if not context.args:
        await update.message.reply_text(
            "❌ الاستخدام: `/addadmin <chat_id>`\n\n"
            "💡 يمكن للإدمن الجديد معرفة الـ chat\_id عن طريق إرسال `/myid` للبوت.",
            parse_mode="Markdown",
        )
        return
    try:
        new_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح.")
        return
    admins = load_admins()
    if new_id in admins:
        await update.message.reply_text(f"ℹ️ المستخدم `{new_id}` إدمن بالفعل.", parse_mode="Markdown")
        return
    admins.add(new_id)
    save_admins(admins)
    await update.message.reply_text(f"✅ تمت إضافة الإدمن `{new_id}` بنجاح.", parse_mode="Markdown")
    logger.info(f"Admin {user_id} added new admin {new_id}")

async def cmd_removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """حذف إدمن. الاستخدام: /removeadmin <chat_id>"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ ليس لديك صلاحية لهذا الأمر.")
        return
    if not context.args:
        await update.message.reply_text(
            "❌ الاستخدام: `/removeadmin <chat_id>`",
            parse_mode="Markdown",
        )
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ الرجاء إدخال رقم صحيح.")
        return
    if target_id == MASTER_ADMIN_ID:
        await update.message.reply_text("⛔ لا يمكن حذف الإدمن الرئيسي.")
        return
    admins = load_admins()
    if target_id not in admins:
        await update.message.reply_text(f"ℹ️ المستخدم `{target_id}` ليس إدمناً.", parse_mode="Markdown")
        return
    admins.discard(target_id)
    save_admins(admins)
    await update.message.reply_text(f"✅ تم حذف الإدمن `{target_id}` بنجاح.", parse_mode="Markdown")
    logger.info(f"Admin {user_id} removed admin {target_id}")

async def cmd_listadmins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض قائمة الإدمنات."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ ليس لديك صلاحية لهذا الأمر.")
        return
    admins = load_admins()
    if not admins:
        await update.message.reply_text("📋 لا يوجد إدمنات حالياً.")
        return
    lines = ["👥 *قائمة الإدمنات:*\n"]
    for i, aid in enumerate(sorted(admins), 1):
        master = " 👑" if aid == MASTER_ADMIN_ID else ""
        lines.append(f"{i}. `{aid}`{master}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إرسال معرّف المستخدم (chat_id)."""
    await update.message.reply_text(
        f"🆔 معرّفك (Chat ID): `{update.effective_user.id}`",
        parse_mode="Markdown",
    )

# ═══════════════════════════════════════════════════════════════════════════════
# رد الإدمن على المستخدم (+ تفعيل المحادثة المباشرة)
# ═══════════════════════════════════════════════════════════════════════════════
async def admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    عندما يرد الإدمن (Reply) على رسالة إشعار، يتم إرسال الرد للمستخدم الأصلي
    ويدخل المستخدم في وضع المحادثة المباشرة تلقائياً.
    """
    msg = update.message
    admin_id = update.effective_user.id

    # تحقق أن المرسل إدمن
    if not is_admin(admin_id):
        return

    # تحقق أن الرسالة هي رد على رسالة أخرى
    if not msg.reply_to_message:
        return

    replied_msg_id = msg.reply_to_message.message_id
    key = (admin_id, replied_msg_id)

    # ابحث عن المستخدم الأصلي
    mapped = message_to_user_map.get(key)
    if not mapped:
        return
        
    if isinstance(mapped, tuple):
        user_chat_id, serial = mapped
    else:
        user_chat_id = mapped
        serial = None

    # تفعيل المحادثة المباشرة للمستخدم
    is_new_chat = user_chat_id not in active_chats
    active_chats[user_chat_id] = serial if serial else True

    try:
        if is_new_chat:
            serial_text = f" [طلب #{serial}]" if serial else ""
            chat_start_text = (
                f"📬 *تنبيه من قسم الأمن{serial_text}:*\n{DIVIDER}\n"
                f"💬 *أنت الآن في محادثة مباشرة مع المسؤول*\n"
                f"اكتب ردك مباشرة وسيصل للمسؤول فوراً 👇\n\n"
                f"🔚 _لإنهاء المحادثة أرسل /end_"
            )
            await context.bot.send_message(
                chat_id=user_chat_id, text=chat_start_text,
                parse_mode="Markdown", reply_markup=kb_end_chat(),
            )
            
        if msg.text:
             await context.bot.send_message(
                 chat_id=user_chat_id, 
                 text=f"📬 *المسؤول:*\n{DIVIDER}\n\n{msg.text}", 
                 parse_mode="Markdown"
             )
        else:
             await context.bot.send_message(
                 chat_id=user_chat_id, 
                 text=f"📬 *المسؤول (مرفق):*", 
                 parse_mode="Markdown"
             )
             await context.bot.copy_message(
                 chat_id=user_chat_id,
                 from_chat_id=admin_id,
                 message_id=msg.message_id
             )

        await msg.reply_text("✅ تم إرسال ردك للمستخدم بنجاح.")
        logger.info(f"Admin {admin_id} replied to user {user_chat_id} (live_chat={not is_new_chat})")
    except Exception as e:
        await msg.reply_text(f"❌ فشل إرسال الرد: {e}")
        logger.error(f"Reply to user {user_chat_id} failed: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# التشغيل الرئيسي
# ═══════════════════════════════════════════════════════════════════════════════
def main() -> None:
    # تهيئة ملف الإدمنات
    init_admins()

    app = Application.builder().token(BOT_TOKEN).build()

    any_msg = filters.ALL & ~filters.COMMAND

    # ── معترض المحادثة المباشرة (مجموعة -1 ليعمل قبل ConversationHandler) ──
    app.add_handler(MessageHandler(any_msg, intercept_live_chat), group=-1)
    app.add_handler(CallbackQueryHandler(end_chat_button, pattern=r"^end_chat$"), group=-1)

    conv = ConversationHandler(
        per_message=False,
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(main_menu, pattern=r"^(badge|vauth|telegram|suggest|home)$")
            ],
            # ── الباج ──────────────────────────────────────────
            BADGE_NAME:    [MessageHandler(any_msg, badge_name)],
            BADGE_MIL_NUM: [MessageHandler(any_msg, badge_mil_num)],
            BADGE_UNIT:    [MessageHandler(any_msg, badge_unit)],
            BADGE_PROBLEM: [MessageHandler(any_msg, badge_problem)],
            # ── التخويل ────────────────────────────────────────
            VEHICLE_AUTH_MENU: [
                CallbackQueryHandler(vauth_menu, pattern=r"^(va_|home)")
            ],
            VA_NAME:    [MessageHandler(any_msg, va_name)],
            VA_MIL_NUM: [MessageHandler(any_msg, va_mil_num)],
            VA_UNIT:    [MessageHandler(any_msg, va_unit)],
            VA_NOTES:   [MessageHandler(any_msg, va_notes)],
            # ── البرقيات ───────────────────────────────────────
            TG_NAME:     [MessageHandler(any_msg, tg_name)],
            TG_VEH_TYPE: [MessageHandler(any_msg, tg_veh_type)],
            TG_COLOR:    [MessageHandler(any_msg, tg_color)],
            TG_FROM_TO:  [MessageHandler(any_msg, tg_from_to)],
            TG_DATE:     [MessageHandler(any_msg, tg_date)],
            # ── مقترح ──────────────────────────────────────────
            SUGGESTION: [MessageHandler(any_msg, suggestion)],
        },
        fallbacks=[
            CommandHandler("start", start),
            CommandHandler("end", cmd_end),
            CallbackQueryHandler(go_home, pattern=r"^home$"),
        ],
        allow_reentry=True,
    )

    # تخزين مرجع ConversationHandler للاستخدام في admin_reply
    global conv_handler
    conv_handler = conv

    app.add_handler(conv)

    # ── أوامر عامة ───────────────────────────────────────────────
    app.add_handler(CommandHandler("end", cmd_end))

    # ── أوامر إدارة الإدمنات ───────────────────────────────────────────────
    app.add_handler(CommandHandler("addadmin", cmd_addadmin))
    app.add_handler(CommandHandler("removeadmin", cmd_removeadmin))
    app.add_handler(CommandHandler("listadmins", cmd_listadmins))
    app.add_handler(CommandHandler("myid", cmd_myid))

    # ── معالج رد الإدمن على المستخدم ──────────────────────────────────────
    # يلتقط أي رسالة تكون رداً (reply) من إدمن
    app.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND & filters.REPLY,
        admin_reply,
    ))

    print("[Kameel Bot] Running and polling for updates...", flush=True)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
