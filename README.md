# molecad

API для извлечения информации из баз данных Pubchem и дальнейшего взаимодействия с этими данными.

## Содержание

* [Документация на Confluence](#документация-на-confluence)
* [Настройка виртуального окружения](#настройка-виртуального-окружения)
* [Настройка переменных окружения](#настройка-переменных-окружения)
* [Как развернуть MongoDB локально на macOS](#как-развернуть-mongodb-локально-на-macos)
* [Скрипт для скачивания молекул с Pubchem и их загрузки в MongoDB](#cкрипт-для-скачивания-молекул-с-pubchem-и-их-загрузки-в-mongodb)  
* [Использование mongo-rdkit для подструктурного поиска по базе](#использование-mongo-rdkit-для-подструктурного-поиска-по-базе)
* [Схема базы данных](#схема-базы-данных)
* [Документация ручек API](#документация-ручек-api)
* [Структура проекта](#структура-проекта)


## Документация на Confluence

* [Как развернуть MongoDB локально на macOS](https://confluence.biocad.ru/x/3BhQCw)
* [Что можно скачать из баз данных PubChem](https://confluence.biocad.ru/x/DwpQCw)
* [Как использовать molecad для скачивания данных из Pubchem](https://confluence.biocad.ru/x/_ixQCw)
* [Описание ручек api](https://confluence.biocad.ru/x/jCxQCw)


## Настройка виртуального окружения

> Перед тем как приступить к настройке виртуального окружения, убедитесь, что на вашем компьютере 
> установлены [pyenv](https://github.com/pyenv/pyenv-installer) и [poetry](https://python-poetry.org/docs/), 
> причем их пути должны быть добавлены в `PATH`.

Склонируйте [репозиторий](https://github.com/vvrubel/molecad) и запустите shell из директории, 
содержащей файл `pyproject.toml`.

В проекте используется Python версии 3.7.10, который вы можете установить, используя `pyenv`:

```shell
$ pyenv install 3.7.10
$ pyenv local 3.7.10
```

Создать виртуальное окружение и установить все зависимости проекта можно с помощью `poetry`:

```shell
$ poetry install
```

Вуаля! Все зависимости проекта установлены и никакой конды, вам не потребовалось.  
Подробнее о реализации пути через `conda` можно почитать [тут](https://confluence.biocad.ru/x/vi1QCw).


## Настройка переменных окружения

После настройки виртуальной среды, необходимо задать переменные окружения – это параметры для 
настройки api, подключения к mongodb, запуска скрипта, выполняющего запросы к базам данных Pubchem.  
Удобнее всего установить их один раз, создав файл `.env` из шаблона `.env.sample`. 

В корневой директории найдите файл `.env.sample`, скопируйте его, заполните недостающие поля и 
переименуйте в `.env`.

Переменные окружения в файле `.env` могут быть двух типов: имеющие значение по умолчанию и нет. 
Переменные не имеющие значений по умолчанию обязательны к первоначальной настройке.

Переменная|Описание, `значение по умолчанию` 
---|---
MONGO_HOST|Хост базы данных MongoDB; по умолчанию -> `"127.0.0.1"`  
MONGO_PORT|Порт базы данных MongoDB; по умолчанию -> `27017`  
MONGO_USER|Имя пользователя базы данных MongoDB  
MONGO_PASSWORD|Пароль пользователя базы данных MongoDB  
MONGO_DB_NAME|Название базы данных, к которой будет подключаться пользователь; по умолчанию -> `"molecad"`  
MONGO_DB_COLLECTION|Название коллекции, в которой хранятся данные о свойствах молекул из базы данных `Compound`, скачанные с серверов Pubchem; по умолчанию -> `"mol_props"` 
PROJ_DIR|Путь до корневой директории проекта, если значение не определено, то будет использоваться текущая директория; по умолчанию -> `.`
FETCH_DIR|Шаблон именования пути до директорий для сохранения файлов, полученных от серверов Pubchem с помощью команды `fetch`; по умолчанию -> `./downloads/fetch`
SPLIT_DIR|Шаблон именования пути до директорий для сохранения файлов, полученных в результате выполнения команды `split` над json-файлами; по умолчанию -> `./downloads/split`
JSON|Путь, по которому расположен json-файл, который необходимо передать в качестве аргумента при вызове команды `split`. 

Этот файл был записан в  являющийся аргументом при команде `split` необходимый для запуска команды  качестве опции 


условия, которым должен удовлетворять файл:файл был получен в результате выполнения команды `fetch`, а его содержимое можно аннотировать типом `List[Dict[str, Any]]`, причем число элементов в списке должно быть больше 100000 
и имеет структуру списка, элементами которого являются словари длиною не более 100000 элементов (количество документов, которое можно загрузить с помощью команды `db.collection.insert_many({..})`). Для загрузки данных из этого файла в базу с помощью команды `populate` его необходимо предварительно разделить с помощью команды `split` на несколько меньших по размеру файлов, каждый из которых будет содержать в себе не более 100000 документов.







## Как развернуть MongoDB локально на macOS

Установите на свой компьютер сервер MongoDB: Community Server можно поставить с помощью 
менеджера пакетов для macOS - `brew`, а Enterprise Server - из архива `.targz`. Добавьте путь до 
исполняемого файла в `PATH`.  
Ниже описаны основные шаги разворачивания локальной базы на примере 
Enterprise Server. Детальное описание процесса установки и инстукции для Community Server можно 
найти по [ссылке](https://confluence.biocad.ru/x/3BhQCw).

Переходим в каталог с только что установленным сервером MongoDB и создаем в нем подкаталог для 
локальной базы, после чего запустим сервер.

```shell
$ mkdir -p ./data/db
$ mongod --dbpath ./data/db
```

После того как сервер запущен, становится возможным подключение к локальной базе данных. При 
первом запуске базы необходимо создать пользователей.  
Пример кода для создания суперпользователя: 

```shell
$ mongo
MongoDB Enterprise> use admin
MongoDB Enterprise> db.createUser({ user: "superuser", pwd: "<pwd>", roles: [ "root" ] })
```

После того как пользователь будет создан, нужно выключить сервер, выйти в исходный shell.

```shell
MongoDB Enterprise> db.shutdownServer()
MongoDB Enterprise> exit
```

Теперь перезапускаем сервер mongod, но с параметром `--auth` для подключения по логину-паролю. 
Готово! Теперь вы можете подключаться к своей локальной базе данных, используя креды:

```shell
$ mongod --dbpath ./data/db --auth
$ mongo mongodb://superuser:<password>@127.0.0.1:27017/admin
```

## Скрипт для скачивания молекул с Pubchem и их загрузки в MongoDB

Перейдите в корневую директорию проекта, содержащую файл `.env` и запустите в ней shell, 
в котором исполните файл `./molecad/data/console/script.example.sh`, 
если вас устраивают заданные параметры.
Данный скрипт запустит файл `./molecad/data/console/__main__.py`, который представляет собой 
утилиту для извлечения информации с серверов Pubchem и ее записи в файл 
или в локальную базу данных с помощью интерфейса командной строки.  

Если вы хотите применить настройки из файла `.env`, введите в консоль команду:
```shell
source .env
```  

Справка по работе утилиты:

```shell
$ poetry run python -m molecad.data.console __main__ --help                      

Usage: python -m molecad.data.console [OPTIONS] COMMAND [ARGS]...

  Утилита для извлечения информации с серверов Pubchem и ее записи в файлы или
  в локальную базу данных с помощью интерфейса командной строки.

Options:
  --help  Show this message and exit.

Commands:
  fetch     Выполняет запрос к серверу Pubchem, извлекает данные из...
  populate  Загружает chunked-файлы из указанной директории в локальную...
  split     Разрезает большой JSON на чанки меньшего размера для...
```

Справка по команде `fetch`:  
```shell
$ poetry run python -m molecad.data.console fetch --help                                                                                                        
Usage: python -m molecad.data.console fetch [OPTIONS]

  Выполняет запрос к серверу Pubchem, извлекает данные из ответа сервера и
  пишет их в файл

Options:
  --out-dir PATH   Путь до output-директории, в которую будет записан JSON-
                   файл. Не должна существовать на момент создания файла.  [required]
  --start INTEGER  Первое значение из запрашиваемых CID  [required]
  --stop INTEGER   Последнее значение из запрашиваемых CID  [required]
  --size INTEGER   Максимальное число идентификаторов в одном запросе
                   [required]
  --help           Show this message and exit.
```

В результате выполнения команды `fetch` будет создан JSON-файл в директории `out_dir`; 
содержимое файла представляет собой список из словарей.  

при скачивании данных с серверов Pubchem с помощью команды `fetch` из консольной утилиты, программа не ждет пока выполнятся все запросы для того, чтобы сохранить файл, а сохраняет результаты по мере выполнения (количество идентификаторов указывается при вызове команды)

Так как MongoDB имеет ограничение на количество создаваемых документов при разовой загрузке в базу 
из файла, то дальнейший план будет определяться длинной списка, который находится в этом файле. 
Если длина списка (число запрошенных идентификаторов) < 100000, то этот файл можно сразу загрузить 
в локальную базу данных MongoDB, используя команду `populate`. Иначе перед загрузкой потребуется 
его разделение на chunked-файлы меньшего размера с помощью команды `split`, например по 1000 
идентификаторов в файле.


Справка по команде `split`:

```shell
$ poetry run python -m molecad.data.console split --help

Usage: python -m molecad.data.console split [OPTIONS]

  Разрезает большой JSON на чанки меньшего размера для последующей загрузки в
  MongoDB, что необходимо из-за внутренних ограничений MongoDB на количество
  документов, загружаемых за один раз одним файлом.

Options:
  --file PATH     Путь до большого JSON-файла  [required]
  --f-dir PATH    Путь до директории, в которую будут записаны созданные
                  chunked-файлы – не должна существовать до начала выполнения записи файлов 
                  [required]
  --size INTEGER  Максимальное число элементов в одном chunked-файле
  --help          Show this message and exit.

```

Справка по команде `populate`:

```shell
$ poetry run python -m molecad.data.console populate --help                                                                                                   
Usage: python -m molecad.data.console populate [OPTIONS]

  Загружает chunked-файлы из указанной директории в локальную базу MongoDB.

Options:
  --f-dir PATH       Путь до директории, содержащей chunked-файлы, содержимое
                     каждого из которых представляет собой список, длинной до
                     100000 элементов - ограничение MongoDB  [required]
  --collection TEXT  Название коллекции MongoDB, в которую будут загружены
                     файлы.  [required]
  --help             Show this message and exit.
                                                  
```

## Использование mongo-rdkit для подструктурного поиска по базе

Исторически сложилось, что `mongo-rdkit` и просто `rdkit` используют виртуальное окружение 
`conda` для разрешения своих зависимостей.  Но в данном проекте было решено реализовать 
управление зависимостями этих библиотек с использованием `poetry`.  
Если вы хотите использовать окружение конды и вам хочется узнать, как установить `conda` рядом с 
`pyenv` наиболее безболезненно – читайте [тут](https://confluence.biocad.ru/x/vi1QCw).

## Схема базы данных


## Документация ручек API