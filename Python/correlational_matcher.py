import os
from pathlib import Path
from typing import Dict, Optional, Tuple, Union
import numpy as np
import pandas as pd


class CorridorMagneticMatcher:
    """Модуль корреляционной пространственной локализации (КЭА)

    на основе 1D-профиля модуля магнитного поля BT вдоль оси Y.
    """

    def __init__(
        self,
        ref_profile: pd.DataFrame,
        doors_map: Dict[str, float],
        step_sample_dist: float = 0.5,
    ):
        """:param ref_profile: DataFrame с колонками 'Y' и 'BT_mean'

        :param doors_map: Словарь дверей вида {'Аудитория 101': 3.5, ...}
        :param step_sample_dist: Шаг пространственной сетки дискретизации (по
        умолчанию 0.5 м)
        """
        self.step_sample_dist = step_sample_dist
        self.doors_map = doors_map

        # Извлекаем координаты Y и модуль магнитного поля BT
        if "Y" not in ref_profile.columns or "BT_mean" not in ref_profile.columns:
            raise KeyError(
                "ref_profile должен содержать столбцы 'Y' и 'BT_mean'!"
            )

        y_raw = ref_profile["Y"].values
        b_raw = ref_profile["BT_mean"].values

        # 1. Построение пространственной сетки y_grid с шагом step_sample_dist
        self.y_min = y_raw.min()
        self.y_max = y_raw.max()
        self.y_grid = np.arange(
            self.y_min, self.y_max + self.step_sample_dist, self.step_sample_dist
        )

        # 2. Интерполяция эталонного профиля на регулярную сетку
        self.b_ref_grid = np.interp(self.y_grid, y_raw, b_raw)

        # 3. Центрирование эталонного сигнала (вычитание постоянной составляющей)
        self.b_ref_centered = self.b_ref_grid - np.mean(self.b_ref_grid)

    def match_segment(
        self,
        measured_bt: np.ndarray,
        estimated_length: float,
    ) -> Tuple[float, float, str, float]:
        """Сопоставляет замеренный отрезок шагов с эталонной картой коридора.

        :param measured_bt: Массив значений BT, записанный во время ходьбы
        :param estimated_length: Оценочная длина пройденного отрезка в метрах
        (из PDR) :return: (Matched_Y_coord, correlation_coefficient,
        nearest_door_name, distance_to_door)
        """
        if len(measured_bt) < 3:
            raise ValueError("Массив измерений слишком короткий!")

        # 1. Приведение замеренного отрезка к регулярному шагу (resampling)
        num_window_points = max(
            3, int(np.round(estimated_length / self.step_sample_dist)) + 1
        )
        meas_indices = np.linspace(0, len(measured_bt) - 1, num_window_points)
        meas_resampled = np.interp(
            meas_indices, np.arange(len(measured_bt)), measured_bt
        )

        # 2. Центрирование замеренного сигнала и расчет нормы
        meas_centered = meas_resampled - np.mean(meas_resampled)
        meas_norm = np.linalg.norm(meas_centered)

        if meas_norm == 0:
            return self.y_min, 0.0, "Неизвестно", 0.0

        win_size = len(meas_resampled)
        num_shifts = len(self.y_grid) - win_size + 1

        if num_shifts <= 0:
            raise ValueError(
                f"Пройденный отрезок ({estimated_length}м) превышает длину эталонного коридора ({self.y_max - self.y_min}м)!"
            )

        best_corr = -1.0
        best_shift_idx = 0

        # 3. Скользящее окно корреляции (КЭА)
        for i in range(num_shifts):
            ref_window = self.b_ref_centered[i : i + win_size]
            ref_win_centered = ref_window - np.mean(ref_window)
            ref_norm = np.linalg.norm(ref_win_centered)

            if ref_norm == 0:
                continue

            # Коэффициент корреляции Пирсона
            corr = np.dot(meas_centered, ref_win_centered) / (
                meas_norm * ref_norm
            )

            if corr > best_corr:
                best_corr = corr
                best_shift_idx = i

        # 4. Вычисление итоговой координаты Y (конец пройденного отрезка)
        matched_y = self.y_grid[best_shift_idx + win_size - 1]

        # 5. Поиск ближайшей двери
        nearest_door, dist_to_door = self.find_nearest_door(matched_y)

        return matched_y, float(best_corr), nearest_door, float(dist_to_door)

    def find_nearest_door(self, current_y: float) -> Tuple[str, float]:
        """Находит ближайшую аудиторию/дверь по заданной координате Y."""
        if not self.doors_map:
            return "Карта дверей пуста", 0.0

        best_door = None
        min_dist = float("inf")

        for door_name, door_y in self.doors_map.items():
            dist = abs(current_y - door_y)
            if dist < min_dist:
                min_dist = dist
                best_door = door_name

        return best_door, min_dist


# =====================================================================
# ЗАПУСК И ПРОВЕРКА РАБОТОСПОСОБНОСТИ
# =====================================================================
if __name__ == "__main__":
    CURRENT_DIR = Path(__file__).resolve().parent

    # Определяем путь к папке data
    DATA_DIR = (
        CURRENT_DIR / "data"
        if (CURRENT_DIR / "data").exists()
        else CURRENT_DIR.parent / "data"
    )

    summary_file = DATA_DIR / "processed_magnetic_summary.csv"
    doors_file = DATA_DIR / "doors.csv"

    print("=== ИНИЦИАЛИЗАЦИЯ И СВЯЗКА МОДУЛЕЙ ===")

    # 1. Проверяем наличие файлов
    if not summary_file.exists():
        raise FileNotFoundError(f"Файл сводки не найден: {summary_file}")
    if not doors_file.exists():
        raise FileNotFoundError(f"Файл дверей не найден: {doors_file}")

    # 2. Загружаем эталонную карту напрямую из CSV и снимаем ограничения на вывод строк
    pd.set_option("display.max_rows", None)
    ref_df = pd.read_csv(summary_file)

    print(
        f"\nЗагружена эталонная карта из {summary_file.name} (Всего точек: {len(ref_df)}):"
    )
    # Выводим ВСЕ точки эталонной карты без .head()
    print(ref_df[["point_num", "file_name", "Y", "BT_mean"]])

    # 3. Загружаем карту дверей из CSV и преобразуем в словарь {door_name: Y}
    doors_df = pd.read_csv(doors_file)
    doors_config = dict(zip(doors_df["door_name"], doors_df["Y"]))

    print(f"\nЗагружена карта дверей (Всего дверей: {len(doors_config)}):")
    # Выводим ВСЕ двери без среза [:3]
    for name, y in doors_config.items():
        print(f"  - {name}: {y} м")

    # 4. Инициализируем коррелятор с шагом 0.5 м
    matcher = CorridorMagneticMatcher(
        ref_profile=ref_df, doors_map=doors_config, step_sample_dist=0.5
    )

    # 5. ЭМУЛЯЦИЯ ЗАМЕРА: Берём участок из эталона (от Y = 3.5 до 6.0 м) с шумом
    sample_segment = ref_df[
        (ref_df["Y"] >= 3.5) & (ref_df["Y"] <= 6.0)
    ]["BT_mean"].values
    noisy_measured_bt = sample_segment + np.random.normal(
        0, 0.3, len(sample_segment)
    )

    # 6. Запуск корреляционного поиска
    matched_y, correlation, door, dist_to_door = matcher.match_segment(
        measured_bt=noisy_measured_bt, estimated_length=2.5
    )

    print("\n=== РЕЗУЛЬТАТ ЛОКАЛИЗАЦИИ ===")
    print(f"Рассчитанная координата Y: {matched_y:.2f} м")
    print(f"Коэффициент корреляции (уверенность): {correlation:.4f}")
    print(f"Ближайшая дверь: {door}")
    print(f"Расстояние до двери: {dist_to_door:.2f} м")