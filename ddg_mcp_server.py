#!/usr/bin/env python3
"""
MCP server for searching information via DuckDuckGo Search (DDGS)
"""

import json
import sys
import os
from typing import Any, Dict, List, Optional

try:
    from ddgs import DDGS
except ImportError:
    print("Ошибка: Не установлен пакет ddgs. Установите его: pip install ddgs")
    sys.exit(1)

def send_message(data: Dict[str, Any]) -> None:
    """Send message via STDIO"""
    data_str = json.dumps(data, ensure_ascii=True)
    # If running in terminal (manual test) - pretty print for debugging
    if sys.stdin.isatty():
        print("=== Response ===")
        print(json.dumps(data, ensure_ascii=True, indent=2))
        print("=================")
    else:
        # If running via STDIO (Cline) - use MCP protocol
        message = f'{len(data_str)}\n{data_str}\n'
        sys.stdout.write(message)
        sys.stdout.flush()
        os.fsync(sys.stdout.fileno())  # Force sync

def read_message() -> Optional[Dict[str, Any]]:
    """Read messages via STDIO according to MCP protocol"""
    try:
        # If running in terminal (manual test) - use interactive mode
        if sys.stdin.isatty():
            print("=== Interactive Debug Mode ===")
            print("Enter JSON-RPC requests (or 'quit' to exit):")
            while True:
                try:
                    line = input("> ").strip()
                    if line.lower() == 'quit':
                        return None
                    if line:
                        parsed = json.loads(line)
                        if isinstance(parsed, dict):
                            return parsed
                        else:
                            print("Error: Not a dictionary")
                except EOFError:
                    return None
                except json.JSONDecodeError as e:
                    print(f"JSON Error: {e}")
                except Exception as e:
                    print(f"Error: {e}")
        else:
            # If running via STDIO (Cline) - use MCP protocol
            # Read message length
            length_line = sys.stdin.readline()
            if not length_line:
                return None

            # Skip empty lines
            while length_line.strip() == "":
                length_line = sys.stdin.readline()
                if not length_line:
                    return None
            
            # Check if line is JSON (manual input via STDIO)
            stripped_line = length_line.strip()
            if stripped_line.startswith('{') and stripped_line.endswith('}'):
                parsed = json.loads(stripped_line)
                if isinstance(parsed, dict):
                    return parsed
                else:
                    return None

            length = int(stripped_line)

            # Read JSON message of specified length
            message = sys.stdin.read(length)

            # Skip \n after message
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
    """Handle incoming request"""
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")

    # Handle client registration request
    if method == "client/registerCapability":
        # Just acknowledge the registration
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {}
        }

    # Handle progress notifications (no response needed)
    if method == "progress":
        # Just ignore progress notifications
        return None

    # Required initialize method
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "ddg-search",
                    "version": "1.0.0"
                },
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
    """Main server loop"""
    try:
        # If running in terminal - show welcome message
        if sys.stdin.isatty():
            print("DuckDuckGo MCP Server - Debug Mode")
            print("Server info:")
            print("  Name: ddg-search")
            print("  Version: 1.0.0")
            print("  Protocol: 2024-11-05")
            print()
        
        # Infinite request processing loop
        while True:
            try:
                message = read_message()
                if message is None:
                    # If message is None, it means EOF or connection closed
                    break  # Exit the loop gracefully
                
                # Check that message is a dictionary
                if not isinstance(message, dict):
                    continue

                response = handle_request(message)
                if response:
                    send_message(response)
                    
            except KeyboardInterrupt:
                # Graceful shutdown on Ctrl+C
                if sys.stdin.isatty():
                    print("\nServer shutdown requested.")
                break
            except Exception:
                # For other errors, continue processing in STDIO mode
                # or exit in debug mode
                if sys.stdin.isatty():
                    import traceback
                    traceback.print_exc()
                    break
                continue
                
    except Exception:
        # Send error to client and exit
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": "Server error"
            }
        }
        try:
            send_message(error_response)
        except:
            pass
        
if __name__ == "__main__":
    main()