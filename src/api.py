import logging

import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Список идентификаторов вакансий
employer_ids = [
    1375441,
    1455,
    11435141,
    561525,
    3892566,
    5756945,
    10745593,
    3551949,
    4905190,
    3131901,
]


def get_employer_data(employer_id: int) -> tuple[dict, dict]:
    """
    Получает данные о работодателе и его вакансиях по идентификатору работодателя.

    :param employer_id: Идентификатор работодателя.
    :return: Кортеж, содержащий информацию о работодателе и список вакансий:
             - employer_data (dict): Данные о работодателе или None, если не найден.
             - vacancy_data (dict): Данные о вакансиях или None, если они не найдены.
    """
    employer_url = f"https://api.hh.ru/employers/{employer_id}"
    vacancy_url = f"https://api.hh.ru/vacancies?employer_id={employer_id}"

    try:
        # Получение информации о работодателе
        employer_response = requests.get(employer_url, timeout=10)
        if employer_response.status_code == 404:
            logging.error(f"Работодатель с ID {employer_id} не найден.")
            return None, None
        employer_response.raise_for_status()  # Проверка на другие ошибки
        employer_data = employer_response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при получении данных о работодателе {employer_id}: {e}")
        return None, None

    try:
        # Получение вакансий работодателя
        vacancy_response = requests.get(vacancy_url, timeout=10)
        if vacancy_response.status_code == 404:
            logging.error(f"Вакансии для работодателя с ID {employer_id} не найдены.")
            return employer_data, None
        vacancy_response.raise_for_status()  # Проверка на другие ошибки
        vacancy_data = vacancy_response.json()
    except requests.exceptions.RequestException as e:
        logging.error(
            f"Ошибка при получении вакансий для работодателя {employer_id}: {e}"
        )
        return employer_data, None

    return employer_data, vacancy_data


def main() -> None:
    """
    Главная функция для извлечения и отображения данных о работодателях и их вакансиях.

    Проходит по списку идентификаторов работодателей, получает данные о каждом
    работодателе и выводит информацию о найденных вакансиях. Если данные не найдены,
    выводится сообщение об ошибке.

    :return: None
    """
    for employer_id in employer_ids:
        employer_data, vacancy_data = get_employer_data(employer_id)
        if employer_data and vacancy_data:
            logging.info(f"Работодатель: {employer_data['name']}")
            logging.info("Вакансии:")
            for vacancy in vacancy_data["items"]:
                salary = vacancy.get("salary")

                if salary is not None:
                    salary_from = salary.get("from")
                    salary_to = salary.get("to")
                    currency = salary.get("currency", "не указана")

                    # Определяем, как выводить информацию о зарплате
                    if salary_from is None and salary_to is not None:
                        logging.info(f"- {vacancy['name']} (Зарплата: до {salary_to} {currency})")
                    elif salary_to is None and salary_from is not None:
                        logging.info(f"- {vacancy['name']} (Зарплата: от {salary_from} {currency})")
                    elif salary_from is not None and salary_to is not None:
                        logging.info(f"- {vacancy['name']} (Зарплата: от {salary_from} до {salary_to} {currency})")
                    else:
                        logging.info(f"- {vacancy['name']} (Зарплата: не указана)")
                else:
                    logging.info(f"Вакансия '{vacancy['name']}' не имеет информации о зарплате.")


if __name__ == "__main__":
    main()