# MCP сервер для поиска информации через DuckDuckGo Search

Этот MCP сервер предоставляет инструменты для поиска информации в интернете с использованием библиотеки DDGS (DuckDuckGo Search).

## Установка

### Требования

- Python 3.8+
- `uv` (https://github.com/astral-sh/uv) - рекомендуется для управления зависимостями
- Или стандартный `pip` и `venv`

### Шаги установки

1.  **Клонируйте репозиторий или создайте папку проекта:**
    ```bash
    mkdir duck_duck_MCP
    cd duck_duck_MCP
    ```

2.  **(Рекомендуется) Создайте виртуальное окружение:**
    ```bash
    # С uv
    uv venv
    # Активируйте (Windows)
    venv\Scripts\activate
    # Активируйте (Linux/macOS)
    source .venv/bin/activate
    ```
    *Примечание: Если вы используете `uv`, он автоматически создаст и активирует `.venv` при первом запуске `uv pip install`.*

3.  **Установите зависимости:**
    ```bash
    # С uv (рекомендуется)
    uv pip install ddgs
    # Или с pip
    pip install ddgs
    ```
    *Примечание: `ddgs` - это библиотека для работы с DuckDuckGo Search.*

## Запуск

Сервер может работать в двух режимах: **STDIO** и **TCP**.

### Режим STDIO

Этот режим используется для прямого взаимодействия через стандартные потоки ввода/вывода. Подходит для запуска из терминала или интеграции с клиентами, которые запускают сервер как дочерний процесс.

1.  **Запустите сервер напрямую:**
    ```bash
    # Если вы в виртуальном окружении
    python ddg_mcp_server.py
    # Или с полным путем к python из venv
    venv\Scripts\python.exe ddg_mcp_server.py
    ```

### Режим TCP

Этот режим запускает сервер как TCP-сервер, прослушивающий указанный порт. Подходит для интеграции с клиентами, которые подключаются по сети.

1.  **Запустите TCP-сервер:**
    ```bash
    # Если вы в виртуальном окружении
    python tcp_ddg_server.py
    # Или с полным путем к python из venv
    venv\Scripts\python.exe tcp_ddg_server.py
    ```

2.  По умолчанию сервер запустится на `127.0.0.1:8765`. Вы увидите сообщение:
    ```
    TCP сервер запущен на 127.0.0.1:8765
    ```

## Поддерживаемые методы MCP

Сервер реализует следующие методы протокола MCP:

- `initialize` - Инициализация сервера
- `tools/list` - Получение списка доступных инструментов
- `tools/call` - Вызов инструмента

## Доступные инструменты

### `get_search_operators`
Получить документацию по операторам поиска DDG

**Параметры:** нет

### `search_text`
Текстовый поиск через DDGS

**Параметры:**
- `query` (обязательный): Поисковый запрос
- `region`: Регион (us-en, uk-en, ru-ru, и т.д.) - по умолчанию "us-en"
- `safesearch`: Уровень фильтрации (on, moderate, off) - по умолчанию "moderate"
- `timelimit`: Ограничение по времени (d, w, m, y)
- `max_results`: Максимальное количество результатов - по умолчанию 10
- `page`: Номер страницы результатов - по умолчанию 1
- `backend`: Поисковые движки (auto, google, bing, и т.д.) - по умолчанию "auto"

### `search_images`
Поиск изображений через DDGS

**Параметры:**
- `query` (обязательный): Поисковый запрос
- `region`: Регион - по умолчанию "us-en"
- `safesearch`: Уровень фильтрации (on, moderate, off) - по умолчанию "moderate"
- `timelimit`: Ограничение по времени (d, w, m, y)
- `max_results`: Максимальное количество результатов - по умолчанию 10
- `page`: Номер страницы результатов - по умолчанию 1
- `backend`: Поисковые движки - по умолчанию "auto"
- `size`: Размер изображения (Small, Medium, Large, Wallpaper)
- `color`: Цвет изображения (color, Monochrome, Red, и т.д.)
- `type_image`: Тип изображения (photo, clipart, gif, и т.д.)
- `layout`: Макет изображения (Square, Tall, Wide)
- `license_image`: Лицензия изображения (any, Public, Share, и т.д.)

### `search_videos`
Поиск видео через DDGS

**Параметры:**
- `query` (обязательный): Поисковый запрос
- `region`: Регион - по умолчанию "us-en"
- `safesearch`: Уровень фильтрации (on, moderate, off) - по умолчанию "moderate"
- `timelimit`: Ограничение по времени (d, w, m)
- `max_results`: Максимальное количество результатов - по умолчанию 10
- `page`: Номер страницы результатов - по умолчанию 1
- `backend`: Поисковые движки - по умолчанию "auto"
- `resolution`: Разрешение видео (high, standard)
- `duration`: Длительность видео (short, medium, long)
- `license_videos`: Лицензия видео (creativeCommon, youtube)

### `search_news`
Поиск новостей через DDGS

**Параметры:**
- `query` (обязательный): Поисковый запрос
- `region`: Регион - по умолчанию "us-en"
- `safesearch`: Уровень фильтрации (on, moderate, off) - по умолчанию "moderate"
- `timelimit`: Ограничение по времени (d, w, m)
- `max_results`: Максимальное количество результатов - по умолчанию 10
- `page`: Номер страницы результатов - по умолчанию 1
- `backend`: Поисковые движки - по умолчанию "auto"

### `search_books`
Поиск книг через DDGS

**Параметры:**
- `query` (обязательный): Поисковый запрос
- `max_results`: Максимальное количество результатов - по умолчанию 10
- `page`: Номер страницы результатов - по умолчанию 1
- `backend`: Поисковые движки - по умолчанию "auto"

## Примеры использования

### Текстовый поиск
```json
{
  "method": "search_text",
  "params": {
    "query": "python programming",
    "max_results": 5,
    "region": "us-en"
  }
}
```

### Поиск изображений
```json
{
  "method": "search_images",
  "params": {
    "query": "cats",
    "max_results": 10,
    "color": "Monochrome"
  }
}
```

### Получение операторов поиска
```json
{
  "method": "get_search_operators",
  "params": {}
}
```

## Операторы поиска DDG

- `cats dogs` - Результаты о cats или dogs
- `"cats and dogs"` - Результаты точного совпадения "cats and dogs"
- `cats -dogs` - Меньше упоминаний dogs в результатах
- `cats +dogs` - Больше упоминаний dogs в результатах
- `cats filetype:pdf` - PDF файлы о cats
- `dogs site:example.com` - Страницы о dogs с сайта example.com
- `cats -site:example.com` - Страницы о cats, исключая example.com
- `intitle:dogs` - Заголовок страницы содержит слово "dogs"
- `inurl:cats` - URL страницы содержит слово "cats"  

## Примеры конфигов
### Для TCP

```
{
  "mcpServers": {
    "ddg-tcp": {
      "command": "tcp",
      "args": [
        "127.0.0.1:8765"
      ],
      "env": {},
      "active": true
    }
  }
} 
```
Jan:  
```
{
  "command": "tcp",
  "args": [
    "127.0.0.1:8765"
  ],
  "env": {},
  "active": true
}
```  
Для Jan рекомендую использовать TCP
### Конфигурация для запуска напрямую 
```
{
  "mcpServers": {
    "ddg-stdio": {
      "command": "python",
      "args": [
        "Путь_к_папке_duck_duck_MCP\\ddg_mcp_server.py"
      ],
      "env": {},
      "active": true
    }
  }
}
```
## Обработка ошибок

Сервер может возвращать следующие ошибки:
- Превышение лимита запросов
- Таймаут запроса
- Общие ошибки поиска

## Поддержка прокси

Для использования прокси можно установить переменную окружения `DDGS_PROXY`:
```bash
export DDGS_PROXY="socks5h://user:password@1.2.3.4:8080"
