import os
import re

from datetime import datetime
from urllib.request import urlopen
from urllib.error import URLError
from json import loads


def get_reports() -> None:
    tasks_json, users_json = get_data_dict()
    create_reports(users_json, tasks_json)


def get_data_dict() -> (dict, dict):
    try:
        return loads(urlopen("https://json.medrating.org/todos").read().decode()), \
               loads(urlopen("https://json.medrating.org/users").read().decode())
    except URLError:
        print("URLError при попытке получить JSON")
    except:
        print("Ошибка  при попытке получить JSON")

    try_again_que()


def create_reports(users_json, tasks_json) -> None:
    # объеденение словарей для большего удобства и скорости работы алгоритма
    add_tasks_in_user_dict(tasks_json, users_json)

    change_directory()

    for user in users_json:
        create_report(user)


def create_report(user) -> None:
    # получение кортежей задач пользователея
    tasks = get_user_tasks(user["tasks"])
    # Создание выходной информации
    output = get_output(user, *tasks)

    # получении имени пользователя для создания имени файла-отчета
    user_firstname = get_user_firstname(user["name"])
    user_report_name = f'{user_firstname}.txt'

    try:
        if os.path.isfile(user_report_name):
            # Переименование старого отчета
            older_report_new_name = get_new_file_name(user_firstname)
            rename_report(user_firstname, older_report_new_name)

        # создание нового
        write_report(user_firstname, output)

    except RepeatFileError:
        file_to_remove_name = get_new_file_name(user_firstname)
        print("был создан второй отчет с тем же именем, в том числе датой и временем до минуты \n"
              f"Файл {file_to_remove_name}.txt Будет удален\n"
              f"Удалить файл и создать новый отчет - y | Выход - n? | empty for pass")
        answer = input()
        if answer == "y" or answer == "yes":
            os.remove(f"{file_to_remove_name}.txt")
            create_report(user)
        elif answer == "n" or answer == "no":
            exit()
        else:
            pass

    except DamagedFileError:
        current_datetime = format_datetime_for_file_system(get_current_time_str())
        damaged_file_name = f"_Error_{user_firstname}_Error_Datetime_{current_datetime}"
        print(f"Файл несоответствует шаблону или был поврежден\n{user_firstname} -> {damaged_file_name}")
        rename_report(user_firstname, damaged_file_name)
        create_report(user)

    except Exception as e:
        # переименование отчета к старому имени в случае ошибок, чтобы актуальный отчет был без даты
        rename_report(get_new_file_name(user_firstname), user_firstname)
        print(e)
        raise Exception


def get_user_tasks(tasks: list) -> (dict, dict):
    """
    Преобразует входной список задач, в кортеж из двух словарей - completed, uncompleted.
    Каждая задача начинается с новой строки.
    """
    completed = {
        "tasks": "",
        "count": 0,
    }
    uncompleted = {
        "tasks": "",
        "count": 0,
    }

    for task in tasks:
        if len(task["title"]) > 48:
            task["title"] = task["title"][0:48] + '...'
        if task["completed"]:
            completed["tasks"] += task["title"] + '\n'
            completed["count"] += 1
        else:
            uncompleted["tasks"] += task["title"] + '\n'
            uncompleted["count"] += 1

    return completed, uncompleted


def get_current_time_str() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def format_datetime_for_file_system(date_time_str:str) -> str:
    return f'{date_time_str[6:10]}' \
           f'-{date_time_str[3:5]}-' \
           f'{date_time_str[0:2]}T' \
           f'{date_time_str[11:13]}：' \
           f'{date_time_str[14:16]}'


def get_output(user: dict, completed_tasks: dict, uncompleted_tasks: dict) -> str:
    """Преобразует полученную информацию из словарей в выходную строку, которая будет записана в файл"""
    current_time = get_current_time_str()
    output = f'Отчет для {user["company"]["name"]}.\n' \
             f'{user["name"]}<{user["email"]}> {current_time}\n' \
             f'Всего задач: {completed_tasks["count"] + uncompleted_tasks["count"]}\n' \
             f'\n'

    if completed_tasks["count"] < 0 and uncompleted_tasks["count"] < 0:
        output += f'У {user["name"]} нет завершенных или активных задач'
    else:
        if completed_tasks["count"] > 0:
            output += f'Завершенные задачи ({completed_tasks["count"]}):\n{completed_tasks["tasks"]}\n'
        if uncompleted_tasks["count"] > 0:
            output += f'Оставшиеся задачи ({uncompleted_tasks["count"]}):\n{uncompleted_tasks["tasks"]}'
    return output


def add_tasks_in_user_dict(tasks_json: dict, users_json: dict) -> None:
    """Добавляет в словарь пользователя ключ tasks, значением которого будут задачи данного пользователя"""
    for task in tasks_json:
        try:
            if "tasks" not in users_json[task["userId"] - 1]:
                users_json[task["userId"] - 1]["tasks"] = []
            users_json[task["userId"] - 1]["tasks"].append(task)
        except KeyError:
            print(f"empty task {task}\n")


def change_directory() -> None:
    """Проверка наличия директории "tasks"/создание -> переход в директорию"""
    if not os.path.isdir("tasks"):
        os.mkdir("tasks")
    os.chdir("tasks")


def get_user_firstname(fullname: str) -> str:
    """Получение имени из полного имени, с проверкой на наличие 'Mr' и 'Mrs'"""
    fullname_as_list = fullname.split()
    firstname = fullname_as_list[0]
    if ('mr' or 'mrs') in fullname_as_list[0].lower():
        firstname += fullname_as_list[1]
    return firstname


def write_report(user_firstname, output) -> None:
    try:
        with open(f'{user_firstname}.txt', "w") as f:
            f.write(output)
    except OSError:
        print("Ошибка при попытка записи в отчет по user_firstname", user_firstname)


def get_file_second_line(file_name) -> str:
    with open(f'{file_name}.txt', "r") as f:
        return f.readlines()[1]


def get_new_file_name(file_name: str) -> str:
    datetime_created = get_file_second_line(file_name)[-17: -1: 1]
    if re.fullmatch(r'\d\d.\d\d.\d{4} \d\d:\d\d', datetime_created):
        return f'old_{file_name}_{format_datetime_for_file_system(datetime_created)}'
    else:
        raise DamagedFileError


def rename_report(file_name: str, new_filename: str) -> None:
    try:
        os.rename(f'{file_name}.txt', f'{new_filename}.txt')
    except FileExistsError:
        raise RepeatFileError


class RepeatFileError(Exception):
    pass


class DamagedFileError(Exception):
    pass


def try_again_que() -> None:
    print("Попробовать снова?  y / n")
    answer = input()
    if answer == "y" or answer == "yes":
        get_reports()
    else:
        exit()


if __name__ == '__main__':
    try:
        get_reports()
        print("Отчеты составлены")
    except Exception as e:
        print(e)
        print("Необработанная ошибка")
        try_again_que()

    print("Нажмите Enter для выхода")
    input()
