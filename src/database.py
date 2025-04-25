import configparser
import os

import psycopg2
from psycopg2 import sql


class DBManager:
    def __init__(self):
        """
        Инициализация объекта DBManager.

        Загружает параметры подключения к базе данных из файла
        'database.ini' и устанавливает соединение с PostgreSQL.

        Создает базу данных, если она не существует, и создаёт
        необходимые таблицы в базе данных.

        :raises FileNotFoundError: Если файл 'database.ini' не найден.
        :raises KeyError: Если секция [postgresql] или необходимые параметры отсутствуют в файле конфигурации.
        """
        config = configparser.ConfigParser()

        # Получаем путь к корневой директории проекта
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        # Формируем путь к файлу database.ini
        config_path = os.path.join(root_dir, "database.ini")

        config.read(config_path)

        if "postgresql" not in config:
            print("Секция [postgresql] не найдена в файле database.ini")

        # Получаем параметры подключения из файла
        self.host = config["postgresql"]["host"]
        self.user = config["postgresql"]["user"]
        self.password = config["postgresql"]["password"]
        self.port = config["postgresql"]["port"]
        self.dbname = config["postgresql"]["dbname"]

        # Подключаемся к PostgreSQL без указания базы данных
        self.connection = psycopg2.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
            database="postgres",  # Подключаемся к существующей базе данных
        )
        self.cursor = self.connection.cursor()
        self.create_database_if_not_exists()  # Создаем базу данных, если она не существует
        self.connection.close()  # Закрываем текущее соединение

        # Подключаемся к только что созданной базе данных
        self.connection = psycopg2.connect(
            host=self.host,
            user=self.user,
            password=self.password,
            port=self.port,
            database=self.dbname,
        )
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_database_if_not_exists(self):
        """
        Создает базу данных, если она не существует.

        Закрывает текущее соединение с базой данных, открывает новое соединение
        с сервером PostgreSQL и выполняет команду создания базы данных.

        Если база данных уже существует, выводится соответствующее сообщение.

        :raises Exception: Если возникает ошибка при создании базы данных.
        """
        try:
            # Закрываем текущее соединение, если оно открыто
            if self.connection:
                self.connection.close()

            # Создаем новое соединение с сервером без указания базы данных
            self.connection = psycopg2.connect(
                user=self.user, password=self.password, host=self.host, port=self.port
            )
            self.cursor = self.connection.cursor()

            # Включаем автокоммит
            self.connection.autocommit = True

            # Выполняем команду создания базы данных
            self.cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self.dbname))
            )
            print(f"База данных {self.dbname} успешно создана.")
        except psycopg2.errors.DuplicateDatabase:
            print(f"База данных {self.dbname} уже существует.")
        except Exception as e:
            print(f"Ошибка при создании базы данных: {e}")
        finally:
            # Закрываем соединение
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()

            # Восстанавливаем соединение с новой базой данных
            self.connection = psycopg2.connect(
                database=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
            )
            self.cursor = self.connection.cursor()

    def create_database(self):
        """
        Создает базу данных с именем, указанным в атрибуте `self.dbname`.

        Этот метод закрывает текущее соединение с базой данных, создает новое соединение к серверу PostgreSQL
        без указания базы данных,
        и выполняет команду создания базы данных. Если база данных с таким именем уже существует, выводится
        соответствующее сообщение.

        :raises psycopg2.errors.DuplicateDatabase: Если база данных с указанным именем уже существует.
        :raises Exception: Если возникает ошибка при создании базы данных.
        """
        try:
            # Закрываем текущее соединение
            self.cursor.close()
            self.connection.close()

            # Создаем новое соединение к PostgreSQL без указания базы данных
            connection = psycopg2.connect(
                host=self.host, user=self.user, password=self.password, port=self.port
            )
            connection.autocommit = True  # Включаем автокоммит

            cursor = connection.cursor()
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(self.dbname))
            )

            # Закрываем новое соединение
            cursor.close()
            connection.close()

            # Восстанавливаем исходное соединение
            self.connection = psycopg2.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                port=self.port,
                database=self.dbname,
            )
            self.cursor = self.connection.cursor()
        except psycopg2.errors.DuplicateDatabase:
            print(f"Database {self.dbname} already exists.")

    def create_tables(self):
        """
        Создает необходимые таблицы в базе данных.

        Этот метод создает таблицы `companies` и `vacancies`, если они еще не существуют.
        Таблица `companies` хранит информацию о компаниях, а таблица `vacancies` - информацию о вакансиях.

        :raises Exception: Если возникает ошибка при создании таблиц.
        """
        # Создание таблицы для организаций
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS companies (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                vacancies_count INTEGER DEFAULT 0
            );
            """
        )

        # Создание таблицы для вакансий
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS vacancies (
                id SERIAL PRIMARY KEY,
                company_id INTEGER REFERENCES companies(id),
                title VARCHAR(255) NOT NULL,
                salary INTEGER NULL,  
                url VARCHAR(255) NOT NULL
            );
            """
        )
        self.connection.commit()

    def close(self):
        """
        Закрывает текущее соединение с базой данных и курсор.

        Этот метод должен вызываться, когда работа с базой данных завершена, чтобы освободить ресурсы.
        """
        self.cursor.close()
        self.connection.close()

    def insert_company(self, name):
        """
        Вставляет новую компанию в таблицу `companies`.

        :param name: Название компании, которое будет добавлено в базу данных.
        :return: ID вставленной компании.
        :raises Exception: Если возникает ошибка при вставке компании.
        """
        self.cursor.execute(
            """
            INSERT INTO companies (name) VALUES (%s) RETURNING id;
            """,
            (name,),
        )
        company_id = self.cursor.fetchone()[0]
        self.connection.commit()  # Сохраняем изменения
        return company_id

    def insert_vacancy(self, company_id, title, salary, url):
        """
        Вставляет новую вакансию в базу данных.

        :param company_id: ID компании, к которой относится вакансия.
        :param title: Название вакансии.
        :param salary: Зарплата, предлагаемая по вакансии. Может быть None.
        :param url: URL-адрес, по которому можно найти подробности о вакансии.
        """
        self.cursor.execute(
            """
            INSERT INTO vacancies (company_id, title, salary, url) VALUES (%s, %s, %s, %s);
            """,
            (company_id, title, salary, url),
        )
        self.connection.commit()

    def get_companies_and_vacancies_count(self):
        """
        Получает список компаний и количество вакансий для каждой компании.

        :return: Список кортежей, где каждый кортеж содержит имя компании и количество вакансий.
        """
        self.cursor.execute(
            """
            SELECT c.name, COUNT(v.id) as vacancies_count
            FROM companies c
            LEFT JOIN vacancies v ON c.id = v.company_id
            GROUP BY c.name;
            """
        )
        return self.cursor.fetchall()

    def get_all_vacancies(self):
        """
        Получает все вакансии с информацией о компании.

        :return: Список кортежей, где каждый кортеж содержит имя компании, название вакансии, зарплату и URL.
        """
        self.cursor.execute(
            """
            SELECT c.name, v.title, v.salary, v.url
            FROM vacancies v
            JOIN companies c ON v.company_id = c.id;
            """
        )
        vacancies = self.cursor.fetchall()
        # Обработка None значений для зарплаты
        return [(name, title, salary if salary is not None else "не указана", url) for name, title, salary, url in
                vacancies]

    def get_avg_salary(self):
        """
        Вычисляет среднюю зарплату по всем вакансиям.

        :return: Средняя зарплата (число) или None, если зарплат нет.
        """
        self.cursor.execute(
            """
            SELECT AVG(salary) FROM vacancies;
            """
        )
        avg_salary = self.cursor.fetchone()[0]
        return avg_salary if avg_salary is not None else 0  # Возвращаем 0, если зарплат нет

    def get_vacancies_with_higher_salary(self):
        """
        Получает вакансии с зарплатой выше средней.

        :return: Список кортежей, где каждый кортеж содержит имя компании, название вакансии, зарплату и URL.
        """
        avg_salary = self.get_avg_salary()
        if avg_salary == 0:  # Если нет зарплат, возвращаем пустой список
            return []

        self.cursor.execute(
            """
            SELECT c.name, v.title, v.salary, v.url
            FROM vacancies v
            JOIN companies c ON v.company_id = c.id
            WHERE v.salary > %s;
            """,
            (avg_salary,),
        )
        vacancies = self.cursor.fetchall()
        # Обработка None значений для зарплаты
        return [(name, title, salary if salary is not None else "не указана", url) for name, title, salary, url in
                vacancies]

    def get_vacancies_with_keyword(self, keyword):
        """
        Получает вакансии, в названии которых содержится заданное ключевое слово.

        :param keyword: Ключевое слово для поиска в названиях вакансий.
        :return: Список кортежей, где каждый кортеж содержит имя компании, название вакансии, зарплату и URL.
        """
        self.cursor.execute(
            """
            SELECT c.name, v.title, v.salary, v.url
            FROM vacancies v
            JOIN companies c ON v.company_id = c.id
            WHERE v.title ILIKE %s;
            """,
            (f"%{keyword}%",),
        )
        return self.cursor.fetchall()