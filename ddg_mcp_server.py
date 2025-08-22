#!/usr/bin/env python3
"""
MCP сервер для поиска информации через DuckDuckGo Search (DDGS)
"""

import json
import sys
from typing import Any, Dict, List, Optional

try:
    from ddgs import DDGS
except ImportError:
    print("Ошибка: Не установлен пакет ddgs. Установите его: pip install ddgs")
    sys.exit(1)

def send_message(data: Dict[str, Any]) -> None:
    """Отправка сообщения через STDIO"""
    data_str = json.dumps(data, ensure_ascii=False)
    sys.stdout.write(f'{len(data_str)}\n{data_str}\n')
    sys.stdout.flush()

def read_message() -> Optional[Dict[str, Any]]:
    """Функция чтения сообщений через STDIO по протоколу MCP"""
    try:
        # Если запущен в терминале (ручной тест) - используем input()
        if sys.stdin.isatty():
            line = input()
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                return parsed
            else:
                return None
        else:
            # Если запущен через STDIO (Jan) - используем протокол MCP
            # Читаем длину сообщения
            length_line = sys.stdin.readline()
            if not length_line:
                return None

            # Пропускаем пустые строки
            while length_line.strip() == "":
                length_line = sys.stdin.readline()
                if not length_line:
                    return None
            
            # Проверяем, является ли строка JSON (ручной ввод через STDIO)
            stripped_line = length_line.strip()
            if stripped_line.startswith('{') and stripped_line.endswith('}'):
                parsed = json.loads(stripped_line)
                if isinstance(parsed, dict):
                    return parsed
                else:
                    return None

            length = int(stripped_line)

            # Читаем JSON-сообщение указанной длины
            message = sys.stdin.read(length)

            # Пропускаем \n после сообщения
            sys.stdin.read(1)

            parsed = json.loads(message)
            if isinstance(parsed, dict):
                return parsed
            else:
                return None
    except Exception:
        return None

def get_search_operators() -> Dict[str, str]:
    """Возвращает документацию по операторам поиска DDG"""
    return {
        "description": "Операторы поиска DDG",
        "operators": {
            "cats dogs": "Результаты о cats или dogs",
            '"cats and dogs"': "Результаты точного совпадения 'cats and dogs'",
            "cats -dogs": "Меньше упоминаний dogs в результатах",
            "cats +dogs": "Больше упоминаний dogs в результатах",
            "cats filetype:pdf": "PDF файлы о cats",
            "dogs site:example.com": "Страницы о dogs с сайта example.com",
            "cats -site:example.com": "Страницы о cats, исключая example.com",
            "intitle:dogs": "Заголовок страницы содержит слово 'dogs'",
            "inurl:cats": "URL страницы содержит слово 'cats'"
        }
    }

def search_text(
    query: str,
    region: str = "us-en",
    safesearch: str = "moderate",
    timelimit: Optional[str] = None,
    max_results: int = 10,
    page: int = 1,
    backend: str = "auto"
) -> List[Dict[str, str]]:
    """Текстовый поиск через DDGS"""
    try:
        with DDGS() as ddgs:
            results = ddgs.text(
                query=query,
                region=region,
                safesearch=safesearch,
                timelimit=timelimit,
                max_results=max_results,
                page=page,
                backend=backend
            )
            return list(results) if results else []
    except Exception as e:
        raise Exception(f"Ошибка поиска: {str(e)}")

# === Остальные функции поиска ===
# (search_images, search_videos, search_news, search_books)

def search_images(
    query: str,
    region: str = "us-en",
    safesearch: str = "moderate",
    timelimit: Optional[str] = None,
    max_results: int = 10,
    page: int = 1,
    backend: str = "auto",
    size: Optional[str] = None,
    color: Optional[str] = None,
    type_image: Optional[str] = None,
    layout: Optional[str] = None,
    license_image: Optional[str] = None
) -> List[Dict[str, str]]:
    """Поиск изображений через DDGS"""
    try:
        with DDGS() as ddgs:
            results = ddgs.images(
                query=query,
                region=region,
                safesearch=safesearch,
                timelimit=timelimit,
                max_results=max_results,
                page=page,
                backend=backend,
                size=size,
                color=color,
                type_image=type_image,
                layout=layout,
                license_image=license_image
            )
            return list(results) if results else []
    except Exception as e:
        raise Exception(f"Ошибка поиска изображений: {str(e)}")

def search_videos(
    query: str,
    region: str = "us-en",
    safesearch: str = "moderate",
    timelimit: Optional[str] = None,
    max_results: int = 10,
    page: int = 1,
    backend: str = "auto",
    resolution: Optional[str] = None,
    duration: Optional[str] = None,
    license_videos: Optional[str] = None
) -> List[Dict[str, str]]:
    """Поиск видео через DDGS"""
    try:
        with DDGS() as ddgs:
            results = ddgs.videos(
                query=query,
                region=region,
                safesearch=safesearch,
                timelimit=timelimit,
                max_results=max_results,
                page=page,
                backend=backend,
                resolution=resolution,
                duration=duration,
                license_videos=license_videos
            )
            return list(results) if results else []
    except Exception as e:
        raise Exception(f"Ошибка поиска видео: {str(e)}")

def search_news(
    query: str,
    region: str = "us-en",
    safesearch: str = "moderate",
    timelimit: Optional[str] = None,
    max_results: int = 10,
    page: int = 1,
    backend: str = "auto"
) -> List[Dict[str, str]]:
    """Поиск новостей через DDGS"""
    try:
        with DDGS() as ddgs:
            results = ddgs.news(
                query=query,
                region=region,
                safesearch=safesearch,
                timelimit=timelimit,
                max_results=max_results,
                page=page,
                backend=backend
            )
            return list(results) if results else []
    except Exception as e:
        raise Exception(f"Ошибка поиска новостей: {str(e)}")

def search_books(
    query: str,
    max_results: int = 10,
    page: int = 1,
    backend: str = "auto"
) -> List[Dict[str, str]]:
    """Поиск книг через DDGS"""
    try:
        with DDGS() as ddgs:
            results = ddgs.books(
                query=query,
                max_results=max_results,
                page=page,
                backend=backend
            )
            return list(results) if results else []
    except Exception as e:
        raise Exception(f"Ошибка поиска книг: {str(e)}")

def handle_request(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Обработка входящего запроса"""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")

    # Обязательный метод initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "capabilities": {
                    "tools": {}
                }
            }
        }
    
    # Список доступных инструментов
    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "ddg_search_text",
                        "description": "Поиск текста через DuckDuckGo",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Поисковый запрос"},
                                "region": {"type": "string", "default": "us-en"},
                                "safesearch": {"type": "string", "default": "moderate", "enum": ["on", "moderate", "off"]},
                                "timelimit": {"type": "string", "enum": ["d", "w", "m", "y"]},
                                "max_results": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                                "page": {"type": "integer", "default": 1},
                                "backend": {"type": "string", "default": "auto"}
                            },
                            "required": ["query"]
                        }
                    }
                ]
            }
        }

    # Вызов инструмента
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        try:
            if tool_name == "ddg_search_text":
                results = search_text(**arguments)
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(results, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
                }
            elif tool_name == "ddg_search_operators":
                results = get_search_operators()
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(results, ensure_ascii=False, indent=2)
                            }
                        ]
                    }
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }

    # Неизвестный метод
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        }
    }

def main():
    """Основной цикл сервера"""
    try:
        # Регистрация возможностей
        send_message({
            "jsonrpc": "2.0",
            "method": "client/registerCapability",
            "params": {
                "registrations": []
            }
        })

        # Бесконечный цикл обработки запросов
        while True:
            try:
                message = read_message()
                # print(f"DEBUG: Получено сообщение: {message}")  # Убрал file=sys.stderr
                if message is None:
                    # print("DEBUG: message is None, продолжаем")
                    continue  # Продолжаем ждать
                
                # Проверяем, что message - словарь
                if not isinstance(message, dict):
                    # print(f"DEBUG: message не словарь: {message}")
                    continue

                response = handle_request(message)
                if response:
                    # print(f"DEBUG: Отправляем ответ: {response}")
                    send_message(response)
            except Exception as e:
                # print(f"DEBUG: Ошибка в цикле: {e}")
                # Продолжаем цикл, не завершаемся
                continue
                
    except Exception as e:
        # print(f"DEBUG: Фатальная ошибка: {e}")
        # Отправляем ошибку клиенту
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": f"Server error: {str(e)}"
            }
        }
        try:
            send_message(error_response)
        except:
            pass
        
if __name__ == "__main__":
    main()