import datetime
import html
import json
import os
import re
from zoneinfo import ZoneInfo

import jdatetime
import requests

TOKEN = os.environ["BOT_TOKEN"]        # توکنی که BotFather داده
CHANNEL = os.environ["CHANNEL_ID"]     # مثل @my_channel

MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
          "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
G_MONTHS = ["ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن",
            "ژوئیه", "اوت", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"]

DIVIDER = "┈┈┈┈┈┈┈┈┈┈┈┈┈┈"
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def to_fa_digits(text):
    """همه‌ی ارقام لاتین را فارسی می‌کند."""
    return text.translate(FA_DIGITS)


# ───────────── قواعد تاریخ ─────────────

def last_day_of_year(year):
    """آخرین روز سال شمسی: ۳۰ اسفند در سال کبیسه، وگرنه ۲۹."""
    return 30 if jdatetime.date(year, 1, 1).isleap() else 29


def nth_weekday(year, month, weekday, n):
    """n‌امین روز مشخصِ هفته در یک ماه میلادی (weekday: دوشنبه=۰ ... یکشنبه=۶)."""
    first = datetime.date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + datetime.timedelta(days=offset + 7 * (n - 1))


def thanksgiving(year):
    """تشکرگزاری آمریکا: پنجشنبه‌ی چهارم نوامبر."""
    return nth_weekday(year, 11, 3, 4)


# هر قاعده‌ی خاص دو ورودی می‌گیرد: تاریخ شمسی و تاریخ میلادیِ امروز (هر دو به وقت تهران)
def is_chaharshanbe_suri(j, g):
    """غروب سه‌شنبه‌ی پیش از آخرین چهارشنبه‌ی سال شمسی."""
    d = jdatetime.date(j.year, 12, last_day_of_year(j.year))
    while d.togregorian().weekday() != 2:      # 2 = چهارشنبه
        d -= jdatetime.timedelta(days=1)
    return j == d - jdatetime.timedelta(days=1)


def is_panjeh(j, g):
    """آغاز پنج روز پایانی سال شمسی."""
    return j == jdatetime.date(j.year, 12, last_day_of_year(j.year) - 4)


def is_us_mothers_day(j, g):
    return g == nth_weekday(g.year, 5, 6, 2)       # یکشنبه‌ی دوم مه


def is_us_fathers_day(j, g):
    return g == nth_weekday(g.year, 6, 6, 3)       # یکشنبه‌ی سوم ژوئن


def is_us_labor_day(j, g):
    return g == nth_weekday(g.year, 9, 0, 1)       # دوشنبه‌ی اول سپتامبر


def is_black_friday(j, g):
    return g == thanksgiving(g.year) + datetime.timedelta(days=1)


RULES = {
    "chaharshanbe_suri": is_chaharshanbe_suri,
    "panjeh": is_panjeh,
    "us_mothers_day": is_us_mothers_day,
    "us_fathers_day": is_us_fathers_day,
    "us_labor_day": is_us_labor_day,
    "black_friday": is_black_friday,
}


def matches(item, j, g):
    """آیا مناسبت امروز است؟ سه نوع: قاعده‌ای، میلادی ثابت، شمسی ثابت."""
    if "rule" in item:
        return RULES[item["rule"]](j, g)
    if "gmonth" in item:
        return item["gmonth"] == g.month and item["gday"] == g.day
    return item["month"] == j.month and item["day"] == j.day


# ───────────── قالب‌بندی پیام ─────────────

def split_text(text):
    """
    متن را به سه بخش تقسیم می‌کند:
      lead   : جمله‌ی اول (خلاصه) برای نقل‌قول
      points : بقیه‌ی جمله‌ها و بندهای جداشده با «؛» برای بولت
      notes  : جمله‌های داخل پرانتز (مثل «در شمارش زرتشتی ۱۶ مهر»)
    """
    sentences = [s.strip() for s in re.split(r"(?<=[.!؟?])\s+", text.strip()) if s.strip()]
    notes = [s[1:-1].strip() for s in sentences if s.startswith("(") and s.endswith(")")]
    body = [s for s in sentences if not (s.startswith("(") and s.endswith(")"))]
    if not body:
        return "", [], notes

    first_parts = [p.strip() for p in body[0].rstrip(".").split("؛") if p.strip()]
    lead = first_parts[0]
    points = first_parts[1:]
    for s in body[1:]:
        points += [p.strip() for p in s.rstrip(".").split("؛") if p.strip()]
    return lead, points, notes


def format_item(item):
    """یک مناسبت را به متن HTML تلگرام تبدیل می‌کند."""
    esc = lambda s: html.escape(s, quote=False)
    lead, points, notes = split_text(item["text"])

    lines = [f"🔥 <b>{esc(item['title'])}</b>", ""]
    if lead:
        lines += [f"<blockquote>{esc(lead)}</blockquote>", ""]
    lines += [f"• {esc(p)}" for p in points]
    if points:
        lines.append("")
    lines += [f"🗓 <i>{esc(n)}</i>" for n in notes]
    if item.get("fact"):
        lines += ["", f"<blockquote>📜 <b>بدانید:</b> {esc(item['fact'])}</blockquote>"]
    return "\n".join(lines).strip()


def build_message(items, j, g):
    head = (f"📅 <b>{j.day} {MONTHS[j.month - 1]} {j.year}</b>\n"
            f"<i>{g.day} {G_MONTHS[g.month - 1]} {g.year}</i>")
    sep = f"\n\n{DIVIDER}\n\n"
    body = sep.join(format_item(x) for x in items)
    return to_fa_digits(f"{head}\n{DIVIDER}\n\n{body}")


def send(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    resp = requests.post(url, data={"chat_id": CHANNEL, "text": text,
                                    "parse_mode": "HTML"}, timeout=30)
    if resp.status_code == 400:
        # اگر تلگرام قالب‌بندی را نپذیرفت، همان متن را ساده بفرست
        plain = html.unescape(re.sub(r"<[^>]+>", "", text))
        resp = requests.post(url, data={"chat_id": CHANNEL, "text": plain}, timeout=30)
    resp.raise_for_status()


if __name__ == "__main__":
    # تاریخ امروز به وقت تهران، هم میلادی و هم شمسی
    g = datetime.datetime.now(ZoneInfo("Asia/Tehran")).date()
    j = jdatetime.date.fromgregorian(date=g)

    with open("festivals.json", encoding="utf-8") as f:
        festivals = json.load(f)

    items = [x for x in festivals if matches(x, j, g)]
    if not items:
        print("امروز مناسبتی نیست؛ چیزی ارسال نشد.")
        raise SystemExit(0)   # خروج عادی، تا GitHub اجرا را «موفق» ثبت کند

    send(build_message(items, j, g))
    print("ارسال شد.")
