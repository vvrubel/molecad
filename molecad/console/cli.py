import pathlib
from typing import Any, Dict, List

import click
import pymongo
import pymongo.errors
import rdkit.RDLogger
from loguru import logger
from mongordkit import Search

from molecad.console.cli_db import (
    connect_mongodb,
    create_molecule,
    delete_broken,
    drop_db,
    upload_data,
)
from molecad.console.downloader import execute_requests
from molecad.console.utils import (
    build_filename,
    check_dir,
    chunked,
    convert_data,
    parse_first_and_last,
    read_json,
    write_json,
)
from molecad.settings import Settings
from molecad.utils import timer

rdkit.RDLogger.DisableLog("rdApp.*")


@click.group(
    help="Консольная утилита для извлечения информации о свойствах молекул с серверов Pubchem, "
    "сохранения полученной информации в файлы формата JSON и загрузки содержимого файлов в "
    "локальную базу данных.",
    invoke_without_command=True,
)
@click.option(
    "--setup",
    type=click.Choice(["PROD", "DEV"], case_sensitive=False),
    help="Опция позволяет выбирать конфигурационный файл, содержащий переменные окружения и "
    "настройки базы данных.",
)
@click.option(
    "--debug/--no-debug", default=False, help="Флаг для включения/отключения режима отладки."
)
@click.pass_context
def molecad(ctx: click.Context, setup: str):
    if setup == "PROD":
        ctx.obj = Settings(_env_file=".env.prod", _env_file_encoding="utf-8")
    else:
        ctx.obj = Settings()

    logger.debug(f"Команда запущена с контекстом {ctx.obj.env}.")
    logger.info(f"Выбрана база {ctx.obj.db_name}")


@molecad.command(
    help="Извлекает и сохраняет информацию из базы данных Pubchem – 'Compound'. "
    "Для совершения запроса к серверу необходимо уточнить диапазон идентификаторов "
    "интересуемых соединений - 'CID'. Данные извлекаются путем отправления запроса на "
    "сгенерированный URL. Из-за ограничения на количество символов в строке URL, "
    "отправка запроса, включающего все желаемые идентификаторы, может привести к ошибке, "
    "поэтому рекомендуется использовать опцию `--size`, которая по умолчанию равна `100`. "
    "Полученные данные сохраняются в файл, причем имеется возможность сохранять файл "
    "порциями до окончания работы программы, указав в качестве опции `--f-size` желаемое "
    "количество идентификаторов в сохраняемом файле, которое по умолчанию равна `1000`. "
)
@click.option("--start", required=True, type=int, help="Первое значение из запрашиваемых CID.")
@click.option("--stop", required=True, type=int, help="Последнее значение из запрашиваемых CID.")
@click.option(
    "--size",
    default=100,
    show_default=True,
    type=int,
    help="Максимальное число идентификаторов в одном запросе, по умолчанию равно 100.",
)
@click.option(
    "--f-size",
    default=1000,
    show_default=True,
    type=int,
    help="Максимальное число идентификаторов в сохраняемом файле, по умолчанию равно 1000.",
)
@click.pass_obj
@timer
def fetch(obj: Settings, start: int, stop: int, size: int, f_size: int) -> None:
    fetch_dir = pathlib.Path(obj.fetch_dir)
    new_dir: pathlib.Path = check_dir(fetch_dir, start, stop)
    logger.info(f"Файлы будут сохранены в директорию {new_dir}")
    data = execute_requests(start, stop + 1, size)
    chunks = chunked(data, f_size)
    for chunk in chunks:
        first, last = parse_first_and_last(chunk)
        logger.debug(f"Сохраняю данные для CID: {first} – {last}")
        file: pathlib.Path = build_filename(new_dir, first, last)
        write_json(file, chunk)


@molecad.command(
    help='При использовании команды "db.collection.insert_many({...})" имеется ограничение на '
    "максимально допустимое количество добавляемых документов за один раз равное 100000. "
    "Данная функция служит для того, чтобы разрезать JSON-файлы, превышающие указанное выше "
    "ограничение, на файлы меньшего размера."
)
@click.option(
    "--file",
    required=True,
    type=pathlib.Path,
    help="Файл не подходящий под критерии загрузки файлов в MongoDB.",
)
@click.option(
    "--f-size",
    default=1000,
    show_default=True,
    type=int,
    help="Максимальное число идентификаторов в сохраняемом файле, по умолчанию равно 1000.",
)
@click.pass_obj
@timer
def split(obj: Settings, file: pathlib.Path, f_size: int) -> None:
    split_dir = pathlib.Path(obj.split_dir)
    data: List[Dict[str, Any]] = convert_data(read_json(file))
    logger.debug(f"Открываю файл {file}")
    start, stop = parse_first_and_last(data)
    new_dir: pathlib.Path = check_dir(split_dir, start, stop)
    for i, chunk in enumerate(chunked(data, f_size), start=1):
        first, last = parse_first_and_last(chunk)
        chunk_path: pathlib.Path = build_filename(new_dir, first, last)
        write_json(chunk_path, chunk)
        logger.info(f"Записываю в файл {chunk_path}")


@molecad.command(
    help="Из указанной директории загружает файлы в коллекцию MongoDB. Количество документов в "
    "файле не должно превышать 100000, иначе данный файл будет пропущен при загрузке. При "
    'указании опции "--drop" удаляет все коллекции в базе, после чего создает их заново и '
    'устанавливает уникальный индекс "CID" и индекс "index" на коллекциях "properties" и '
    '"molecules". '
)
@click.option(
    "--f-dir",
    required=True,
    type=pathlib.Path,
    help="Путь до директории, содержащей chunked-файлы, каждый из которых представляет собой "
    "список длиной до 100000 элементов.",
)
@click.option(
    "--drop",
    is_flag=True,
    help='Если опция "--drop" указана, то база будет очищена.',
)
@click.pass_obj
@timer
def populate(obj: Settings, f_dir: pathlib.Path, drop: bool) -> None:
    db = connect_mongodb(obj.mongo_uri)[obj.db_name]
    if drop:
        drop_db(db)
    properties, molecules, mfp_counts = obj.get_collections()

    total, succeed, failed, created = (0 for _ in range(4))
    logger.info(f"Произвожу импорт из папки {f_dir}", fg="yellow")
    for file in f_dir.glob("./**/*.json"):
        try:
            logger.debug(f"Импортирую файл {file}")
            data: List[Dict[str, Any]] = convert_data(read_json(file))
            total += len(data)
            data, c = create_molecule(data, molecules)
            created += c
            s, f = upload_data(data, properties)
            succeed += s
            failed += f
        except pymongo.errors.BulkWriteError as e:
            click.secho(e, fg="red")
            continue
        except pymongo.errors.DuplicateKeyError as e:
            click.secho(e, fg="red")
            continue
    deleted = delete_broken(properties)
    click.secho(
        f"Выбрана база данных: {obj.db_name}\n"
        f"Коллекция представлений молекул: {molecules.name}\n"
        f"Создано схем: {created}\n"
        f"Коллекция свойств молекул: {properties.name}\n"
        f"Общее количество обработанных документов: {total}\n"
        f"Новых документов: {succeed},\n"
        f"Пропущено дубликатов: {failed},\n"
        f"Удалено документов без SMILES: {deleted[0]},\n"
        f"Удалено документов без схемы: {deleted[1]}",
        fg="green",
    )

    click.secho("Начинаю генерировать Fingerprints", fg="yellow")
    Search.AddPatternFingerprints(molecules)
    click.secho("Команда AddPatternFingerprints выполнена.", fg="bright_blue")
    Search.AddMorganFingerprints(molecules, mfp_counts)
    click.secho("Команда AddMorganFingerprints выполнена.", fg="bright_blue")


molecad.add_command(fetch)
molecad.add_command(split)
molecad.add_command(populate)


if __name__ == "__main__":
    molecad()
