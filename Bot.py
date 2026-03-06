import os, asyncio, sqlite3, yt_dlp, time, html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- CONFIGURATION ---
TOKEN = "8209292293:AAGjegQ0Ev-C-r2uC3lOGOCXeXRE87obiRE"
ADMIN_ID = 6806787718          
LOG_CHANNEL_ID = -1003728640833
FORCE_SUB_CHANNEL = "@downlodhistoryy"

# --- DATABASE ---
conn = sqlite3.connect('final_legend_v4.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, state TEXT DEFAULT "none")')
conn.commit()

# --- HELPERS ---
async def is_member(user_id, context):
    try:
        m = await context.bot.get_chat_member(chat_id=FORCE_SUB_CHANNEL, user_id=user_id)
        return m.status in ['member', 'administrator', 'creator']
    except: return False

async def cyber_anim(message, steps):
    for step in steps:
        try:
            await message.edit_text(f"<b>{step}</b>", parse_mode='HTML')
            await asyncio.sleep(0.5)
        except: pass

def download_video(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    if not os.path.exists('downloads'): os.makedirs('downloads')
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
        size = f"{os.path.getsize(path)/(1024*1024):.2f} MB"
        return path, info.get('title', 'Video'), size

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_id = update.effective_user.id
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (u_id,))
    conn.commit()

    if u_id == ADMIN_ID:
        btn = [[InlineKeyboardButton("📊 Total Users", callback_data="stats"), InlineKeyboardButton("📢 Broadcast", callback_data="bc")],
               [InlineKeyboardButton("📥 User View", callback_data="ask_link")]]
        await update.message.reply_text("<b>🛠 ADMIN CONTROL PANEL</b>", reply_markup=InlineKeyboardMarkup(btn), parse_mode='HTML')
    else:
        if not await is_member(u_id, context):
            btn = [[InlineKeyboardButton("Join Channel 📢", url=f"https://t.me/{FORCE_SUB_CHANNEL[1:]}")],
                   [InlineKeyboardButton("Verify ✅", callback_data="verify")]]
            await update.message.reply_text("<b>👋 Hello! Pehle join karein.</b>", reply_markup=InlineKeyboardMarkup(btn), parse_mode='HTML')
        else:
            await update.message.reply_text("<b>✅ System Ready!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download Video", callback_data="ask_link")]]), parse_mode='HTML')

async def callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    u_id = query.from_user.id
    await query.answer()

    if query.data == "verify":
        if await is_member(u_id, context):
            await query.edit_message_text("<b>✅ Verified!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📥 Download Video", callback_data="ask_link")]]), parse_mode='HTML')
        else: await query.answer("❌ Pehle join kijiye!", show_alert=True)
    
    elif query.data == "ask_link":
        cursor.execute('UPDATE users SET state = "waiting" WHERE user_id = ?', (u_id,))
        conn.commit()
        await query.message.reply_text("🚀 <b>Send link to download...</b>", parse_mode='HTML')

    elif query.data == "bc":
        cursor.execute('UPDATE users SET state = "bc_mode" WHERE user_id = ?', (u_id,))
        conn.commit()
        await query.message.reply_text("📢 <b>BROADCAST MODE:</b>\nSend any message (Text/Media) to blast.")

    elif query.data == "stats":
        cursor.execute('SELECT COUNT(*) FROM users')
        await query.message.reply_text(f"📊 Total Users: <code>{cursor.fetchone()[0]}</code>", parse_mode='HTML')

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u_id = update.effective_user.id
    cursor.execute('SELECT state FROM users WHERE user_id = ?', (u_id,))
    res = cursor.fetchone()
    state = res[0] if res else "none"

    # --- 1. BROADCAST LOGIC (50+ Users Animation) ---
    if state == "bc_mode" and u_id == ADMIN_ID:
        cursor.execute('UPDATE users SET state = "none" WHERE user_id = ?', (u_id,))
        conn.commit()
        cursor.execute('SELECT user_id FROM users'); all_u = cursor.fetchall()
        
        st = await update.message.reply_text("📡 <b>Initializing Broadcast...</b>", parse_mode='HTML')
        log_m = await context.bot.send_message(LOG_CHANNEL_ID, "🛰 <b>Starting Mass Broadcast...</b>", parse_mode='HTML')
        
        s, f, total = 0, 0, len(all_u)
        for i, (target,) in enumerate(all_u):
            try:
                await context.bot.copy_message(target, update.message.chat_id, update.message.message_id)
                s += 1
            except: f += 1
            if i % 5 == 0:
                prog = f"🚀 <b>Progress: {int((i+1)/total*100)}%</b>\n✅ Success: {s}\n❌ Fail: {f}"
                try: 
                    await st.edit_text(prog, parse_mode='HTML')
                    await log_m.edit_text(f"📊 <b>Channel Progress:</b>\n{prog}", parse_mode='HTML')
                except: pass
        await st.edit_text(f"🎊 <b>Done! Sent to {s} users.</b>", parse_mode='HTML')
        return

    # --- 2. DOWNLOAD LOGIC (System Notice Format) ---
    if state == "waiting" and update.message.text and "http" in update.message.text:
        cursor.execute('UPDATE users SET state = "none" WHERE user_id = ?', (u_id,))
        conn.commit()
        
        bot_st = await update.message.reply_text("🔌 <code>Connecting...</code>", parse_mode='HTML')
        start_t = time.time()
        
        try:
            path, title, size = await asyncio.to_thread(download_video, update.message.text)
            await cyber_anim(bot_st, ["🔍 Scanning...", "🔐 Verifying...", "🧬 Decoding...", "🎉 Ready!"])
            
            safe_t = html.escape(title)
            safe_n = html.escape(update.effective_user.first_name)

            # Professional Log Notice
            notice = (
                f"🔻 <b>SYSTEM NOTICE: NEW DOWNLOAD LOG</b> 🔻\n\n"
                f"👤  <b>User Detected</b> → {safe_n}\n"
                f"🎬  <b>Media Title</b> → {safe_t[:25]}...\n"
                f"📦  <b>File Size</b> → {size}\n"
                f"⏱  <b>Time</b> → {round(time.time()-start_t, 2)}s\n\n"
                f"🟢 <b>DELIVERY SUCCESS</b>\n"
                f"📤 <b>Log Entry Updated in Channel</b>"
            )
            await context.bot.send_message(LOG_CHANNEL_ID, notice, parse_mode='HTML')

            with open(path, 'rb') as v:
                await context.bot.send_video(u_id, v, caption=f"✅ <b>{safe_t}</b>", supports_streaming=True, parse_mode='HTML')
            os.remove(path); await bot_st.delete()
            
        except Exception as e:
            await bot_st.edit_text(f"❌ Error: {html.escape(str(e))}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback_query))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_msg))
    app.run_polling()
    
