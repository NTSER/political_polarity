import pathlib
import os
import sys
import scrapy
from scrapy.loader import ItemLoader

from ..utils import URLS, get_next_url, content_from_quote
from ..items import FormulanewsgeItem

sys.path.append(os.path.join(pathlib.Path(__file__).parents[4]))

from pipelines_configuration.scrape_configuration import ScrapeConfig


class FormulaSpider(scrapy.Spider):
    name = "formula"
    allowed_domains = ["formulanews.ge"]
    start_urls = URLS
    config = ScrapeConfig().get_config()
    start_date = config["start_date"]
    end_date = config["end_date"]
    date = end_date

    def parse(self, response):
        items = response.xpath("//div[@class='col-lg-3 news__box__card']")
        for item in items:
            url = item.xpath(
                ".//div[contains(@class,'date')]/following-sibling::a/@href"
            ).get()
            is_quote = item.xpath("./div[@class='main__phrases__box']")

            if is_quote:
                yield response.follow(url=url, callback=self.parse_quote)
            else:
                yield response.follow(url=url, callback=self.parse_content)

        next_page_exist = response.xpath("//body/*")
        if next_page_exist and self.date >= self.start_date:
            next_url = get_next_url(response.url)
            yield response.follow(next_url, callback=self.parse)

    def parse_content(self, response):
        loader = ItemLoader(
            item=FormulanewsgeItem(), selector=response, response=response
        )
        loader.add_xpath("date", "//*[@class='news__inner__images_created']")
        loader.add_xpath("title", "//*[@class='news__inner__desc__title']/text()")
        loader.add_value("content_url", response.url)
        loader.add_xpath("content", "//section[@class='article-content']//text()")
        loader.add_value("source", "formulanewsge")
        date = loader.get_collected_values("date")
        if isinstance(date, list):
            self.date = date[0]
            if (date[0] >= self.start_date) and (date[0] < self.end_date):
                yield loader.load_item()

    def parse_quote(self, response):
        loader = ItemLoader(
            item=FormulanewsgeItem(), selector=response, response=response
        )
        loader.add_xpath("date", "//div[@class='phrase-date']")
        loader.add_xpath("title", "//div[@class='phrase-title']/text()")
        loader.add_value("content_url", response.url)

        quote = response.xpath("//div[@id='phrase-main']//text()").getall()
        quote_description = response.xpath(
            "//div[@class='phrase-text'][2]//text()"
        ).getall()

        content = content_from_quote(quote, quote_description)
        loader.add_value("content", content)
        loader.add_value("source", "formulanewsge")
        date = loader.get_collected_values("date")
        if isinstance(date, list):
            self.date = date[0]
            if (date[0] >= self.start_date) and (date[0] < self.end_date):
                yield loader.load_item()
