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
    uv pip install -r requirements.txt
    # Или с pip
    pip install -r requirements.txt
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
      "timeout": 120,
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
Для Jan и Cline не рекомендую использовать TCP
### Конфигурация для запуска напрямую 
```
{
  "mcpServers": {
    "ddg-stdio": {
      "disabled": true,
      "timeout": 60,
      "type": "stdio",
      "command": "python",
      "args": [
        "Path_To\\ddg_mcp_server.py"
      ],
      "env": {}
    }
  }
}
```

### Конфигурация с использованием Python из venv (рекомендуется)

**Для Windows:**
```json
{
  "mcpServers": {
    "ddg-stdio": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "C:\\Users\\Igor\\Desktop\\duck_duck_MCP\\venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\Igor\\Desktop\\duck_duck_MCP\\ddg_mcp_server.py"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

**Важно:**
- Замените `C:\\Users\\Igor\\Desktop\\duck_duck_MCP` на ваш реальный путь к проекту
- Используйте двойные обратные слashes (`\\`) в путях для Windows
- Убедитесь, что в venv установлены все зависимости: `pip install -r requirements.txt`
- Переменная окружения `PYTHONIOENCODING=utf-8` обязательна для правильной работы с кириллицей

**Для Linux/macOS:**
```json
{
  "mcpServers": {
    "ddg-stdio": {
      "disabled": false,
      "timeout": 60,
      "type": "stdio",
      "command": "/path/to/duck_duck_MCP/venv/bin/python",
      "args": ["/path/to/duck_duck_MCP/ddg_mcp_server.py"],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```
{
  "mcpServers": {
    "ddg-stdio": {
      "command": "Полный_путь_к_папке_duck_duck_MCP\\venv\\Scripts\\python.exe",
      "timeout": 120,
       "type": "stdio",
      "args": [
        "Полный_путь_к_папке_duck_duck_MCP\\ddg_mcp_server.py"
      ],
      "env": {},
      "active": true
    }
  }
}
```
*Замените `Полный_путь_к_папке_duck_duck_MCP` на реальный путь к вашему проекту. Например: `E:\\Users\\Igory\\Desktop\\duck_duck_MCP\\venv\\Scripts\\python.exe`*

## Обработка ошибок

Сервер может возвращать следующие ошибки:
- Превышение лимита запросов
- Таймаут запроса
- Общие ошибки поиска

## Тестирование

Проект включает несколько тестовых скриптов для проверки работы сервера в разных режимах:

### Для запуска введите:
```bash
python test_server_enhanced.py
```  
и следуйте инструкциям.

## Поддержка прокси
Для использования прокси можно установить переменную окружения `DDGS_PROXY`:
```bash
export DDGS_PROXY="socks5h://user:password@1.2.3.4:8080"
```

---

# MCP Server for Information Search via DuckDuckGo Search

This MCP server provides tools for searching information on the internet using the DDGS (DuckDuckGo Search) library.

## Installation

### Requirements

- Python 3.8+
- `uv` (https://github.com/astral-sh/uv) - recommended for dependency management
- Or standard `pip` and `venv`

### Installation Steps

1.  **Clone the repository or create a project folder:**
    ```bash
    mkdir duck_duck_MCP
    cd duck_duck_MCP
    ```

2.  **(Recommended) Create a virtual environment:**
    ```bash
    # With uv
    uv venv
    # Activate (Windows)
    venv\Scripts\activate
    # Activate (Linux/macOS)
    source .venv/bin/activate
    ```
    *Note: If you use `uv`, it will automatically create and activate `.venv` when you first run `uv pip install`.*

3.  **Install dependencies:**
    ```bash
    # With uv (recommended)
    uv pip install -r requirements.txt
    # Or with pip
    pip install -r requirements.txt
    ```
    *Note: `ddgs` is a library for working with DuckDuckGo Search.*

## Running

The server can work in two modes: **STDIO** and **TCP**.

### STDIO Mode

This mode is used for direct interaction through standard input/output streams. Suitable for running from the terminal or integration with clients that launch the server as a child process.

1.  **Run the server directly:**
    ```bash
    # If you're in a virtual environment
    python ddg_mcp_server.py
    # Or with full path to python from venv
    venv\Scripts\python.exe ddg_mcp_server.py
    ```

### TCP Mode

This mode launches the server as a TCP server listening on the specified port. Suitable for integration with clients that connect over the network.

1.  **Run TCP server:**
    ```bash
    # If you're in a virtual environment
    python tcp_ddg_server.py
    # Or with full path to python from venv
    venv\Scripts\python.exe tcp_ddg_server.py
    ```

2.  By default, the server will start on `127.0.0.1:8765`. You will see the message:
    ```
    TCP server started on 127.0.0.1:8765
    ```

## Supported MCP Methods

The server implements the following MCP protocol methods:

- `initialize` - Server initialization
- `tools/list` - Get list of available tools
- `tools/call` - Call tool

## Available Tools

### `get_search_operators`
Get documentation on DDG search operators

**Parameters:** none

### `search_text`
Text search via DDGS

**Parameters:**
- `query` (required): Search query
- `region`: Region (us-en, uk-en, ru-ru, etc.) - default "us-en"
- `safesearch`: Filtering level (on, moderate, off) - default "moderate"
- `timelimit`: Time limit (d, w, m, y)
- `max_results`: Maximum number of results - default 10
- `page`: Result page number - default 1
- `backend`: Search engines (auto, google, bing, etc.) - default "auto"

### `search_images`
Image search via DDGS

**Parameters:**
- `query` (required): Search query
- `region`: Region - default "us-en"
- `safesearch`: Filtering level (on, moderate, off) - default "moderate"
- `timelimit`: Time limit (d, w, m, y)
- `max_results`: Maximum number of results - default 10
- `page`: Result page number - default 1
- `backend`: Search engines - default "auto"
- `size`: Image size (Small, Medium, Large, Wallpaper)
- `color`: Image color (color, Monochrome, Red, etc.)
- `type_image`: Image type (photo, clipart, gif, etc.)
- `layout`: Image layout (Square, Tall, Wide)
- `license_image`: Image license (any, Public, Share, etc.)

### `search_videos`
Video search via DDGS

**Parameters:**
- `query` (required): Search query
- `region`: Region - default "us-en"
- `safesearch`: Filtering level (on, moderate, off) - default "moderate"
- `timelimit`: Time limit (d, w, m)
- `max_results`: Maximum number of results - default 10
- `page`: Result page number - default 1
- `backend`: Search engines - default "auto"
- `resolution`: Video resolution (high, standard)
- `duration`: Video duration (short, medium, long)
- `license_videos`: Video license (creativeCommon, youtube)

### `search_news`
News search via DDGS

**Parameters:**
- `query` (required): Search query
- `region`: Region - default "us-en"
- `safesearch`: Filtering level (on, moderate, off) - default "moderate"
- `timelimit`: Time limit (d, w, m)
- `max_results`: Maximum number of results - default 10
- `page`: Result page number - default 1
- `backend`: Search engines - default "auto"

### `search_books`
Book search via DDGS

**Parameters:**
- `query` (required): Search query
- `max_results`: Maximum number of results - default 10
- `page`: Result page number - default 1
- `backend`: Search engines - default "auto"

## Usage Examples

### Text Search
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

### Image Search
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

### Getting Search Operators
```json
{
  "method": "get_search_operators",
  "params": {}
}
```

## DDG Search Operators

- `cats dogs` - Results about cats or dogs
- `"cats and dogs"` - Exact match results for "cats and dogs"
- `cats -dogs` - Fewer mentions of dogs in results
- `cats +dogs` - More mentions of dogs in results
- `cats filetype:pdf` - PDF files about cats
- `dogs site:example.com` - Pages about dogs from example.com
- `cats -site:example.com` - Pages about cats, excluding example.com
- `intitle:dogs` - Page title contains the word "dogs"
- `inurl:cats` - Page URL contains the word "cats"

## Configuration Examples
### For TCP

```json
{
  "mcpServers": {
    "ddg-tcp": {
      "timeout": 120,
      "command": "tcp",
       "type": "tcp",
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
```json
{
  "command": "tcp",
  "args": [
    "127.0.0.1:8765"
  ],
  "env": {},
  "active": true
}
```
*TCP mode is not recommended for Jan and Cline*

### Configuration for Direct Launch
```json
{
  "mcpServers": {
    "ddg-stdio": {
      "command": "python",
      "timeout": 120,
       "type": "stdio",
      "args": [
        "Path_to_duck_duck_MCP_folder\\ddg_mcp_server.py"
      ],
      "env": {},
      "active": true
    }
  }
}
```

### Configuration Using Python from venv (Recommended)
```json
{
  "mcpServers": {
    "ddg-stdio": {
      "command": "Full_path_to_duck_duck_MCP_folder\\venv\\Scripts\\python.exe",
      "timeout": 120,
       "type": "stdio",
      "args": [
        "Full_path_to_duck_duck_MCP_folder\\ddg_mcp_server.py"
      ],
      "env": {},
      "active": true
    }
  }
}
```
*Replace `Full_path_to_duck_duck_MCP_folder` with the actual path to your project. For example: `E:\\Users\\Igory\\Desktop\\duck_duck_MCP\\venv\\Scripts\\python.exe`*

## Error Handling

The server may return the following errors:
- Request limit exceeded
- Request timeout
- General search errors

## Testing

The project includes several test scripts to check server operation in different modes:

### To run, enter:
```bash
python test_server_enhanced.py
```
and follow the instructions.

## Proxy Support

To use a proxy, you can set the `DDGS_PROXY` environment variable:
```bash
export DDGS_PROXY="socks5h://user:password@1.2.3.4:8080"
```
