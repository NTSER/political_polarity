import json
import pathlib
import os
import sys

import scrapy
from scrapy.loader import ItemLoader

from ..items import Tv1GeItem
from ..utils import URLS, get_next_url

sys.path.append(os.path.join(pathlib.Path(__file__).parents[4]))

from pipelines_configuration.scrape_configuration import ScrapeConfig


class Tv1Spider(scrapy.Spider):
    name = "tv1"
    allowed_domains = ["1tv.ge"]
    config = ScrapeConfig().get_config()
    start_date = config["start_date"]
    end_date = config["end_date"]
    date = end_date

    def start_requests(self):
        for url in URLS:
            yield scrapy.Request(url, method="POST", callback=self.parse)

    def parse(self, response):
        json_resp = json.loads(response.body)
        items = json_resp.get("data")
        page_exists = items != "no ids"
        if page_exists and self.date >= self.start_date:
            links = [item.get("post_permalink") for item in items]
            yield from response.follow_all(links, callback=self.parse_content)

            next_url = get_next_url(response.url)
            yield response.follow(next_url, callback=self.parse, method="POST")

    def parse_content(self, response):
        loader = ItemLoader(Tv1GeItem(), selector=response)
        loader.add_xpath("date", "//div[@class='article-date']/text()")
        loader.add_xpath("title", "//div[contains(@class, 'article-title')]/text()")
        loader.add_value("content_url", response.url)
        loader.add_xpath(
            "content", "//div[contains(@class, 'article-intro')]//p//text()"
        )
        loader.add_value("source", "tv1ge")
        date = loader.get_collected_values("date")
        if isinstance(date, list):
            self.date = date[0]
            if (date[0] >= self.start_date) and (date[0] < self.end_date):
                yield loader.load_item()
