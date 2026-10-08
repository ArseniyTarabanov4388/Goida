import os
import re
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd


class DataLoader:
    # Шаг между точками замеров в метрах (0.5 м)
    SAMPLE_STEP_METERS = 0.5

    @classmethod
    def extract_y_from_filename(cls, filename: str) -> Optional[float]:

        stem = Path(filename).stem.strip()


        match = re.search(r"\d+", stem)
        if match:
            point_number = int(match.group(0))
            y_meters = (point_number - 1) * cls.SAMPLE_STEP_METERS
            return y_meters

        return None

    @classmethod
    def generate_summary_csv(
        cls,
        data_dir: str | Path,
        output_filename: str = "processed_magnetic_summary.csv",
    ) -> pd.DataFrame:

        path = Path(data_dir).resolve()
        print(f"[DataLoader] Поиск CSV-файлов в папке: {path}")

        if not path.exists():
            raise FileNotFoundError(f"Папка с данными не найдена по пути: {path}")


        csv_files = sorted(list(path.glob("*.csv")))
        csv_files = [f for f in csv_files if f.name != output_filename]

        if not csv_files:
            raise FileNotFoundError(
                f"В папке {path} не найдено CSV-файлов замеров (вида 1.csv, 2.csv)."
            )

        print(f"[DataLoader] Найдено файлов для обработки: {len(csv_files)} шт.")

        results = []

        for file_path in csv_files:
            y_coord = cls.extract_y_from_filename(file_path.name)
            if y_coord is None:
                print(f"[DataLoader] Пропущен файл (нет числа в имени): {file_path.name}")
                continue

            df = cls._read_csv_robust(file_path)
            if df is None:
                print(f"[DataLoader] Ошибка чтения/пустой файл: {file_path.name}")
                continue


            rename_map = {}
            for col in df.columns:
                c = col.strip().lower()
                if c == "bx":
                    rename_map[col] = "Bx"
                elif c == "by":
                    rename_map[col] = "By"
                elif c == "bz":
                    rename_map[col] = "Bz"
                elif c in ["bt", "b", "b_module"]:
                    rename_map[col] = "BT"

            df.rename(columns=rename_map, inplace=True)

            if not all(col in df.columns for col in ["Bx", "By", "Bz"]):
                print(f"[DataLoader] В файле {file_path.name} отсутствуют колонки Bx, By, Bz.")
                continue


            for col in ["Bx", "By", "Bz", "BT"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(
                        df[col].astype(str).str.replace(",", "."), errors="coerce"
                    )

            df.dropna(subset=["Bx", "By", "Bz"], inplace=True)


            calc_bt = np.sqrt(df["Bx"] ** 2 + df["By"] ** 2 + df["Bz"] ** 2)
            if "BT" not in df.columns:
                df["BT"] = calc_bt
            else:
                df["BT"] = df["BT"].fillna(calc_bt)


            point_num = int(re.search(r"\d+", Path(file_path).stem).group(0))

            results.append(
                {
                    "point_num": point_num,
                    "file_name": file_path.name,
                    "Y": y_coord,
                    "Bx_mean": round(df["Bx"].mean(), 2),
                    "By_mean": round(df["By"].mean(), 2),
                    "Bz_mean": round(df["Bz"].mean(), 2),
                    "BT_mean": round(df["BT"].mean(), 2),
                }
            )

        if not results:
            raise ValueError("Не удалось успешно обработать ни один CSV-файл.")


        summary_df = pd.DataFrame(results)
        summary_df.sort_values(by="point_num", inplace=True)
        summary_df.reset_index(drop=True, inplace=True)


        output_path = path / output_filename
        summary_df.to_csv(output_path, index=False, encoding="utf-8-sig")

        print("\n" + "=" * 60)
        print(f"[УСПЕХ] Итоговый файл сохранен: {output_path}")
        print("=" * 60)

        return summary_df

    @staticmethod
    def _read_csv_robust(file_path: Path) -> Optional[pd.DataFrame]:

        separators = [",", ";", "\t"]
        encodings = ["utf-8", "utf-8-sig", "cp1251"]

        for enc in encodings:
            for sep in separators:
                try:
                    df = pd.read_csv(file_path, sep=sep, encoding=enc, decimal=",")
                    df.columns = df.columns.str.strip()
                    cols_lower = [c.lower() for c in df.columns]
                    if any(b in cols_lower for b in ["bx", "by", "bz"]):
                        return df
                except Exception:
                    continue
        return None



CURRENT_FILE_DIR = Path(__file__).resolve().parent



PATH_OPTION_1 = CURRENT_FILE_DIR / "data"

PATH_OPTION_2 = CURRENT_FILE_DIR.parent / "data"

if PATH_OPTION_1.exists():
    TARGET_DATA_DIR = PATH_OPTION_1
elif PATH_OPTION_2.exists():
    TARGET_DATA_DIR = PATH_OPTION_2
else:

    TARGET_DATA_DIR = PATH_OPTION_1

print(f"[START] Запуск скрипта DataLoader...")
print(f"[INFO] Целевая директория: {TARGET_DATA_DIR.resolve()}\n")

try:
    df_result = DataLoader.generate_summary_csv(
        data_dir=TARGET_DATA_DIR,
        output_filename="processed_magnetic_summary.csv",
    )

    print("\nПервые 5 усредненных точек:")
    print(df_result[["point_num", "file_name", "Y", "Bx_mean", "By_mean", "Bz_mean", "BT_mean"]].to_string())

except Exception as err:
    print(f"\n[ОШИБКА ВЫПОЛНЕНИЯ]: {err}")