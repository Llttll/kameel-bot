#!/usr/bin/env python3
"""
بوت قسم الأمن - كميل
Security Department Telegram Bot
"""

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
)

# ─── الإعدادات ────────────────────────────────────────────────────────────────
BOT_TOKEN = "8478999240:AAGHK7aSH2rz_3doNM6uJLStfXxRUWICe1c"   # ← ضع توكن البوت هنا
ADMIN_CHAT_ID = 38866499                 # ← ضع معرّف الإدمن لاستقبال الطلبات (اختياري)

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

# ─── مساعد: إشعار الإدمن ────────────────────────────────────────────────────
async def notify_admin(context: ContextTypes.DEFAULT_TYPE, user, text: str):
    if not ADMIN_CHAT_ID:
        return
    try:
        mention = f"@{user.username}" if user.username else user.first_name
        msg = f"🔔 *طلب جديد* من {mention} (ID: `{user.id}`)\n\n{text}"
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Admin notify failed: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# شاشة البداية
# ═══════════════════════════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await send_or_edit(update, WELCOME, kb_main())
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════════════════════
# القائمة الرئيسية
# ═══════════════════════════════════════════════════════════════════════════════
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    q = update.callback_query
    await q.answer()

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
    context.user_data["b_name"] = update.message.text
    await update.message.reply_text(
        "✅ تم.\n\n*2️⃣  الرقم العسكري:*\nأرسل رقمك العسكري 👇",
        parse_mode="Markdown",
    )
    return BADGE_MIL_NUM

async def badge_mil_num(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["b_mil"] = update.message.text
    await update.message.reply_text(
        "✅ تم.\n\n*3️⃣  الوحدة / الفوج / القسم:*\nأرسل اسم وحدتك 👇",
        parse_mode="Markdown",
    )
    return BADGE_UNIT

async def badge_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["b_unit"] = update.message.text
    await update.message.reply_text(
        "✅ تم.\n\n*4️⃣  ما هية المشكلة؟*\nاشرح مشكلتك بالتفصيل 👇",
        parse_mode="Markdown",
    )
    return BADGE_PROBLEM

async def badge_problem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["b_prob"] = update.message.text
    d = context.user_data

    summary = (
        f"✅ *تم استلام طلبك بنجاح!*\n\n"
        f"📋 *ملخص طلب الباج (الهوية):*\n{DIVIDER}\n"
        f"👤 الاسم الثلاثي : {d.get('b_name')}\n"
        f"🔢 الرقم العسكري : {d.get('b_mil')}\n"
        f"🏛️ الوحدة / الفوج : {d.get('b_unit')}\n"
        f"❗ المشكلة : {d.get('b_prob')}\n"
        f"{DIVIDER}\n📩 سيتم التواصل معك في أقرب وقت ممكن 🫡"
    )
    await update.message.reply_text(summary, reply_markup=kb_back(), parse_mode="Markdown")
    await notify_admin(context, update.effective_user, summary)
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
    context.user_data["va_name"] = update.message.text
    await update.message.reply_text(
        "✅ تم.\n\n*2️⃣  الرقم العسكري:*\nأرسل رقمك العسكري 👇",
        parse_mode="Markdown",
    )
    return VA_MIL_NUM

async def va_mil_num(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["va_mil"] = update.message.text
    await update.message.reply_text(
        "✅ تم.\n\n*3️⃣  الوحدة / الفوج / القسم:*\nأرسل اسم وحدتك 👇",
        parse_mode="Markdown",
    )
    return VA_UNIT

async def va_unit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["va_unit"] = update.message.text
    await update.message.reply_text(
        "✅ تم.\n\n*4️⃣  ملاحظات إضافية / تفاصيل الطلب:*\nأضف أي تفاصيل 👇",
        parse_mode="Markdown",
    )
    return VA_NOTES

async def va_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["va_notes"] = update.message.text
    d = context.user_data

    summary = (
        f"✅ *تم استلام طلبك بنجاح!*\n\n"
        f"🚗 *ملخص طلب التخويل:*\n{DIVIDER}\n"
        f"📌 نوع الطلب : {d.get('va_type')}\n"
        f"👤 الاسم الثلاثي : {d.get('va_name')}\n"
        f"🔢 الرقم العسكري : {d.get('va_mil')}\n"
        f"🏛️ الوحدة / الفوج : {d.get('va_unit')}\n"
        f"📝 الملاحظات : {d.get('va_notes')}\n"
        f"{DIVIDER}\n📩 سيتم التواصل معك في أقرب وقت ممكن 🫡"
    )
    await update.message.reply_text(summary, reply_markup=kb_back(), parse_mode="Markdown")
    await notify_admin(context, update.effective_user, summary)
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════════════════════
# نموذج البرقيات
# ═══════════════════════════════════════════════════════════════════════════════
async def tg_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["tg_name"] = update.message.text
    await update.message.reply_text(
        "✅ تم.\n\n*2️⃣  نوع العجلة:*\nأرسل نوع العجلة 👇",
        parse_mode="Markdown",
    )
    return TG_VEH_TYPE

async def tg_veh_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["tg_veh"] = update.message.text
    await update.message.reply_text(
        "✅ تم.\n\n*3️⃣  اللون والموديل:*\nأرسل لون وموديل العجلة 👇",
        parse_mode="Markdown",
    )
    return TG_COLOR

async def tg_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["tg_color"] = update.message.text
    await update.message.reply_text(
        "✅ تم.\n\n*4️⃣  من وإلى:*\nأرسل الوجهة (من أين وإلى أين) 👇",
        parse_mode="Markdown",
    )
    return TG_FROM_TO

async def tg_from_to(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["tg_route"] = update.message.text
    await update.message.reply_text(
        "✅ تم.\n\n*5️⃣  التاريخ:*\nأرسل تاريخ البرقية 👇",
        parse_mode="Markdown",
    )
    return TG_DATE

async def tg_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["tg_date"] = update.message.text
    d = context.user_data

    summary = (
        f"✅ *تم استلام البرقية بنجاح!*\n\n"
        f"📨 *ملخص البرقية:*\n{DIVIDER}\n"
        f"👤 بأمرة (الاسم) : {d.get('tg_name')}\n"
        f"🚗 نوع العجلة : {d.get('tg_veh')}\n"
        f"🎨 اللون والموديل : {d.get('tg_color')}\n"
        f"📍 من وإلى : {d.get('tg_route')}\n"
        f"📅 التاريخ : {d.get('tg_date')}\n"
        f"{DIVIDER}\n📩 سيتم التواصل معك في أقرب وقت ممكن 🫡"
    )
    await update.message.reply_text(summary, reply_markup=kb_back(), parse_mode="Markdown")
    await notify_admin(context, update.effective_user, summary)
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════════════════════
# مقترح / مشكلة
# ═══════════════════════════════════════════════════════════════════════════════
async def suggestion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    await update.message.reply_text(
        f"✅ *شكراً لك!*\n\n"
        f"💡 تم استلام مقترحك/مشكلتك وسيتم إيصالها للمسؤولين.\n"
        f"{DIVIDER}\n📩 سيتم التواصل معك في أقرب وقت ممكن 🫡",
        reply_markup=kb_back(),
        parse_mode="Markdown",
    )
    await notify_admin(
        context,
        update.effective_user,
        f"💡 *مقترح / مشكلة:*\n{DIVIDER}\n{text}",
    )
    return MAIN_MENU

# ═══════════════════════════════════════════════════════════════════════════════
# زر العودة من أي حالة
# ═══════════════════════════════════════════════════════════════════════════════
async def go_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await start(update, context)

# ═══════════════════════════════════════════════════════════════════════════════
# التشغيل الرئيسي
# ═══════════════════════════════════════════════════════════════════════════════
def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    txt = filters.TEXT & ~filters.COMMAND

    conv = ConversationHandler(
        per_message=False,
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                CallbackQueryHandler(main_menu, pattern=r"^(badge|vauth|telegram|suggest|home)$")
            ],
            # ── الباج ──────────────────────────────────────────
            BADGE_NAME:    [MessageHandler(txt, badge_name)],
            BADGE_MIL_NUM: [MessageHandler(txt, badge_mil_num)],
            BADGE_UNIT:    [MessageHandler(txt, badge_unit)],
            BADGE_PROBLEM: [MessageHandler(txt, badge_problem)],
            # ── التخويل ────────────────────────────────────────
            VEHICLE_AUTH_MENU: [
                CallbackQueryHandler(vauth_menu, pattern=r"^(va_|home)")
            ],
            VA_NAME:    [MessageHandler(txt, va_name)],
            VA_MIL_NUM: [MessageHandler(txt, va_mil_num)],
            VA_UNIT:    [MessageHandler(txt, va_unit)],
            VA_NOTES:   [MessageHandler(txt, va_notes)],
            # ── البرقيات ───────────────────────────────────────
            TG_NAME:     [MessageHandler(txt, tg_name)],
            TG_VEH_TYPE: [MessageHandler(txt, tg_veh_type)],
            TG_COLOR:    [MessageHandler(txt, tg_color)],
            TG_FROM_TO:  [MessageHandler(txt, tg_from_to)],
            TG_DATE:     [MessageHandler(txt, tg_date)],
            # ── مقترح ──────────────────────────────────────────
            SUGGESTION: [MessageHandler(txt, suggestion)],
        },
        fallbacks=[
            CommandHandler("start", start),
            CallbackQueryHandler(go_home, pattern=r"^home$"),
        ],
        allow_reentry=True,
    )

    app.add_handler(conv)

    print("[Kameel Bot] Running and polling for updates...", flush=True)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()