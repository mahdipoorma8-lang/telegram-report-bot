# main.py
# Telegram Daily Report Bot - Production Ready
# Persian commands + Jalali date + Daily reminder (Asia/Tehran)
# python-telegram-bot v20+

import sqlite3
import os
import jdatetime
from datetime import time
from zoneinfo import ZoneInfo
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

# ========= تنظیمات =========
load_dotenv()  # خواندن متغیرهای محیطی
BOT_TOKEN = os.getenv("BOT_TOKEN") or "8217406460:AAFhmRdYqMbR5CKT2YsjDl6A-0gdixzTBW4"
ADMIN_IDS = list(map(int, os.getenv("7506306837", "").split(",")))
DB_NAME = "reports.db"

# ساعت یادآوری به وقت ایران
REMINDER_HOUR = 20
REMINDER_MINUTE = 0
# ===========================


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT,
            report_date TEXT,
            report_text TEXT
        )
    """)
    conn.commit()
    conn.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n"
        "هر روز فقط *یک گزارش* می‌تونی بفرستی.\n"
        "اگه دوباره پیام بدی، گزارش امروزت *ویرایش* میشه ✏️\n\n"
        "📌 دستور مدیر:\n"
        "/گزارش_ماهانه"
    )


async def save_or_edit_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text
    today = jdatetime.date.today().strftime("%Y/%m/%d")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    # بررسی گزارش امروز
    c.execute(
        "SELECT id FROM reports WHERE user_id=? AND report_date=?",
        (user.id, today),
    )
    row = c.fetchone()

    if row:
        # ویرایش گزارش
        c.execute(
            "UPDATE reports SET report_text=? WHERE id=?",
            (text, row[0]),
        )
        conn.commit()
        conn.close()
        await update.message.reply_text("✏️ گزارش امروز ویرایش شد")
    else:
        # ثبت گزارش جدید
        c.execute(
            "INSERT INTO reports (user_id, full_name, report_date, report_text) "
            "VALUES (?, ?, ?, ?)",
            (user.id, user.full_name, today, text),
        )
        conn.commit()
        conn.close()
        await update.message.reply_text("✅ گزارش امروز ثبت شد")


async def gozaresh_mahane(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ شما دسترسی ندارید")
        return

    now = jdatetime.date.today()
    month_prefix = f"{now.year}/{str(now.month).zfill(2)}"

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT full_name, report_date, report_text FROM reports "
        "WHERE report_date LIKE ? ORDER BY report_date",
        (f"{month_prefix}%",),
    )
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("📭 گزارشی برای این ماه ثبت نشده")
        return

    message = f"📊 گزارش ماه {month_prefix} (شمسی)\n\n"
    for full_name, date, report in rows:
        message += f"👤 {full_name} – {date}\n"
        message += f"{report}\n"
        message += "─" * 20 + "\n"

    for i in range(0, len(message), 4000):
        await update.message.reply_text(message[i:i + 4000])


# ========= یادآوری روزانه (ساعت ۱۷ ایران) =========
async def daily_reminder(context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id FROM reports")
    users = c.fetchall()
    conn.close()

    for (user_id,) in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="⏰ یادآوری روزانه\n"
                     "لطفاً گزارش امروزت رو ارسال کن 📝"
            )
        except:
            pass


async def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("گزارش_ماهانه", gozaresh_mahane))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_or_edit_report))

    # جاب یادآوری
    app.job_queue.run_daily(
        daily_reminder,
        time=time(
            hour=REMINDER_HOUR,
            minute=REMINDER_MINUTE,
            tzinfo=ZoneInfo("Asia/Tehran"),
        ),
    )

    print("Bot is running...")
    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
