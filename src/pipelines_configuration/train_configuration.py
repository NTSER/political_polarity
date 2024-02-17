import os
import yaml


class TrainConfig:
    def __init__(self):
        with open(
            os.path.join(os.path.dirname(__file__), "train_config.yaml"),
            "r",
        ) as yaml_file:
            self.config = yaml.safe_load(yaml_file)

    def get_config(self):
        return self.config
