from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import re


def change_date_str(strng):
    match = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", strng)
    day, month, year = map(int, match.groups())
    return re.sub(
        r"(\d{1,2})\.(\d{1,2})\.(\d{4}).*",
        f"{str(day)}.{str(month+1)}.{str(year)}",
        strng,
    )


def extract_date(url):
    match = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", url)
    day, month, year = map(int, match.groups())
    date = datetime(
        year, month - 1, day
    )  # -1 because in website months are from 2 to 13
    return date


def get_other_day_url(url):
    date = extract_date(url)
    new_date = date - timedelta(days=1)
    formatted_date = new_date.strftime("%d.%m.%Y")
    updated_url = re.sub(r"(\d{1,2})\.(\d{1,2})\.(\d{4}).*", formatted_date, url)
    updated_url = change_date_str(updated_url)
    return updated_url


def get_next_page_in_day(next_li_element):
    match = re.search(r"\'(.+)\'", next_li_element)
    return match.group(1)


def get_date_url(date):
    date_str = date.strftime("%d.%m.%Y")
    date_str = change_date_str(date_str)
    return f"https://rustavi2.ge/ka/news/politics/date/{date_str}"
