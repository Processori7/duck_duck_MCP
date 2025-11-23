#!/usr/bin/env python3
"""
MCP server for searching information via DuckDuckGo Search (DDGS)
Uses NDJSON (newline-delimited JSON) as required by the MCP specification.
"""
import json
import sys
import os
import ftfy
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Настройка кодировки для Windows
if sys.platform == "win32":
    import io
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    from ddgs import DDGS
except ImportError:
    print("Ошибка: Не установлен пакет ddgs. Установите его: pip install ddgs")
    sys.exit(1)


def send_message(data: Dict[str, Any]) -> None:
    """Отправка сообщения через STDOUT в формате NDJSON (один JSON-объект на строку с \\n в конце)"""
    try:
        data_str = json.dumps(data, ensure_ascii=False)
        sys.stdout.write(data_str + "\n")
        sys.stdout.flush()
        logger.debug(f"Sent MCP message: {data_str[:500]}...")
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise


def read_message() -> Optional[Dict[str, Any]]:
    """Чтение одного NDJSON-сообщения из STDIN"""
    try:
        line = sys.stdin.readline()
        if not line:
            logger.info("EOF received – exiting")
            return None
        line = line.strip()
        if not line:
            logger.debug("Skipped empty line")
            return None
        parsed = json.loads(line)
        if isinstance(parsed, dict):
            logger.debug(f"Received valid message: {parsed}")
            return parsed
        else:
            logger.warning("Parsed message is not a dictionary")
            return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}, line: {line}")
        return None
    except Exception as e:
        logger.error(f"Error reading message: {e}")
        import traceback
        traceback.print_exc()
        return None


# === ДАЛЕЕ – ВСЁ ОСТАЛЬНОЕ ОСТАЁТСЯ БЕЗ ИЗМЕНЕНИЙ ===
# (включая fix_encoding, search_*, handle_request и т.д.)

def get_search_operators() -> Dict[str, Any]:
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


def fix_encoding(text: str) -> str:
    if not text:
        return text
    original_text = text
    try:
        fixed_by_ftfy = ftfy.fix_text(text)
        if fixed_by_ftfy != text:
            cyrillic_count = sum(1 for c in fixed_by_ftfy if 'а' <= c <= 'я' or 'А' <= c <= 'Я')
            latin_count = sum(1 for c in fixed_by_ftfy if ('a' <= c <= 'z' or 'A' <= c <= 'Z'))
            emoji_count = sum(1 for c in fixed_by_ftfy if 0x1F600 <= ord(c) <= 0x1F64F)
            if cyrillic_count > 0 or emoji_count > 0:
                logger.debug(f"ftfy improved text: Cyrillic={cyrillic_count}, Emoji={emoji_count}")
                text = fixed_by_ftfy
    except ImportError:
        logger.debug("ftfy not available")
    except Exception as e:
        logger.debug(f"ftfy failed: {e}")

    corruption_indicators = get_encoding_corruption_patterns()
    if has_encoding_corruption(text, corruption_indicators):
        logger.debug(f"Detected encoding corruption in: '{text[:50]}...'")
        strategies = [
            lambda t: repair_windows1251_corruption(t),
            lambda t: repair_latin1_corruption(t),
            lambda t: repair_cp1252_corruption(t),
            lambda t: repair_double_utf8(t),
            lambda t: manual_fix_multilingual_encoding(t),
            lambda t: repair_mojibake_patterns(t),
            lambda t: repair_html_entities(t),
        ]
        best_result = evaluate_encoding_candidates(text, strategies)
        if best_result != text:
            logger.info(f"Successfully repaired encoding: '{text[:30]}...' -> '{best_result[:30]}...'")
            return best_result

    return normalize_text_final(text)


def manual_fix_multilingual_encoding(text: str) -> str:
    replacements = {
        'Р°': 'а', 'Р±': 'б', 'РІ': 'в', 'Рі': 'г', 'Рґ': 'д', 'Рµ': 'е', 'Р¶': 'ж', 'Р·': 'з',
        'Рё': 'и', 'Р№': 'й', 'Рє': 'к', 'Р»': 'л', 'Рј': 'м', 'РЅ': 'н', 'Рѕ': 'о', 'Рї': 'п',
        'СЂ': 'р', 'СЃ': 'с', 'С‚': 'т', 'Сѓ': 'у', 'С„': 'ф', 'С…': 'х', 'С†': 'ц', 'С‡': 'ч',
        'С€': 'ш', 'С‰': 'щ', 'СЌ': 'ь', 'С‹': 'ы', 'СЌ': 'э', 'СЋ': 'ю', 'СЏ': 'я',
        'Рђ': 'А', 'Р‘': 'Б', 'Р’': 'В', 'Р“': 'Г', 'Р”': 'Д', 'Р•': 'Е',
    }
    result = text
    for corrupted, correct in replacements.items():
        if corrupted in result:
            result = result.replace(corrupted, correct)
            logger.debug(f"Replaced '{corrupted}' -> '{correct}'")
    return result


def get_encoding_corruption_patterns():
    return {
        'double_encoded_cyrillic': ['Р°', 'Р±', 'РІ', 'Рі', 'Рґ', 'Рµ', 'Р¶', 'Р·', 'Рё', 'Р№'],
        'latin1_as_utf8': ['Ð', 'Ñ', 'Â', 'Ã', 'â', 'ç'],
        'windows1252_artifacts': ['€', '‚', 'ƒ', '„', '…', '†']
    }


def has_encoding_corruption(text: str, patterns) -> bool:
    sample = text[:500]
    return sum(1 for lst in patterns.values() for p in lst if p in sample) >= 2


def repair_windows1251_corruption(text: str) -> str:
    try:
        return text.encode('windows-1251', errors='ignore').decode('utf-8', errors='ignore')
    except (UnicodeError, LookupError):
        return text


def repair_latin1_corruption(text: str) -> str:
    try:
        return text.encode('iso-8859-1', errors='ignore').decode('utf-8', errors='ignore')
    except (UnicodeError, LookupError):
        return text


def repair_cp1252_corruption(text: str) -> str:
    try:
        return text.encode('windows-1252', errors='ignore').decode('utf-8', errors='ignore')
    except (UnicodeError, LookupError):
        return text


def repair_double_utf8(text: str) -> str:
    try:
        return text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
    except UnicodeError:
        return text


def repair_mojibake_patterns(text: str) -> str:
    mojibake_map = {
        'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú',
        'Ã±': 'ñ', 'Ã¢': 'â', 'Ã´': 'ô', 'Ã¨': 'è', 'Ã ': 'à'
    }
    result = text
    for corrupted, correct in mojibake_map.items():
        result = result.replace(corrupted, correct)
    return result


def repair_html_entities(text: str) -> str:
    import html
    try:
        return html.unescape(text)
    except Exception:
        return text


def evaluate_encoding_candidates(original: str, strategies) -> str:
    best = original
    best_score = calculate_text_quality_score(original)
    for strategy in strategies:
        try:
            candidate = strategy(original)
            score = calculate_text_quality_score(candidate)
            if score > best_score:
                best, best_score = candidate, score
        except Exception as e:
            logger.debug(f"Strategy failed: {e}")
    return best


def calculate_text_quality_score(text: str) -> float:
    if not text:
        return 0.0
    length = len(text)
    cyrillic = sum(1 for c in text if 'а' <= c <= 'я' or 'А' <= c <= 'Я')
    latin = sum(1 for c in text if 'a' <= c <= 'z' or 'A' <= c <= 'Z')
    spaces = sum(1 for c in text if c.isspace())
    score = 0.0
    if cyrillic > 0:
        score += (cyrillic / length) * 2.0
    if latin > 0:
        score += (latin / length) * 1.5
    if 0.05 <= (spaces / length) <= 0.25:
        score += 1.0
    for lst in get_encoding_corruption_patterns().values():
        for p in lst:
            if p in text:
                score -= 0.5
    return max(0.0, score)


def normalize_text_final(text: str) -> str:
    import unicodedata
    try:
        normalized = unicodedata.normalize('NFKC', text)
        normalized = normalized.replace('\xa0', ' ')
        import re
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    except Exception:
        return text


def search_text(
    query: str,
    region: str = "us-en",
    safesearch: str = "moderate",
    timelimit: Optional[str] = None,
    max_results: int = 10,
    page: int = 1,
    backend: str = "auto"
) -> List[Dict[str, str]]:
    try:
        import unicodedata
        query = unicodedata.normalize('NFKC', query).replace('\xa0', ' ').strip()
        logger.info(f"Searching text with query: {query}, region: {region}, backend: {backend}")
        has_cyrillic = any('а' <= c <= 'я' or 'А' <= c <= 'Я' for c in query)
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
            result_list = list(results) if results else []
            for item in result_list:
                if 'title' in item:
                    item['title'] = fix_encoding(item['title'])
                if 'body' in item:
                    item['body'] = fix_encoding(item['body'])
                if 'href' in item:
                    item['href'] = item['href'].strip()
            logger.info(f"Found {len(result_list)} text results")
            return result_list
    except Exception as e:
        logger.error(f"Text search error: {str(e)}")
        raise Exception(f"Ошибка поиска: {str(e)}")


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
    try:
        import unicodedata
        query = unicodedata.normalize('NFKC', query).replace('\xa0', ' ').strip()
        logger.info(f"Searching news with query: {query}, region: {region}, timelimit: {timelimit}")
        has_cyrillic = any('а' <= c <= 'я' or 'А' <= c <= 'Я' for c in query)
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
            result_list = list(results) if results else []
            for item in result_list:
                for field in ['title', 'body', 'source']:
                    if field in item:
                        item[field] = fix_encoding(item[field])
            if not result_list and has_cyrillic:
                logger.info("Trying fallback: us-en region and transliteration")
                results = ddgs.news(query=query, region="us-en", safesearch=safesearch, timelimit=timelimit, max_results=max_results, page=page, backend=backend)
                result_list = list(results) if results else []
                if not result_list:
                    transl_map = {
                        'новости': 'news', 'россии': 'russia', 'россия': 'russia',
                        'москва': 'moscow', 'путин': 'putin', 'кремль': 'kremlin',
                        'украина': 'ukraine', 'спорт': 'sport', 'футбол': 'football',
                        'политика': 'politics', 'экономика': 'economy'
                    }
                    query_trans = ' '.join(transl_map.get(w.lower(), w) for w in query.split())
                    if query_trans != query:
                        results = ddgs.news(query=query_trans, region="us-en", safesearch=safesearch, timelimit=timelimit, max_results=max_results, page=page, backend=backend)
                        result_list = list(results) if results else []
                if result_list:
                    for item in result_list:
                        for field in ['title', 'body', 'source']:
                            if field in item:
                                item[field] = fix_encoding(item[field])
                        item['_note'] = f"Results from fallback (original region {region} had no results)"

            logger.info(f"Found {len(result_list)} news results")
            return result_list
    except Exception as e:
        error_msg = str(e)
        logger.error(f"News search error: {error_msg}")
        if "No results found" in error_msg:
            return [{
                "title": "Нет результатов",
                "body": f"К сожалению, не найдено новостей по запросу '{query}' в регионе {region}. Попробуйте использовать ddg_search_text или запрос на английском.",
                "href": "",
                "date": "",
                "source": "DuckDuckGo News API",
                "_note": "News search has limited support for non-English queries."
            }]
        raise Exception(f"Ошибка поиска новостей: {error_msg}")


def search_books(
    query: str,
    max_results: int = 10,
    page: int = 1,
    backend: str = "auto"
) -> List[Dict[str, str]]:
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
    logger.info(f"START handle_request with request: {request}")
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    logger.info(f"Handling method: {method} with ID: {request_id}")

    if method == "client/registerCapability":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "progress" or method == "notifications/initialized":
        return None
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "ddg-search", "version": "1.0.0"},
                "capabilities": {"tools": {}}
            }
        }
    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"resources": []}}
    if method == "resources/templates/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"resource_templates": []}}

    if method == "tools/list":
        tools = [
            {
                "name": "ddg_search_text",
                "description": "Поиск текста через DuckDuckGo",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "region": {"type": "string", "default": "us-en"},
                        "safesearch": {"type": "string", "default": "moderate", "enum": ["on", "moderate", "off"]},
                        "timelimit": {"type": "string", "enum": ["d", "w", "m", "y"]},
                        "max_results": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                        "page": {"type": "integer", "default": 1},
                        "backend": {"type": "string", "default": "auto"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "ddg_search_news",
                "description": "Поиск новостей через DuckDuckGo News",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "region": {"type": "string", "default": "us-en"},
                        "safesearch": {"type": "string", "default": "moderate", "enum": ["on", "moderate", "off"]},
                        "timelimit": {"type": "string", "enum": ["d", "w", "m"]},
                        "max_results": {"type": "integer", "default": 10, "minimum": 1},
                        "page": {"type": "integer", "default": 1},
                        "backend": {"type": "string", "default": "auto"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "ddg_search_images",
                "description": "Поиск изображений через DuckDuckGo Images",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "region": {"type": "string", "default": "us-en"},
                        "safesearch": {"type": "string", "default": "moderate", "enum": ["on", "moderate", "off"]},
                        "timelimit": {"type": "string", "enum": ["d", "w", "m", "y"]},
                        "max_results": {"type": "integer", "default": 10, "minimum": 1},
                        "page": {"type": "integer", "default": 1},
                        "backend": {"type": "string", "default": "auto"},
                        "size": {"type": "string", "enum": ["Small", "Medium", "Large", "Wallpaper"]},
                        "color": {"type": "string", "enum": ["color", "Monochrome", "Red", "Orange", "Yellow", "Green", "Blue", "Purple", "Pink", "Brown", "Black", "Gray", "Teal", "White"]},
                        "type_image": {"type": "string", "enum": ["photo", "clipart", "gif", "transparent", "line"]},
                        "layout": {"type": "string", "enum": ["Square", "Tall", "Wide"]},
                        "license_image": {"type": "string", "enum": ["any", "Public", "Share", "ShareCommercially", "Modify", "ModifyCommercially"]}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "ddg_search_videos",
                "description": "Поиск видео через DuckDuckGo Videos",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "region": {"type": "string", "default": "us-en"},
                        "safesearch": {"type": "string", "default": "moderate", "enum": ["on", "moderate", "off"]},
                        "timelimit": {"type": "string", "enum": ["d", "w", "m"]},
                        "max_results": {"type": "integer", "default": 10, "minimum": 1},
                        "page": {"type": "integer", "default": 1},
                        "backend": {"type": "string", "default": "auto"},
                        "resolution": {"type": "string", "enum": ["high", "standard"]},
                        "duration": {"type": "string", "enum": ["short", "medium", "long"]},
                        "license_videos": {"type": "string", "enum": ["creativeCommon", "youtube"]}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "ddg_search_books",
                "description": "Поиск книг через DuckDuckGo Books",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "max_results": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                        "page": {"type": "integer", "default": 1},
                        "backend": {"type": "string", "default": "auto"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "ddg_search_operators",
                "description": "Получить документацию по операторам поиска DDG",
                "inputSchema": {"type": "object", "properties": {}}
            }
        ]
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools}
        }

    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        logger.info(f"Calling tool: {tool_name} with arguments: {arguments}")
        try:
            if tool_name in ["ddg_search_text", "ddg_search_news", "ddg_search_images", "ddg_search_videos", "ddg_search_books"]:
                query = arguments.get("query", "").strip()
                if not query:
                    return {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32602,
                            "message": f"Пустой поисковый запрос для инструмента {tool_name}. Укажите 'query'."
                        }
                    }

            if tool_name == "ddg_search_text":
                results = search_text(**arguments)
            elif tool_name == "ddg_search_news":
                results = search_news(**arguments)
            elif tool_name == "ddg_search_images":
                results = search_images(**arguments)
            elif tool_name == "ddg_search_videos":
                results = search_videos(**arguments)
            elif tool_name == "ddg_search_books":
                results = search_books(**arguments)
            elif tool_name == "ddg_search_operators":
                results = get_search_operators()
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                }

            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(results, ensure_ascii=False, indent=2)}]
                }
            }

        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": str(e)}
            }

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"}
    }


def main():
    logger.info("Starting DuckDuckGo MCP Server (NDJSON mode)")
    try:
        while True:
            message = read_message()
            if message is None:
                break
            if not isinstance(message, dict):
                continue
            response = handle_request(message)
            if response is not None:
                send_message(response)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()