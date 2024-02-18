import os
import pathlib

from scrapy.crawler import CrawlerProcess
from pipelines_configuration.scrape_configuration import ScrapeConfig
from scrape.formulanewsge.formulanewsge.spiders.formula import FormulaSpider
from scrape.imedinewsge.imedinewsge.spiders.imedi import ImediSpider
from scrape.mtavaritv.mtavaritv.spiders.mtavari import MtavariSpider
from scrape.tv1ge.tv1ge.spiders.tv1 import Tv1Spider
from scrape.tvpirvelige.scraper import NewsScraperSpider
from scrape.rustavi2ge.rustavi2ge.spiders.rustavi2 import Rustavi2Spider
from scrape.postvmedia.postvmedia.spiders.postv import PostvSpider


def main():
    config = ScrapeConfig().get_config()
    assert (
        sum(config["scrape_spiders"].values()) == 1
    ), "You can scrape only one website on one run"
    # TODO implement scrpaing multiple spiders in one pipeline

    if config["scrape_spiders"]["formula"]:
        Scraper(FormulaSpider, "formula").scrape()
    if config["scrape_spiders"]["imedi"]:
        Scraper(ImediSpider, "imedi").scrape()
    if config["scrape_spiders"]["mtavari"]:
        Scraper(MtavariSpider, "mtavari").scrape()
    if config["scrape_spiders"]["tv1"]:
        Scraper(Tv1Spider, "tv1").scrape()
    if config["scrape_spiders"]["tvpirveli"]:
        NewsScraperSpider().scrape_tvpirveli()
    if config["scrape_spiders"]["rustavi2"]:
        Scraper(Rustavi2Spider, "rustavi2").scrape()
    if config["scrape_spiders"]["postvmedia"]:
        Scraper(PostvSpider, "postvmedia").scrape()


class Scraper:
    def __init__(self, spider, web_name):
        self.config = ScrapeConfig().get_config()
        self.spider = spider
        self.web_name = web_name
        self.filename = "{}_{}".format(
            self.config["start_date"].date(), self.config["end_date"].date()
        )
        self.data_path = os.path.join(
            pathlib.Path(__file__).parents[1], "data", "scraped_data", self.filename
        )
        os.makedirs(self.data_path, exist_ok=True)
        self.check_data_existence()

        self.settings = {
            "FEEDS": {
                f"data/scraped_data/{self.filename}/{web_name}.json": {
                    "format": "json",
                    "encoding": "utf8",
                    "overwrite": True,
                    "indent": 4,
                },
            },
            f"LOG_FILE": f"data/scraped_data/{self.filename}/{web_name}.log",
            "LOG_LEVEL": "INFO",
            "LOG_FILE_APPEND": False,
            "RETRY_ENABLED": True,
            "DOWNLOAD_FAIL_ON_DATALOSS": False,
            "RETRY_TIMES": 100,
            "REQUEST_FINGERPRINTER_IMPLEMENTATION": "2.7",
            "TWISTED_REACTOR": "twisted.internet.asyncioreactor.AsyncioSelectorReactor",
            "DOWNLOAD_DELAY": 0.5,
            "COOKIES_ENABLED": False,
            "ROBOTSTXT_OBEY": False,
            "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        }

    def check_data_existence(self):
        if os.path.exists(os.path.join(self.data_path, f"{self.web_name}.json")):
            raise Exception(
                f"Please make sure you want to delete {self.web_name}.json and remove manually"
            )
        if os.path.exists(os.path.join(self.data_path, f"{self.web_name}.log")):
            raise Exception(
                f"Please make sure you want to delete {self.web_name}.log and remove manually"
            )

    def scrape(self):
        process = CrawlerProcess(settings=self.settings)
        process.crawl(self.spider)
        process.start()


if __name__ == "__main__":
    main()
