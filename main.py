# main.py
# Telegram Daily Report Bot
# Persian messages + Jalali date + Daily reminder (Asia/Tehran)
# python-telegram-bot v20+

import os
import sqlite3
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

# ================== تنظیمات ==================
BOT_TOKEN = os.getenv("8217406460:AAFhmRdYqMbR5CKT2YsjDl6A-0gdixzTBW4")

admin_env = os.getenv("7506306837")
if not admin_env or admin_env.strip() == "":
    print("⚠️ ADMIN_IDS تنظیم نشده")
    ADMIN_IDS = []
else:
    ADMIN_IDS = [int(x) for x in admin_env.split(",")]

DB_NAME = "reports.db"

REMINDER_HOUR = 17
REMINDER_MINUTE = 0
# =============================================


# ================== دیتابیس ==================
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


# ================== دستورات ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام 👋\n\n"
        "📝 هر روز گزارش کارت رو همینجا بفرست.\n"
        "✏️ اگر دوباره پیام بدی، گزارش امروزت ویرایش میشه.\n\n"
        "📌 دستور مدیر:\n"
        "/monthly_report"
    )


async def save_or_edit_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    text = update.message.text
    today = jdatetime.date.today().strftime("%Y/%m/%d")

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()

    c.execute(
        "SELECT id FROM reports WHERE user_id=? AND report_date=?",
        (user.id, today),
    )
    row = c.fetchone()

    if row:
        c.execute(
            "UPDATE reports SET report_text=? WHERE id=?",
            (text, row[0]),
        )
        conn.commit()
        conn.close()
        await update.message.reply_text("✏️ گزارش امروز ویرایش شد")
    else:
        c.execute(
            "INSERT INTO reports (user_id, full_name, report_date, report_text) "
            "VALUES (?, ?, ?, ?)",
            (user.id, user.full_name, today, text),
        )
        conn.commit()
        conn.close()
        await update.message.reply_text("✅ گزارش امروز ثبت شد")


async def monthly_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ شما دسترسی ندارید")
        return

    now = jdatetime.date.today()
    month_prefix = f"{now.year}/{str(now.month).zfill(2)}"

    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT full_name, report_date, report_text "
        "FROM reports WHERE report_date LIKE ? ORDER BY report_date",
        (f"{month_prefix}%",),
    )
    rows = c.fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("📭 گزارشی برای این ماه ثبت نشده")
        return

    message = f"📊 گزارش ماه {month_prefix}\n\n"
    for full_name, date, report in rows:
        message += f"👤 {full_name}\n📅 {date}\n{report}\n"
        message += "─" * 20 + "\n"

    for i in range(0, len(message), 4000):
        await update.message.reply_text(message[i:i + 4000])


# ================== یادآوری ==================
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


# ================== اجرا ==================
async def main():
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("monthly_report", monthly_report))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, save_or_edit_report)
    )

    app.job_queue.run_daily(
        daily_reminder,
        time=time(
            hour=REMINDER_HOUR,
            minute=REMINDER_MINUTE,
            tzinfo=ZoneInfo("Asia/Tehran"),
