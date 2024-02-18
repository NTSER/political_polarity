import pathlib
import os
import sys
import json
import scrapy
from scrapy.loader import ItemLoader
from ..items import PostvmediaItem

sys.path.append(os.path.join(pathlib.Path(__file__).parents[4]))

from pipelines_configuration.scrape_configuration import ScrapeConfig


class PostvSpider(scrapy.Spider):
    name = "postv"
    allowed_domains = ["postv.media"]
    config = ScrapeConfig().get_config()
    start_date = config["start_date"]
    end_date = config["end_date"]
    page_num = 1
    exceeded_start_date = False

    @staticmethod
    def get_query(page_num):
        return {
            "action": "td_ajax_block",
            "td_block_id": "tdi_41",
            "td_column_number": "3",
            "td_current_page": str(page_num),
            "block_type": "td_block_4",
            "td_magic_token": "c536fd573f",
        }

    def start_requests(self):
        yield scrapy.FormRequest(
            url="https://postv.media/wp-admin/admin-ajax.php?td_theme_name=Newspaper&v=12.6.3",
            method="POST",
            formdata=self.get_query(page_num=self.page_num),
            callback=self.parse,
        )

    def parse(self, response):
        selector_text = json.loads(response.body)["td_data"]
        if (selector_text != "") and not self.exceeded_start_date:
            selector = scrapy.Selector(text=selector_text)
            urls = selector.xpath("//h3/a/@href").getall()
            for url in urls:
                yield scrapy.Request(url, callback=self.parse_content)

            # pagination
            self.page_num += 1
            yield scrapy.FormRequest(
                url="https://postv.media/wp-admin/admin-ajax.php?td_theme_name=Newspaper&v=12.6.3",
                method="POST",
                formdata=self.get_query(page_num=self.page_num),
                callback=self.parse,
            )

    def parse_content(self, response):
        loader = ItemLoader(PostvmediaItem(), selector=response)
        loader.add_xpath("date", "//header//span[@class='td-post-date']/time/@datetime")
        loader.add_xpath("title", "//h1[@class='entry-title']/text()")
        loader.add_value("content_url", response.url)
        loader.add_xpath(
            "content", "//div[@class='td-post-content tagdiv-type']//p//text()"
        )
        loader.add_value("source", "postvmedia")
        date = loader.get_collected_values("date")
        if isinstance(date, list) and (len(date) > 0):
            if (
                (date[0] >= self.start_date)
                and (date[0] < self.end_date)
                and (
                    response.xpath(
                        "//ul[@class='td-category']/li/a[text()='პოლიტიკა']"
                    ).get()
                    is not None
                )
            ):
                yield loader.load_item()
            elif date[0] < self.start_date:
                self.exceeded_start_date = True
