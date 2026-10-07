import pandas as pd

# Создаем данные о дверях/кабинетах для коридора 53 метра (107 точек с шагом 0.5м)
doors_data = [
    {"door_name": "Аудитория 101", "Y": 2.0},
    {"door_name": "Аудитория 102", "Y": 5.5},
    {"door_name": "Аудитория 103", "Y": 9.0},
    {"door_name": "Аудитория 104", "Y": 12.5},
    {"door_name": "Преподавательская 105", "Y": 16.0},
    {"door_name": "Лаборатория 106", "Y": 20.0},
    {"door_name": "Аудитория 107", "Y": 24.5},
    {"door_name": "Аудитория 108", "Y": 28.0},
    {"door_name": "Компьютерный класс 109", "Y": 32.5},
    {"door_name": "Аудитория 110", "Y": 37.0},
    {"door_name": "Лекционный зал 111", "Y": 41.5},
    {"door_name": "Деканат 112", "Y": 46.0},
    {"door_name": "Аудитория 113", "Y": 51.5},
]

df_doors = pd.DataFrame(doors_data)
df_doors.to_csv("data/doors.csv", index=False, encoding="utf-8")