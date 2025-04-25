import sys
from typing import Callable, Dict

from api import employer_ids, get_employer_data
from database import DBManager

COMMANDS: Dict[str, tuple[str, Callable]] = {}


def register_as_command(number: str, description: str):
    """
    Декоратор для регистрации команды.

    :param number: Номер команды, который будет использоваться для её вызова.
    :param description: Описание команды, которое будет отображаться пользователю.
    :return: Функция-декоратор, которая регистрирует команду.
    """

    def decorator(func):
        COMMANDS[number] = (description, func)
        return func

    return decorator


@register_as_command("1", "Создать базу данных и таблицы")
def create_database_command(db_manager: DBManager) -> None:
    """
    Создает базу данных и таблицы, если они не существуют.

    :param db_manager: Экземпляр DBManager для управления базой данных.
    :return: None
    """
    db_manager.create_database_if_not_exists()  # Создание базы данных, если она не существует
    db_manager.create_tables()  # Метод для создания таблиц должен быть реализован


@register_as_command("2", "Заполнить таблицу организаций")
def fill_organizations_command(db_manager: DBManager) -> None:
    """
    Заполняет таблицу организаций данными из API.

    :param db_manager: Экземпляр DBManager для управления базой данных.
    :return: None
    """
    for employer_id in employer_ids:
        employer_data, _ = get_employer_data(employer_id)
        if employer_data:
            try:
                db_manager.cursor.execute(
                    """
                    INSERT INTO companies (id, name, vacancies_count) VALUES (%s, %s, 0) ON CONFLICT (id) DO NOTHING;
                    """,
                    (employer_data["id"], employer_data["name"]),
                )
            except Exception as e:
                print(f"Ошибка при добавлении организации {employer_data['name']}: {e}")
    db_manager.connection.commit()
    print("Таблица организаций заполнена.")


@register_as_command("3", "Заполнить таблицу вакансий")
def fill_vacancies_command(db_manager: DBManager) -> None:
    """
    Заполняет таблицу вакансий данными из API.

    :param db_manager: Экземпляр DBManager для управления базой данных.
    :return: None
    """
    for employer_id in employer_ids:
        employer_data, vacancy_data = get_employer_data(employer_id)
        if vacancy_data:
            for vacancy in vacancy_data["items"]:
                try:
                    # Проверяем наличие необходимых полей
                    if "name" in vacancy and "url" in vacancy:
                        # Получаем данные о зарплате
                        salary = vacancy.get("salary")
                        print(f"Данные вакансии: {vacancy}")  # Переместили сюда

                        if salary is not None:
                            salary_from = salary.get("from")
                            salary_to = salary.get("to")
                            salary_currency = salary.get("currency", "не указана")
                            print(f"Полученная зарплата: от {salary_from} до {salary_to} {salary_currency}")
                        else:
                            salary_from = None
                            salary_to = None
                            salary_currency = "не указана"
                            print(f"Нет данных о зарплате для вакансии {vacancy['name']}.")

                        # Используем salary_from и salary_to для вычисления средней зарплаты
                        avg_salary = salary_from if salary_from is not None else (
                            salary_to if salary_to is not None else 0)

                        db_manager.cursor.execute(
                            """
                            INSERT INTO vacancies (title, company_id, salary, url) VALUES (%s, %s, %s, %s) RETURNING id;
                            """,
                            (vacancy["name"], employer_id, avg_salary, vacancy["url"]),
                        )
                        vacancy_id = db_manager.cursor.fetchone()[0]
                        db_manager.cursor.execute(
                            """
                            UPDATE companies SET vacancies_count = vacancies_count + 1 WHERE id = %s;
                            """,
                            (employer_id,),
                        )
                    else:
                        print(f"Недостаточно данных для вакансии: {vacancy}")
                except Exception as e:
                    print(
                        f"Ошибка при добавлении вакансии {vacancy['name']} для работодателя {employer_id}: {e}"
                    )
    db_manager.connection.commit()
    print("Таблица вакансий заполнена.")


@register_as_command("4", "Вывести список всех компаний и количество вакансий")
def list_companies_and_vacancies_command(db_manager: DBManager) -> None:
    """
    Выводит список всех компаний и количество вакансий для каждой компании.

    :param db_manager: Экземпляр DBManager для управления базой данных.
    :return: None
    """
    try:
        companies = db_manager.get_companies_and_vacancies_count()
        print("\nСписок компаний и количество вакансий:")
        for name, vacancies_count in companies:
            print(f"Компания: {name}, Количество вакансий: {vacancies_count}")
    except Exception as e:
        print(f"Ошибка при получении списка компаний: {e}")


@register_as_command("5", "Вывести список всех вакансий")
def list_vacancies_command(db_manager: DBManager) -> None:
    """
    Выводит список всех вакансий из базы данных.

    :param db_manager: Экземпляр DBManager для управления базой данных.
    :return: None
    """
    try:
        vacancies = db_manager.get_all_vacancies()
        print("\nСписок всех вакансий:")
        for vacancy in vacancies:
            print(
                f"Компания: {vacancy[0]}, Название: {vacancy[1]}, Зарплата: {vacancy[2]}, URL: {vacancy[3]}"
            )
    except Exception as e:
        print(f"Ошибка при получении списка вакансий: {e}")


@register_as_command("6", "Вывести среднюю зарплату")
def average_salary_command(db_manager: DBManager) -> None:
    """
    Выводит среднюю зарплату по всем вакансиям.

    :param db_manager: Экземпляр DBManager для управления базой данных.
    :return: None
    """
    try:
        avg_salary = db_manager.get_avg_salary()
        if avg_salary is not None:
            print(f"\nСредняя зарплата: {avg_salary}")
        else:
            print("\nСредняя зарплата не может быть рассчитана (все значения зарплаты отсутствуют).")
    except Exception as e:
        print(f"Ошибка при получении средней зарплаты: {e}")

@register_as_command("7", "Вывести вакансии с зарплатой выше средней")
def higher_salary_command(db_manager: DBManager) -> None:
    """
    Выводит список вакансий с зарплатой выше средней.

    :param db_manager: Экземпляр DBManager для управления базой данных.
    :return: None
    """
    try:
        vacancies = db_manager.get_vacancies_with_higher_salary()
        if vacancies:
            print("\nВакансии с зарплатой выше средней:")
            for vacancy in vacancies:
                salary = vacancy[2] if vacancy[2] is not None else "не указана"
                print(
                    f"Компания: {vacancy[0]}, Название: {vacancy[1]}, Зарплата: {salary}, URL: {vacancy[3]}"
                )
        else:
            print("\nНет вакансий с зарплатой выше средней.")
    except Exception as e:
        print(f"Ошибка при получении вакансий с зарплатой выше средней: {e}")


@register_as_command("8", "Вывести вакансии по ключевому слову")
def keyword_vacancies_command(db_manager: DBManager) -> None:
    """
    Выводит список вакансий, соответствующих заданному ключевому слову.

    :param db_manager: Экземпляр DBManager для управления базой данных.
    :return: None
    """
    keyword = input("Введите ключевое слово для поиска вакансий: ")
    try:
        vacancies = db_manager.get_vacancies_with_keyword(keyword)
        print(f"\nВакансии с ключевым словом '{keyword}':")
        for vacancy in vacancies:
            print(
                f"Компания: {vacancy[0]}, Название: {vacancy[1]}, Зарплата: {vacancy[2]}, URL: {vacancy[3]}"
            )
    except Exception as e:
        print(f"Ошибка при получении вакансий по ключевому слову: {e}")


@register_as_command("0", "Выйти")
def exit_program(db_manager: DBManager) -> None:
    """
    Закрывает соединение с базой данных и завершает программу.

    :param db_manager: Экземпляр DBManager для управления базой данных.
    :return: None
    """
    db_manager.close()
    print("До свидания")
    sys.exit(0)


def main():
    db_manager = DBManager()  # Создание экземпляра DBManager
    try:
        while True:
            print("\nВыберите команду:")
            for number, (description, _) in COMMANDS.items():
                print(f"{number}: {description}")

            choice = input("Введите номер команды: ")
            command = COMMANDS.get(choice)

            if command:
                description, func = command
                func(db_manager)
            else:
                print("Некорректный выбор. Пожалуйста, повторите.")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    finally:
        db_manager.close()  # Закрытие соединения с базой данных


if __name__ == "__main__":
    main()