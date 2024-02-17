import os
import pathlib
import re
from datetime import datetime
from itertools import product

import pandas as pd
import numpy as np

from gensim.models.doc2vec import Doc2Vec, TaggedDocument
from gensim.models.callbacks import CallbackAny2Vec

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split
from pipelines_configuration.train_configuration import TrainConfig


def main():
    config = TrainConfig().get_config()
    trainer = Trainer()
    trainer.create_corpus()
    trainer.train_test_split()
    if not config["hyperparameter_tuning"]["enabled"]:
        trainer.train(config["default_params"])
        trainer.save_model()
    else:
        trainer.hyperparameter_tuning()

    


class EarlyStopException(Exception):
    pass


class EarlyStoppingCallback(CallbackAny2Vec):
    def __init__(self, train_idx, test_idx, y_train, y_test, patience=5):
        self.train_idx = train_idx
        self.test_idx = test_idx
        self.y_train = y_train
        self.y_test = y_test

        self.patience = patience
        self.current_f1_score = 0
        self.best_f1_score = 0
        self.counter = 0

    def on_epoch_end(self, model):
        self.current_f1_score = Trainer.evaluate(
            model, self.train_idx, self.test_idx, self.y_train, self.y_test
        )

        if self.current_f1_score > self.best_f1_score:
            self.best_f1_score = self.current_f1_score
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.patience:
                print("Early stopping triggered. Training stopped.")
                raise EarlyStopException()


class Trainer:
    def __init__(self):
        self.config = TrainConfig().get_config()
        time_str = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
        data_path = os.path.join(pathlib.Path(__file__).parents[1], "data")
        self.scraped_data_path = os.path.join(data_path, "scraped_data")
        self.model_data_path = os.path.join(
            data_path,
            "models",
            "{}_{}".format(self.config["model_name"], time_str),
        )
        os.makedirs(self.model_data_path)
        self.df = pd.concat(
            [
                self.read_files(folder.path)
                for folder in os.scandir(self.scraped_data_path)
            ]
        )

    @staticmethod
    def read_files(folder_path):
        df = pd.DataFrame()
        for file in os.scandir(folder_path):
            basename = os.path.basename(file.path)
            file_extension = os.path.splitext(basename)[1]
            # TODO implement code which doesnt read files indicated in yaml
            if file_extension == ".json":
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

    @staticmethod
    def tag_documents(list_of_documents):
        for i, list_of_words in enumerate(list_of_documents):
            yield TaggedDocument(list_of_words, [i])

    @staticmethod
    def evaluate(model, train_idx, test_idx, y_train, y_test):
        logit = LogisticRegression(max_iter=100000)
        X_train = model.dv.vectors[train_idx]
        X_test = model.dv.vectors[test_idx]
        logit.fit(X_train, y_train)
        pred = logit.predict(X_test)
        return f1_score(y_test, pred, average="macro")

    def create_corpus(self):
        self.df['content'] = self.df['content'].apply(self.preprocess_document)
        self.df = self.df.dropna(subset=['content'])
        self.corpus = list(self.tag_documents(self.df['content']))

    def train_test_split(self):
        self.train_df, self.test_df = train_test_split(
            self.df, test_size=0.03, random_state=7, stratify=self.df["source"]
        )
        self.y_train = self.train_df["source"]
        self.y_test = self.test_df["source"]

    def train(self, params):
        self.model = Doc2Vec(**params)
        self.model.build_vocab(self.corpus)
        self.earlyStoppingCallback = EarlyStoppingCallback(
            self.train_df.index, self.test_df.index, self.y_train, self.y_test
        )

        try:
            self.model.train(
                self.corpus,
                total_examples=self.model.corpus_count,
                epochs=1000,  # It should never reach to 1000, early stopping should stop till that.
                callbacks=[self.earlyStoppingCallback],
            )

        except EarlyStopException:
            pass

    def hyperparameter_tuning(self):
        param_space = self.config["hyperparameter_tuning"]["params"]
        combinations = list(product(*param_space.values()))
        scores = {}
        for i, comb in enumerate(combinations):
            current_params = {k: v for k, v in zip(param_space.keys(), comb)}
            self.train(current_params)
            new_score = self.earlyStoppingCallback.best_f1_score
            scores[i] = new_score
            print(scores)
            if all([new_score > score for score in list(scores.values())[:-1]]):
                self.save_model()
                print('Saved best model')
            


    def save_model(self):
        self.model.save(os.path.join(self.model_data_path, "model.model"))


if __name__ == "__main__":
    main()
