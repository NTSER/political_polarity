import os
import yaml
from datetime import datetime


class ScrapeConfig:
    def __init__(self):
        with open(
            os.path.join(os.path.dirname(__file__), "scrape_config.yaml"),
            "r",
        ) as yaml_file:
            self.config = yaml.safe_load(yaml_file)
        self.config["start_date"] = datetime.strptime(
            self.config["start_date"], "%d-%m-%Y"
        )
        self.config["end_date"] = datetime.strptime(self.config["end_date"], "%d-%m-%Y")

    def get_config(self):
        return self.config
