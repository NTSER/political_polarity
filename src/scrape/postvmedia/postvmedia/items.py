import scrapy
from itemloaders.processors import TakeFirst, MapCompose, Join
from datetime import datetime, timedelta


def parse_date(date_string):
    date = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S%z")
    date = date.replace(tzinfo=None)
    date = date + timedelta(hours=4)
    return date


def join_and_strip(values):
    joined_values = Join()(values)
    stripped_values = joined_values.strip()
    return stripped_values


class PostvmediaItem(scrapy.Item):
    date = scrapy.Field(
        input_processor=MapCompose(parse_date), output_processor=TakeFirst()
    )
    title = scrapy.Field(
        input_processor=MapCompose(str.strip), output_processor=TakeFirst()
    )
    content_url = scrapy.Field(output_processor=TakeFirst())
    content = scrapy.Field(
        input_processor=MapCompose(str.strip), output_processor=join_and_strip
    )
    source = scrapy.Field(output_processor=TakeFirst())
