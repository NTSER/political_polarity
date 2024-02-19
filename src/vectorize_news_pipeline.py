import os
import pathlib
import re
from datetime import datetime

import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
import seaborn as sns

from gensim.models.doc2vec import Doc2Vec
from pipelines_configuration.vectorize_configuration import VectorizeConfig

from tqdm import tqdm

tqdm.pandas()
sns.set_style("whitegrid")


def main():
    vectorizer = Vectorizer()
    vectorizer.check_data()
    vectorizer.process_df()
    vectorizer.vectorize()
    vectorizer.save()


class Vectorizer:
    def __init__(self):
        config = VectorizeConfig().get_config()
        time_str = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
        data_path = os.path.join(pathlib.Path(__file__).parents[1], "data")
        self.vectorized_data_path = os.path.join(data_path, "vectorized_data", time_str)
        self.scraped_data_path = os.path.join(data_path, "scraped_data")
        self.model_path = os.path.join(
            data_path, "models", config["model_name"], "model.model"
        )
        os.makedirs(self.vectorized_data_path, exist_ok=True)
        self.model = Doc2Vec.load(self.model_path)
        self.df = pd.concat(
            [
                self.read_files(folder.path, config["exclude_files"])
                for folder in os.scandir(self.scraped_data_path)
            ]
        )
        self.df["date"] = pd.to_datetime(self.df["date"])

    def check_data(self):
        fig, ax = plt.subplots(figsize=(18, 7))
        grouped = (
            self.df.groupby([self.df["date"].dt.date, "source"])
            .agg({"title": "count"})
            .reset_index()
            .rename({"title": "counts"}, axis=1)
        )
        sns.lineplot(data=grouped, x="date", y="counts", hue="source", ax=ax)
        plt.savefig(
            os.path.join(self.vectorized_data_path, "news.png"), bbox_inches="tight"
        )
        plt.close()

    @staticmethod
    def read_files(folder_path, exclude_files):
        df = pd.DataFrame()
        for file in os.scandir(folder_path):
            basename = os.path.basename(file.path)
            file_extension = os.path.splitext(basename)[1]
            if basename in exclude_files:
                pass
            elif file_extension == ".json":
                df = pd.concat([df, pd.read_json(file.path)])
            elif file_extension == ".csv":
                df = pd.concat([df, pd.read_csv(file.path)])
            elif file_extension == ".parquet":
                df = pd.concat([df, pd.read_parquet(file.path)])
            elif file_extension == ".log":
                pass
            else:
                raise Exception(f"Unknown file extension: {file_extension}")
        return df

    @staticmethod
    def preprocess_document(text):
        if isinstance(text, str):
            text = re.sub(r"[^ა-ჰ ]", " ", text)
            text = re.sub(r" +", " ", text)
            list_of_words = text.split()
            return list_of_words
        return np.nan

    def process_df(self):
        self.df["content"] = self.df["content"].apply(Vectorizer.preprocess_document)
        self.df = self.df.dropna(subset=["content"])

    def vectorize(self):
        self.vectors = np.vstack(
            self.df["content"].progress_apply(self.model.infer_vector).values
        )

    def save(self):
        np.save(os.path.join(self.vectorized_data_path, "vectors.npy"), self.vectors)
        self.df["date"] = self.df["date"].astype(str)
        self.df.to_parquet(os.path.join(self.vectorized_data_path, "data.parquet"))


if __name__ == "__main__":
    main()
