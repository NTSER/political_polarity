import csv
import pathlib
import os
import re
import sys
from datetime import datetime
from urllib.parse import urljoin
import logging

import cloudscraper
from bs4 import BeautifulSoup

from time import sleep
import random

sys.path.append(os.path.join(pathlib.Path(__file__).parents[2]))

from pipelines_configuration.scrape_configuration import ScrapeConfig


class NewsScraperSpider:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper()
        self.config = ScrapeConfig().get_config()
        self.start_date = self.config["start_date"]
        self.end_date = self.config["end_date"]
        self.data_path = os.path.join(
            pathlib.Path(__file__).parents[3],
            "data",
            "scraped_data",
            f"{self.start_date.date()}_{self.end_date.date()}",
        )
        with open(
            os.path.join(self.data_path, "tvpirveli.csv"),
            "w",
            encoding="utf-8",
            newline="",
        ) as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["date", "title", "content_url", "content", "source"])
        os.makedirs(self.data_path, exist_ok=True)

    def get_next_url(self, url):
        current_page = int(re.search(r"\d+$", url).group(0))
        next_page = str(current_page + 1)
        next_url = re.sub(r"\d+$", next_page, url)
        return next_url

    def parse(self, url):
        response = self.scraper.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        items = soup.find_all("div", class_="col-md-6")[:24]
        for item in items:
            loader = {}
            date_string = (
                item.find("div", class_="tvpcard__date").find("span").text.strip()
            )
            loader["date"] = datetime.strptime(date_string, "%d.%m.%y %H:%M")
            loader["title"] = item.find("h3", class_="tvpcard__title").text.strip()
            loader["content_url"] = urljoin(url, item.find("div").find("a")["href"])
            next_url = self.get_next_url(url)
            if loader["date"] < self.start_date:
                next_url = None
            yield (loader, next_url)

    def parse_content(self, loader):
        response = self.scraper.get(loader["content_url"])
        soup = BeautifulSoup(response.text, "html.parser")
        content_element = soup.find_all("div", class_="page__usercontent")
        if isinstance(content_element, list) and len(content_element) >= 2:
            loader["content"] = content_element[1].get_text().strip()
        else:
            loader["content"] = None
        loader["source"] = "tvpirvelige"
        return loader

    def load_and_save(self, loader):
        if (loader["date"] >= self.start_date) and (loader["date"] < self.end_date):
            new_row = list(loader.values())
            with open(
                os.path.join(self.data_path, "tvpirveli.csv"),
                "a",
                encoding="utf-8",
                newline="",
            ) as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(new_row)
                logging.log(
                    logging.INFO, "Saved. current date: {}".format(loader["date"])
                )

    def scrape_tvpirveli(self):
        logging.basicConfig(level=logging.INFO)

        next_url = "https://tvpirveli.ge/ka/siaxleebi/politika?p=1"

        while True:
            logging.log(logging.INFO, next_url)
            for loader, next_url in self.parse(next_url):
                sleep(random.uniform(0.1, 0.6))
                loader = self.parse_content(loader)
                sleep(random.uniform(0.1, 0.6))
                self.load_and_save(loader)
            if next_url is None:
                break
