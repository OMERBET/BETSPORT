"""
Sports Predictions Telegram Bot
Install: pip install python-telegram-bot requests
Run: python bot.py
"""
import logging
import requests
from datetime import datetime, date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ── CONFIG ─────────────────────────────────────────────────────
BOT_TOKEN = "8718292164:AAFcRvNYU09JN3A019u-6sdnwaSoG8B1ZUk"        # من @BotFather
FOOTBALL_API_KEY = "FOOTBALL_API_KEY"   # من api-football.com (مجاني)
API_BASE = "https://v3.football.api-sports.io"

LEAGUES = {
    "البريميرليج": 39,
    "الليغا": 140,
    "البوندسليغا": 78,
    "السيريا A": 135,
    "الليغ 1": 61,
    "دوري الابطال": 2,
}

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)


def api_get(endpoint, params=None):
    headers = {"x-apisports-key": FOOTBALL_API_KEY}
    try:
        r = requests.get(f"{API_BASE}/{endpoint}", headers=headers, params=params or {}, timeout=10)
        return r.json()
    except Exception as e:
        logging.error(f"API Error: {e}")
        return {}


def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 نتائج مباشرة", callback_data="live"),
         InlineKeyboardButton("📅 مباريات اليوم", callback_data="today")],
        [InlineKeyboardButton("🎯 توقعات اليوم", callback_data="predict"),
         InlineKeyboardButton("📊 الاوددات", callback_data="odds")],
        [InlineKeyboardButton("🏆 جداول الدوريات", callback_data="leagues"),
         InlineKeyboardButton("📈 احصائيات", callback_data="stats")],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name
    text = f"مرحبا {name}! 👋\n\n⚽ *بوت التوقعات الرياضية*\n\nاختر من القائمة:"
    await update.message.reply_text(text, reply_markup=main_kb(), parse_mode="Markdown")


async def get_live_text():
    data = api_get("fixtures", {"live": "all"})
    if not data.get("response"):
        return f"🔴 *النتائج المباشرة*\n\nلا توجد مباريات مباشرة الان\n\n_تحديث: {datetime.now().strftime('%H:%M')}_"
    text = f"🔴 *المباريات المباشرة* ({len(data['response'])})\n\n"
    for f in data["response"][:12]:
        h = f["teams"]["home"]["name"]
        a = f["teams"]["away"]["name"]
        hg = f["goals"]["home"] or 0
        ag = f["goals"]["away"] or 0
        mn = f["fixture"]["status"]["elapsed"] or "?"
        lg = f["league"]["name"]
        text += f"🟢 `{mn}'`  *{h}* {hg} - {ag} *{a}*\n    _{lg}_\n\n"
    text += f"_تحديث: {datetime.now().strftime('%H:%M')}_"
    return text


async def get_today_text():
    today = date.today().strftime("%Y-%m-%d")
    data = api_get("fixtures", {"date": today})
    if not data.get("response"):
        return "📅 *مباريات اليوم*\n\nلا توجد مباريات."
    fixtures = data["response"]
    text = f"📅 *مباريات اليوم* - {today}\n📌 {len(fixtures)} مباراة\n\n"
    leagues_map = {}
    for f in fixtures:
        leagues_map.setdefault(f["league"]["name"], []).append(f)
    for lg, matches in list(leagues_map.items())[:7]:
        text += f"🏆 *{lg}*\n"
        for f in matches[:4]:
            h = f["teams"]["home"]["name"]
            a = f["teams"]["away"]["name"]
            st = f["fixture"]["status"]["short"]
            tm = f["fixture"]["date"][11:16]
            if st == "FT":
                text += f"  ✅ {h} *{f['goals']['home']}-{f['goals']['away']}* {a}\n"
            elif st in ["1H", "2H", "HT"]:
                el = f["fixture"]["status"]["elapsed"]
                text += f"  🔴 {h} *{f['goals']['home'] or 0}-{f['goals']['away'] or 0}* {a} `{el}'`\n"
            else:
                text += f"  ⏰ `{tm}` {h} vs {a}\n"
        text += "\n"
    return text


async def get_predict_text():
    today = date.today().strftime("%Y-%m-%d")
    data = api_get("fixtures", {"date": today})
    if not data.get("response"):
        return "🎯 *توقعات اليوم*\n\nلا توجد مباريات."
    big = list(LEAGUES.values())
    fixtures = [f for f in data["response"] if f["league"]["id"] in big and f["fixture"]["status"]["short"] in ["NS","TBD"]][:7]
    if not fixtures:
        return "🎯 *توقعات اليوم*\n\nلا توجد مباريات قادمة في الدوريات الكبيرة."
    text = f"🎯 *توقعات اليوم* - {today}\n\n"
    for f in fixtures:
        h = f["teams"]["home"]["name"]
        a = f["teams"]["away"]["name"]
        lg = f["league"]["name"]
        tm = f["fixture"]["date"][11:16]
        text += f"⚽ *{h}* vs *{a}*\n🏆 {lg}  |  ⏰ {tm}\n"
        pred = api_get("predictions", {"fixture": f["fixture"]["id"]})
        if pred.get("response"):
            p = pred["response"][0].get("predictions", {})
            winner = p.get("winner", {})
            advice = p.get("advice", "")
            pct = p.get("percent", {})
            if winner and winner.get("name"):
                text += f"🏅 المتوقع: *{winner['name']}*\n"
            if advice:
                text += f"💡 {advice}\n"
            if pct:
                text += f"📊 مضيف {pct.get('home','?')} | تعادل {pct.get('draw','?')} | ضيف {pct.get('away','?')}\n"
        else:
            text += "📊 بيانات غير متوفرة\n"
        text += "--------------\n\n"
    text += "⚠️ _للترفيه فقط_"
    return text


async def get_odds_text():
    today = date.today().strftime("%Y-%m-%d")
    data = api_get("fixtures", {"date": today})
    if not data.get("response"):
        return "📊 *الاوددات*\n\nلا توجد مباريات."
    big = list(LEAGUES.values())
    fixtures = [f for f in data["response"] if f["league"]["id"] in big and f["fixture"]["status"]["short"] in ["NS","TBD"]][:8]
    text = f"📊 *الاوددات - {today}*\n\n"
    for f in fixtures:
        h = f["teams"]["home"]["name"]
        a = f["teams"]["away"]["name"]
        text += f"⚽ *{h}* vs *{a}*  |  _{f['league']['name']}_\n"
        odds = api_get("odds", {"fixture": f["fixture"]["id"], "bookmaker": 1})
        if odds.get("response"):
            try:
                bets = odds["response"][0]["bookmakers"][0]["bets"]
                for bet in bets:
                    if bet["name"] == "Match Winner":
                        for v in bet["values"]:
                            em = "🏠" if v["value"]=="Home" else ("🤝" if v["value"]=="Draw" else "✈️")
                            lb = "المضيف" if v["value"]=="Home" else ("تعادل" if v["value"]=="Draw" else "الضيف")
                            text += f"  {em} {lb}: *{v['odd']}*\n"
                        break
            except Exception:
                text += "  بيانات غير متوفرة\n"
        else:
            text += "  بيانات غير متوفرة\n"
        text += "\n"
    text += "⚠️ _للمعلومات فقط_"
    return text


async def get_standings_text(league_id):
    year = datetime.now().year
    data = api_get("standings", {"league": league_id, "season": year})
    if not data.get("response"):
        return "تعذر جلب الجدول."
    try:
        st = data["response"][0]["league"]["standings"][0]
        lg = data["response"][0]["league"]["name"]
        text = f"🏆 *{lg} {year}*\n`#   الفريق          لع ف  ت  خ  ن`\n"
        for t in st[:12]:
            nm = t["team"]["name"][:12].ljust(12)
            text += f"`{t['rank']:2}. {nm} {t['all']['played']:2} {t['all']['win']:2} {t['all']['draw']:2} {t['all']['lose']:2} {t['points']:2}`\n"
        return text
    except Exception as e:
        return f"خطا: {e}"


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data

    if d == "menu":
        await q.edit_message_text("🏠 *القائمة الرئيسية*", reply_markup=main_kb(), parse_mode="Markdown")
    elif d == "live":
        await q.edit_message_text("جاري جلب النتائج المباشرة...")
        text = await get_live_text()
        kb = [[InlineKeyboardButton("🔄 تحديث", callback_data="live"), InlineKeyboardButton("🏠 رجوع", callback_data="menu")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif d == "today":
        await q.edit_message_text("جاري التحميل...")
        text = await get_today_text()
        kb = [[InlineKeyboardButton("🔄 تحديث", callback_data="today"), InlineKeyboardButton("🏠 رجوع", callback_data="menu")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif d == "predict":
        await q.edit_message_text("جاري التحليل والتوقع...")
        text = await get_predict_text()
        kb = [[InlineKeyboardButton("🔄 تحديث", callback_data="predict"), InlineKeyboardButton("🏠 رجوع", callback_data="menu")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif d == "odds":
        await q.edit_message_text("جاري جلب الاوددات...")
        text = await get_odds_text()
        kb = [[InlineKeyboardButton("🔄 تحديث", callback_data="odds"), InlineKeyboardButton("🏠 رجوع", callback_data="menu")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif d in ["leagues", "stats"]:
        kb = [[InlineKeyboardButton(name, callback_data=f"table_{lid}")] for name, lid in LEAGUES.items()]
        kb.append([InlineKeyboardButton("🏠 رجوع", callback_data="menu")])
        await q.edit_message_text("🏆 *اختر الدوري:*", reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
    elif d.startswith("table_"):
        lid = int(d.split("_")[1])
        await q.edit_message_text("جاري جلب الجدول...")
        text = await get_standings_text(lid)
        kb = [[InlineKeyboardButton("🔙 رجوع للدوريات", callback_data="leagues"), InlineKeyboardButton("🏠 رجوع", callback_data="menu")]]
        await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


def main():
    print("Starting sports predictions bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    print("Bot is running! Send /start on Telegram")
    app.run_polling()


if __name__ == "__main__":
    main()
