import os
import sys
import pathlib

from itertools import combinations
from datetime import timedelta
from datetime import datetime

import pandas as pd
import numpy as np

import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from matplotlib.animation import FuncAnimation, FFMpegWriter
import matplotlib.image as mpimg

from pipelines_configuration.derive_index_configuration import DeriveIndexConfig


def main():
    config = DeriveIndexConfig().get_config()
    polarity_obj = PolarityIndex()
    polarity_df = polarity_obj.get_polarity()
    polarity_obj.save_index(polarity_df)
    if config["save_animation"]:
        polarity_obj.save_animation()


class PolarityIndex:
    def __init__(self):
        self.config = DeriveIndexConfig().get_config()
        time_str = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
        data_path = os.path.join(pathlib.Path(__file__).parents[1], "data")
        self.vectorized_data_path = os.path.join(
            data_path, "vectorized_data", self.config["filename"]
        )
        vecs = np.load(os.path.join(self.vectorized_data_path, "vectors.npy"))
        df = pd.read_parquet(os.path.join(self.vectorized_data_path, "data.parquet"))
        self.media_counts = df["source"].value_counts()
        vecs = (vecs - vecs.mean(axis=0)) / vecs.std(axis=0)
        df["vecs"] = vecs.tolist()
        df["vecs"] = df["vecs"].apply(lambda x: np.array(x))
        df["date"] = pd.to_datetime(df["date"])

        self.df = df
        self.period_length = self.config["period_length"]
        self.ewma1 = min(self.config["ewma"])
        self.ewma2 = max(self.config["ewma"])
        self.gov_media = ["imedinewsge", "tv1ge", "postvmedia", "rustavi2ge"]
        self.opp_media = ["tvpirvelige", "formulanewsge", "mtavaritv"]
        self.combs = list(combinations(self.gov_media + self.opp_media, 2))
        self.within_combs = list(combinations(self.gov_media, 2)) + list(
            combinations(self.opp_media, 2)
        )
        self.between_combs = list(set(self.combs) - set(self.within_combs))
        logos_path = os.path.join(pathlib.Path(__file__).parents[0], "logos")
        self.source_to_logo = {
            "imedinewsge": mpimg.imread(os.path.join(logos_path, "imedinews.png")),
            "postvmedia": mpimg.imread(os.path.join(logos_path, "postv.png")),
            "tv1ge": mpimg.imread(os.path.join(logos_path, "1tv.jpg")),
            "rustavi2ge": mpimg.imread(os.path.join(logos_path, "rustavi2.png")),
            "formulanewsge": mpimg.imread(os.path.join(logos_path, "formulanews.png")),
            "mtavaritv": mpimg.imread(os.path.join(logos_path, "mtavari.png")),
            "tvpirvelige": mpimg.imread(os.path.join(logos_path, "tvpirveli.png")),
        }
        self.index_path = os.path.join(data_path, "index", time_str)
        os.makedirs(self.index_path, exist_ok=True)

    def get_representative_vectors(self):
        repr_vecs = (
            self.df.groupby([pd.Grouper(freq=self.period_length, key="date"), "source"])
            .agg({"vecs": "mean"})
            .reset_index()
            .rename({"vecs": "repr_vecs"}, axis=1)
        )
        return repr_vecs

    def get_media_weights(self, ratings_path="data/ratings.xlsx"):
        def explode_row(row):
            new_df = pd.DataFrame(columns=["date", "comb", "weight_i_j"])
            for n_days in range(7):  # 7 days in week
                for media_i, media_j in self.combs:
                    new_row = pd.DataFrame([[None] * 3], columns=new_df.columns)
                    new_row["date"] = row["week"] + timedelta(days=n_days)
                    new_row["comb"] = [[media_i, media_j]]
                    new_row["weight_i_j"] = row[media_i] * row[media_j]

                    new_df = pd.concat([new_df, new_row])
            return new_df

        ratings = pd.read_excel(ratings_path, parse_dates=["week"])
        final_df = pd.DataFrame()
        for index, row in ratings.iterrows():
            new_df = explode_row(row)
            final_df = pd.concat([final_df, new_df])
            final_df["comb"] = final_df["comb"].apply(tuple)
        return final_df

    def get_D(self):
        def cosine_dissimilarity(vec1, vec2):
            cosine_dis = 1 - np.dot(vec1, vec2) / (
                np.linalg.norm(vec1) * np.linalg.norm(vec2)
            )
            return cosine_dis / 2

        D_df = pd.DataFrame(columns=["date", "comb", "D"])
        repr_vecs = self.get_representative_vectors()

        for date in repr_vecs["date"].unique():
            for comb in self.combs:
                temp = repr_vecs[
                    (repr_vecs["date"] == date) & (repr_vecs["source"].isin(comb))
                ]
                if temp.shape[0] == 2:  # If we have statistics for both media sources
                    D = cosine_dissimilarity(
                        temp["repr_vecs"].iloc[0], temp["repr_vecs"].iloc[1]
                    )
                    new_row = pd.DataFrame({"date": date, "comb": [comb], "D": D})
                    D_df = pd.concat([D_df, new_row])
        D_df = D_df.reset_index(drop=True)

        return D_df

    def get_L(self, D_df=None):
        if D_df is None:
            D_df = self.get_D()

        L_df = (
            D_df[D_df["comb"].isin(self.within_combs)]
            .groupby("date")
            .agg({"D": "mean"})
            .reset_index()
            .rename({"D": "L"}, axis=1)
        )

        return L_df

    def get_B(self, D_df=None, L_df=None):
        if D_df is None:
            D_df = self.get_D()
        if L_df is None:
            L_df = (
                D_df[D_df["comb"].isin(self.within_combs)]
                .groupby("date")
                .agg({"D": "mean"})
                .reset_index()
                .rename({"D": "L"}, axis=1)
            )

        B_df = D_df.merge(L_df, how="left", on="date")
        B_df["B"] = B_df["D"] - B_df["L"]
        B_df.loc[B_df["comb"].isin(self.within_combs), "B"] = 0
        B_df = B_df.reset_index(drop=True)

        return B_df

    def get_polarity(self, B_df=None):
        if B_df is None:
            B_df = self.get_B()

        weights_df = self.get_media_weights()

        B_df = B_df.merge(weights_df, how="left", on=["date", "comb"])
        B_df["weight_i_j"] = B_df.groupby("date", group_keys=False)["weight_i_j"].apply(
            lambda x: x / x.sum()
        )
        B_df["polarity"] = B_df["B"] * B_df["weight_i_j"]
        B_df["cluster"] = (
            B_df["comb"]
            .isin(self.between_combs)
            .map({True: "Between", False: "Within"})
        )

        return B_df

    @staticmethod
    def normalize_column(col):
        """
        Normalize the values of a column between 0 and 1.
        """
        return (col - col.min()) / (col.max() - col.min())

    def save_index(self, polarity_df):
        agg_polarity = polarity_df.groupby("date").agg({"polarity": "sum"})
        agg_polarity["polarity"] = PolarityIndex.normalize_column(
            agg_polarity["polarity"]
        )
        agg_polarity[f"polarity_ewma{self.ewma1}"] = (
            agg_polarity["polarity"].ewm(alpha=self.ewma1).mean()
        )
        agg_polarity[f"polarity_ewma{self.ewma2}"] = (
            agg_polarity["polarity"].ewm(alpha=self.ewma2).mean()
        )
        fig, ax = plt.subplots(figsize=[15, 5])

        sns.lineplot(
            data=agg_polarity,
            x="date",
            y=f"polarity_ewma{self.ewma1}",
            ax=ax,
            label=f"α = {self.ewma1}",
            alpha=1,
            c="blue",
        )
        sns.lineplot(
            data=agg_polarity,
            x="date",
            y=f"polarity_ewma{self.ewma2}",
            ax=ax,
            label=f"α = {self.ewma2}",
            alpha=0.5,
            c="grey",
        )

        unique_years = pd.Series(agg_polarity.index).dt.year.unique().tolist()
        unique_years = unique_years + [max(unique_years) + 1]
        for year in unique_years:
            ax.plot(
                [datetime(year, 1, 1), datetime(year, 1, 1)],
                [
                    agg_polarity["polarity_ewma0.25"].min(),
                    agg_polarity["polarity_ewma0.25"].max(),
                ],
                c="r",
                lw=1,
                linestyle="--",
                alpha=1,
            )
            ax.annotate(year, xy=(datetime(year, 6, 2), 0.7), fontsize=16)
        x_ticks = [
            date for date in agg_polarity.index if date.day == 1 and date.month % 2 == 0
        ]
        ax.set_xticks(x_ticks)
        ax.set_xticklabels(
            [date.strftime("%b") for date in x_ticks], rotation=45, fontsize=8
        )
        ax.legend(fontsize=14, loc="lower right")
        ax.grid(True, linestyle="--")
        ax.tick_params(axis="y", labelsize=12)
        ax.set_xlabel("Months", fontsize=14)
        ax.set_ylabel("Exponentially Weighted Average", fontsize=14)
        ax.set_title("Polarity Over Time", fontsize=20, fontweight="bold")

        # Save
        plt.savefig(
            os.path.join(
                self.index_path,
                f"polarity_index.png",
            )
        )
        agg_polarity = agg_polarity.reset_index()
        agg_polarity["date"] = agg_polarity["date"].dt.date
        agg_polarity.to_excel(
            os.path.join(self.index_path, "polarity_index.xlsx"), index=False
        )
        self.media_counts.to_excel(
            os.path.join(self.index_path, "news_quantities.xlsx")
        )

    def reduce_daily_dimension(self):
        pca = PCA(n_components=2, random_state=7)
        repr_vecs = (
            self.df.groupby([pd.Grouper(freq="1d", key="date"), "source"])
            .agg({"vecs": "mean"})
            .reset_index()
        )
        repr_vecs[["x", "y"]] = pca.fit_transform(np.vstack(repr_vecs["vecs"].values))
        repr_vecs[["x_ewma", "y_ewma"]] = repr_vecs.groupby("source", group_keys=False)[
            ["x", "y"]
        ].apply(lambda x: x.ewm(alpha=0.05).mean())
        return repr_vecs

    def save_animation(self, file_name="animation.mp4", im_size=0.4):
        repr_vecs = self.reduce_daily_dimension()
        repr_vecs = repr_vecs.dropna()
        unique_dates = repr_vecs["date"].unique()
        num_iterations = unique_dates.shape[0]
        fig, ax = plt.subplots()

        def annimate(i):
            if i >= num_iterations:
                return

            date = unique_dates[i]
            filtered = repr_vecs[repr_vecs["date"] == date]

            ax.cla()
            ax.scatter(filtered["x_ewma"], filtered["y_ewma"], alpha=0)
            ax.grid(True, linestyle="--", alpha=0.5)
            ax.set_xlim([-3, 3])
            ax.set_ylim([-2, 2])
            ax.set_yticks([-2, -1, 0, 1, 2])
            ax.set_title(date.astype(str)[0:10], fontsize=20, fontweight="bold")
            for j in range(filtered.shape[0]):
                current_img = self.source_to_logo.get(filtered["source"].iloc[j])
                img_y, img_x = current_img.shape[0:2]
                img_y, img_x = img_y / (img_y + img_x), img_x / (img_y + img_x)
                ax.imshow(
                    current_img,
                    extent=[
                        filtered["x_ewma"].iloc[j] - im_size * img_x,
                        filtered["x_ewma"].iloc[j] + im_size * img_x,
                        filtered["y_ewma"].iloc[j] - im_size * img_y,
                        filtered["y_ewma"].iloc[j] + im_size * img_y,
                    ],
                )
            for x, y in zip(filtered["x_ewma"], filtered["y_ewma"]):
                ax.arrow(0, 0, x * 0.7, y * 0.7, width=0.03, color="black")

            ax.scatter(0, 0, color="red", marker="o", edgecolor="black", s=140)

        animation = FuncAnimation(fig, annimate, interval=200, frames=num_iterations)
        writer = FFMpegWriter(fps=15)
        plt.rcParams["animation.ffmpeg_path"] = r"C:\ffmpeg\bin\ffmpeg.exe"
        animation.save(os.path.join(self.index_path, file_name), writer=writer)


if __name__ == "__main__":
    main()
