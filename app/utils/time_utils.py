from datetime import datetime, timezone, timedelta

indonesia_tz = timezone(timedelta(hours=7))


def get_indonesia_time():
    return datetime.now(indonesia_tz)


def get_indonesia_date():
    return datetime.now(indonesia_tz).date()
