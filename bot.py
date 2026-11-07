import datetime
import json
import os
from zoneinfo import ZoneInfo

import jdatetime
import requests

TOKEN = os.environ["BOT_TOKEN"]        # توکنی که BotFather داده
CHANNEL = os.environ["CHANNEL_ID"]     # مثل @my_channel

MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
          "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]


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


def format_item(item):
    """عنوان + توضیح + (اگر باشد) فکت تاریخی."""
    msg = f"🔥 {item['title']}\n{item['text']}"
    if item.get("fact"):
        msg += f"\n\n📜 بدانید: {item['fact']}"
    return msg


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

    header = f"📅 {j.day} {MONTHS[j.month - 1]}"
    body = "\n\n".join(format_item(x) for x in items)

    resp = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHANNEL, "text": f"{header}\n\n{body}"},
        timeout=30,
    )
    resp.raise_for_status()
    print("ارسال شد.")
