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


def is_chaharshanbe_suri(today):
    """غروب سه‌شنبه‌ی پیش از آخرین چهارشنبه‌ی سال."""
    d = jdatetime.date(today.year, 12, last_day_of_year(today.year))
    while d.togregorian().weekday() != 2:      # 2 = چهارشنبه
        d -= jdatetime.timedelta(days=1)
    return today == d - jdatetime.timedelta(days=1)


def is_panjeh(today):
    """آغاز پنج روز پایانی سال."""
    return today == jdatetime.date(today.year, 12,
                                   last_day_of_year(today.year) - 4)


RULES = {"chaharshanbe_suri": is_chaharshanbe_suri, "panjeh": is_panjeh}


def matches(item, today):
    if "rule" in item:
        return RULES[item["rule"]](today)
    return item["month"] == today.month and item["day"] == today.day


if __name__ == "__main__":
    # تاریخ امروز به وقت تهران، تبدیل به شمسی
    now = datetime.datetime.now(ZoneInfo("Asia/Tehran")).date()
    today = jdatetime.date.fromgregorian(date=now)

    with open("festivals.json", encoding="utf-8") as f:
        festivals = json.load(f)

    items = [x for x in festivals if matches(x, today)]
    if not items:
        print("امروز مناسبتی نیست؛ چیزی ارسال نشد.")
        raise SystemExit(0)   # خروج عادی، تا GitHub اجرا را «موفق» ثبت کند

    header = f"📅 {today.day} {MONTHS[today.month - 1]}"
    body = "\n\n".join(f"🔥 {x['title']}\n{x['text']}" for x in items)

    resp = requests.post(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data={"chat_id": CHANNEL, "text": f"{header}\n\n{body}"},
        timeout=30,
    )
    resp.raise_for_status()
    print("ارسال شد.")
