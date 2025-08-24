#!/usr/bin/env python3
"""
MCP server for searching information via DuckDuckGo Search (DDGS)
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
    # Устанавливаем UTF-8 кодировку для STDIO потоков
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    from ddgs import DDGS
except ImportError:
    print("Ошибка: Не установлен пакет ddgs. Установите его: pip install ddgs")
    sys.exit(1)

def send_message(data: Dict[str, Any]) -> None:
    """Отправка сообщения через STDIO"""
    try:
        # Используем ensure_ascii=False для корректной обработки Unicode символов
        data_str = json.dumps(data, ensure_ascii=False)
        # Преобразуем в байты с UTF-8 кодировкой
        data_bytes = data_str.encode('utf-8')
        # Отправляем длину в байтах, не в символах
        message = f'{len(data_bytes)}\n'.encode('utf-8') + data_bytes + b'\n'
        
        logger.debug(f"Отправляем сообщение размером {len(data_bytes)} байт")
        # Записываем байты напрямую в буфер stdout
        sys.stdout.buffer.write(message)
        sys.stdout.buffer.flush()
        
        logger.debug("Сообщение отправлено успешно")
        logger.debug(f"Содержимое сообщения (первые 500 символов): {str(data)[:500]}")
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        raise

def read_message() -> Optional[Dict[str, Any]]:
    """Чтение сообщений через STDIO согласно протоколу MCP с корректной обработкой UTF-8"""
    try:
        # Always use MCP protocol mode (no interactive mode)
        logger.debug("Attempting to read message length")
        # Read message length
        length_line = sys.stdin.readline()
        logger.debug(f"Read length line: {length_line!r}")
        if not length_line:
            logger.info("No length line received (EOF), returning None")
            return None

        # Skip empty lines
        while length_line.strip() == "":
            logger.debug("Skipping empty line")
            length_line = sys.stdin.readline()
            if not length_line:
                logger.info("No length line after skipping empty lines (EOF), returning None")
                return None
        
        # Check if line is JSON (manual input via STDIO)
        stripped_line = length_line.strip()
        logger.debug(f"Stripped line: {stripped_line!r}")
        if stripped_line.startswith('{') and stripped_line.endswith('}'):
            try:
                parsed = json.loads(stripped_line)
                if isinstance(parsed, dict):
                    logger.info(f"Received direct JSON message: {parsed}")
                    return parsed
                else:
                    logger.warning("Direct JSON message is not a dict")
                    return None
            except json.JSONDecodeError:
                # If it's not valid JSON, treat as length
                pass

        # Parse the length (byte count, not character count)
        try:
            byte_length = int(stripped_line)
            logger.info(f"Reading message of byte length: {byte_length}")
        except ValueError:
            logger.error(f"Invalid length format: {stripped_line}")
            return None

        # Read the exact number of bytes using buffer
        message_bytes = sys.stdin.buffer.read(byte_length)
        if len(message_bytes) != byte_length:
            logger.error(f"Expected {byte_length} bytes, got {len(message_bytes)}")
            return None
            
        # Decode bytes to string
        try:
            message = message_bytes.decode('utf-8')
            logger.info(f"Received message content: {message!r}")
        except UnicodeDecodeError as e:
            logger.error(f"UTF-8 decode error: {e}")
            return None

        # Read and skip the trailing newline
        newline = sys.stdin.buffer.read(1)
        logger.debug(f"Skipped newline character: {newline!r}")

        # Parse JSON
        try:
            parsed = json.loads(message)
            if isinstance(parsed, dict):
                logger.info(f"Parsed JSON message: {parsed}")
                return parsed
            else:
                logger.warning("Parsed message is not a dict")
                return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Message content: {message}")
            return None
            
    except ValueError as ve:
        logger.error(f"ValueError reading message: {ve}")
        return None
    except Exception as e:
        logger.error(f"Error reading message: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_search_operators() -> Dict[str, Any]:
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

def fix_encoding(text: str) -> str:
    """Попытка исправить кодировку текста"""
    if not text:
        return text
    
    original_text = text
    
    # Сначала пробуем ftfy
    try:
        fixed_by_ftfy = ftfy.fix_text(text)
        # Check if ftfy actually improved the text
        if fixed_by_ftfy != text:
            cyrillic_count = sum(1 for c in fixed_by_ftfy if 'а' <= c <= 'я' or 'А' <= c <= 'Я')
            if cyrillic_count > 0:
                logger.debug(f"Fixed encoding with ftfy: '{text[:50]}...' -> '{fixed_by_ftfy[:50]}...'")
                text = fixed_by_ftfy
    except ImportError:
        logger.debug("ftfy not available, using manual encoding fix")
    except Exception as e:
        logger.debug(f"ftfy failed: {e}")
    
    # Проверяем на наличие типичных признаков неправильной кодировки
    bad_patterns = [
        # Common double-encoding patterns
        'Р°', 'Р±', 'РІ', 'Рі', 'Р´', 'Рµ', 'Р¶', 'Р·', 'Ри', 'Р¹', 'Рє', 'Р»', 'Рј', 'РЍ', 'Рѕ', 'Р¿',
        'СЂ', 'СЃ', 'С‚', 'Сѓ', 'С„', 'С…', 'С†', 'С‡', 'С€', 'С‰', 'СЌ', 'С‹', 'СЍ', 'СЎ', 'СŽ',
        # Latin-1 interpreted as UTF-8 patterns
        'Ð', 'Ñ', 'Â', 'Ã', 'â', 'ç',
        # Windows-1252 patterns
        '¤', '¦', '¨', '©', 'ª', '«', '¬', '®', '°', '±', '²', '³',
        'Ä', 'Å', 'Æ', 'Ç', 'È', 'É', 'Ê', 'Ë', 'Ì', 'Í', 'Î', 'Ï',
        # Specific corrupted patterns we've seen
        'Рь', 'Рѕ', 'РІ', 'СЃ', 'С‚', 'Ри'
    ]
    
    if any(pattern in text for pattern in bad_patterns):
        logger.debug(f"Detected corrupted encoding patterns in: '{text[:50]}...'")
        
        # Try different decoding strategies
        strategies = [
            # Strategy 1: Assume text was UTF-8 but decoded as Windows-1251, then re-encoded as UTF-8
            lambda t: t.encode('windows-1251', errors='ignore').decode('utf-8', errors='ignore'),
            # Strategy 2: Assume text was UTF-8 but decoded as ISO-8859-1 (Latin-1)
            lambda t: t.encode('iso-8859-1', errors='ignore').decode('utf-8', errors='ignore'),
            # Strategy 3: Try CP1252 (Windows-1252)
            lambda t: t.encode('windows-1252', errors='ignore').decode('utf-8', errors='ignore'),
            # Strategy 4: Double UTF-8 encoding issue
            lambda t: t.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore'),
            # Strategy 5: Manual character replacement for known corrupted sequences
            lambda t: manual_fix_russian_encoding(t),
        ]
        
        best_result = text
        best_cyrillic_ratio = 0
        
        for i, strategy in enumerate(strategies, 1):
            try:
                fixed = strategy(text)
                if fixed and len(fixed) > 0:
                    # Count Cyrillic characters in the result
                    cyrillic_count = sum(1 for c in fixed if 'а' <= c <= 'я' or 'А' <= c <= 'Я')
                    cyrillic_ratio = cyrillic_count / len(fixed) if len(fixed) > 0 else 0
                    
                    # If we have a good amount of Cyrillic and it's better than what we had
                    if cyrillic_ratio > best_cyrillic_ratio and cyrillic_ratio >= 0.05:  # At least 5% Cyrillic
                        best_result = fixed
                        best_cyrillic_ratio = cyrillic_ratio
                        logger.debug(f"Strategy {i} improved text: '{text[:50]}...' -> '{fixed[:50]}...' (Cyrillic: {cyrillic_ratio:.2%})")
            except Exception as e:
                logger.debug(f"Strategy {i} failed: {e}")
        
        if best_result != text:
            return best_result
    
    # If text looks normal or couldn't be fixed, return as is
    return text

def manual_fix_russian_encoding(text: str) -> str:
    """Ручное исправление распространенных повреждений кодировки русского текста"""
    replacements = {
        # Common double-encoded Cyrillic patterns
        'Р°': 'а',  # а
        'Р±': 'б',  # б
        'РІ': 'в',  # в
        'Рі': 'г',  # г
        'Р´': 'д',  # д
        'Рµ': 'е',  # е
        'Р¶': 'ж',  # ж
        'Р·': 'з',  # з
        'Ри': 'и',  # и
        'Р¹': 'й',  # й
        'Рє': 'к',  # к
        'Р»': 'л',  # л
        'Рј': 'м',  # м
        'РЍ': 'н',  # н
        'Рѕ': 'о',  # о
        'Р¿': 'п',  # п
        'СЂ': 'р',  # р
        'СЃ': 'с',  # с
        'С‚': 'т',  # т
        'Сѓ': 'у',  # у
        'С„': 'ф',  # ф
        'С…': 'х',  # х
        'С†': 'ц',  # ц
        'С‡': 'ч',  # ч
        'С€': 'ш',  # ш
        'С‰': 'щ',  # щ
        'СЌ': 'ь',  # ь
        'С‹': 'ы',  # ы
        'СЍ': 'э',  # э
        'СЎ': 'ю',  # ю
        'СŽ': 'я',  # я
        # Capital letters
        'РĆ': 'А',  # А
        'Р‘': 'Б',  # Б
        'РВ': 'В',  # В
        'Р”': 'Г',  # Г
        'Р„': 'Д',  # Д
        'Р…': 'Е',  # Е
        # More patterns - specific to "новости" (news)
        'Рь': 'н',   # Fix for "н" in некоторых случаях 
    }
    
    result = text
    for corrupted, correct in replacements.items():
        if corrupted in result:
            result = result.replace(corrupted, correct)
            logger.debug(f"Replaced '{corrupted}' -> '{correct}' in text")
    
    return result

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
        # Clean up query - remove any non-breaking spaces and normalize
        import unicodedata
        query = unicodedata.normalize('NFKC', query)
        query = query.replace('\xa0', ' ').strip()
        
        logger.info(f"Searching text with query: {query}, region: {region}, backend: {backend}")
        
        # Detect if query contains Cyrillic
        has_cyrillic = any('а' <= char <= 'я' or 'А' <= char <= 'Я' for char in query)
        
        # Keep the specified region for text search - it usually works better
        effective_region = region
        
        if has_cyrillic:
            logger.info(f"Russian/Cyrillic query detected: '{query}' with region: {region}")
        
        with DDGS() as ddgs:
            results = ddgs.text(
                query=query,
                region=effective_region,
                safesearch=safesearch,
                timelimit=timelimit,
                max_results=max_results,
                page=page,
                backend=backend
            )
            result_list = list(results) if results else []
            
            # Try to fix encoding for each result
            for item in result_list:
                if 'title' in item:
                    item['title'] = fix_encoding(item['title'])
                if 'body' in item:
                    item['body'] = fix_encoding(item['body'])
                if 'href' in item:
                    # URLs should not need encoding fix, but clean them
                    item['href'] = item['href'].strip()
                    
                # Add info about encoding fix if it was applied
                if has_cyrillic and effective_region != region:
                    item['_note'] = f'Used {effective_region} region for Russian query to ensure proper encoding'
            
            # Log results for debugging
            logger.info(f"Found {len(result_list)} text results")
            if result_list and len(result_list) > 0:
                logger.debug(f"First result title: {result_list[0].get('title', 'No title')}")
            
            return result_list
    except Exception as e:
        logger.error(f"Text search error: {str(e)}")
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
    """Search news"""
    try:
        # Clean up query - remove any non-breaking spaces and normalize
        import unicodedata
        query = unicodedata.normalize('NFKC', query)
        query = query.replace('\xa0', ' ').strip()
        
        logger.info(f"Searching news with query: {query}, region: {region}, timelimit: {timelimit}")
        
        # Detect if query contains Cyrillic
        has_cyrillic = any('а' <= char <= 'я' or 'А' <= char <= 'Я' for char in query)
        
        # For Russian queries, try to use the specified region first
        effective_region = region
        
        if has_cyrillic:
            logger.info(f"Russian/Cyrillic query detected: '{query}'")
        
        with DDGS() as ddgs:
            results = ddgs.news(
                query=query,
                region=effective_region,
                safesearch=safesearch,
                timelimit=timelimit,
                max_results=max_results,
                page=page,
                backend=backend
            )
            result_list = list(results) if results else []
            
            # Try to fix encoding for each result
            for item in result_list:
                if 'title' in item:
                    item['title'] = fix_encoding(item['title'])
                if 'body' in item:
                    item['body'] = fix_encoding(item['body'])
                if 'source' in item:
                    item['source'] = fix_encoding(item['source'])
                    
                # Add info about region change if it was applied
                if has_cyrillic and effective_region != region:
                    item['_note'] = f'Used {effective_region} region for Russian query to ensure proper encoding'
            
            # If no results found with specified region, try with different approaches
            if not result_list:
                logger.warning(f"No news results for query '{query}' in region {effective_region}")
                
                # Try different strategies for Russian queries
                if has_cyrillic:
                    # Strategy 1: Try with us-en region
                    if effective_region != "us-en":
                        logger.info("Trying with us-en region...")
                        results = ddgs.news(
                            query=query,
                            region="us-en",
                            safesearch=safesearch,
                            timelimit=timelimit,
                            max_results=max_results,
                            page=page,
                            backend=backend
                        )
                        result_list = list(results) if results else []
                    
                    # Strategy 2: Try transliterated query
                    if not result_list:
                        # Simple transliteration for common Russian news terms
                        transliteration_map = {
                            'новости': 'novosti', 'россии': 'russia', 'россия': 'russia',
                            'москва': 'moscow', 'путин': 'putin', 'кремль': 'kremlin',
                            'украина': 'ukraine', 'спорт': 'sport', 'футбол': 'football',
                            'политика': 'politics', 'экономика': 'economy'
                        }
                        
                        query_lower = query.lower()
                        transliterated_parts = []
                        for word in query_lower.split():
                            transliterated_parts.append(transliteration_map.get(word, word))
                        
                        transliterated_query = ' '.join(transliterated_parts)
                        
                        if transliterated_query != query_lower:
                            logger.info(f"Trying transliterated query: '{transliterated_query}'")
                            results = ddgs.news(
                                query=transliterated_query,
                                region="us-en",
                                safesearch=safesearch,
                                timelimit=timelimit,
                                max_results=max_results,
                                page=page,
                                backend=backend
                            )
                            result_list = list(results) if results else []
                
                if result_list:
                    # Fix encoding and add note about region fallback
                    for item in result_list:
                        if 'title' in item:
                            item['title'] = fix_encoding(item['title'])
                        if 'body' in item:
                            item['body'] = fix_encoding(item['body'])
                        if 'source' in item:
                            item['source'] = fix_encoding(item['source'])
                        item['_note'] = f'Results from us-en region (original region {region} had no results)'
            
            logger.info(f"Found {len(result_list)} news results")
            return result_list
    except Exception as e:
        error_msg = str(e)
        logger.error(f"News search error: {error_msg}")
        
        # Provide more helpful error message
        if "No results found" in error_msg:
            return [{
                "title": "Нет результатов",
                "body": f"К сожалению, не найдено новостей по запросу '{query}' в регионе {region}. Попробуйте использовать ddg_search_text для общего поиска или попробовать запрос на английском языке.",
                "href": "",
                "date": "",
                "source": "DuckDuckGo News API",
                "_note": "News search may have limited support for non-English queries. Consider using text search instead."
            }]
        raise Exception(f"Ошибка поиска новостей: {error_msg}")

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
    logger.info(f"START handle_request with request: {request}")
    method = request.get("method")
    params = request.get("params", {})
    request_id = request.get("id")
    
    logger.info(f"Handling method: {method} with ID: {request_id}")
    logger.debug(f"Full request details - Method: {method}, ID: {request_id}, Params: {params}")
    
    # Log the actual request being processed
    logger.debug(f"Actually processing method: {method}")
    
    # Handle client registration request
    if method == "client/registerCapability":
        # Just acknowledge the registration
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {}
        }
        logger.debug(f"Sending response: {response}")
        return response

    # Handle progress notifications (no response needed)
    if method == "progress":
        # Just ignore progress notifications
        logger.debug("Ignoring progress notification")
        return None
    
    # Handle notifications/initialized (no response needed)
    if method == "notifications/initialized":
        logger.info("Received notifications/initialized - client finished initialization")
        # This is a notification, no response needed
        return None

    # Required initialize method
    if method == "initialize":
        logger.info("Processing initialize request")
        response = {
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
        logger.info(f"Sending initialize response: {response}")
        return response
    
    # Handle resources/list method
    elif method == "resources/list":
        logger.info("Processing resources/list request")
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "resources": []  # No resources in this server
            }
        }
        logger.info(f"Sending resources/list response: {response}")
        return response
    
    # Handle resources/templates/list method
    elif method == "resources/templates/list":
        logger.info("Processing resources/templates/list request")
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "resource_templates": []  # No resource templates in this server
            }
        }
        logger.info(f"Sending resources/templates/list response: {response}")
        return response
    
    # Список доступных инструментов
    elif method == "tools/list":
        logger.info("Processing tools/list request - CORRECT METHOD")
        logger.info(f"Request ID for tools/list: {request_id}")
        logger.info(f"Full request for tools/list: {request}")
        tools = [
            {
                "name": "ddg_search_text",
                "description": "Поиск текста через DuckDuckGo",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Поисковый запрос"},
                        "region": {"type": "string", "default": "us-en", "description": "Регион поиска (us-en, ru-ru, uk-ua и т.д.)"},
                        "safesearch": {"type": "string", "default": "moderate", "enum": ["on", "moderate", "off"]},
                        "timelimit": {"type": "string", "enum": ["d", "w", "m", "y"], "description": "d=день, w=неделя, m=месяц, y=год"},
                        "max_results": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                        "page": {"type": "integer", "default": 1},
                        "backend": {"type": "string", "default": "auto"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "ddg_search_news",
                "description": "Поиск новостей через DuckDuckGo News (может использовать backend: duckduckgo, yahoo)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Поисковый запрос для новостей"},
                        "region": {"type": "string", "default": "us-en", "description": "Регион новостей (us-en, ru-ru, uk-ua и т.д.)"},
                        "safesearch": {"type": "string", "default": "moderate", "enum": ["on", "moderate", "off"]},
                        "timelimit": {"type": "string", "enum": ["d", "w", "m"], "description": "d=день, w=неделя, m=месяц (год не поддерживается для новостей)"},
                        "max_results": {"type": "integer", "default": 10, "minimum": 1},
                        "page": {"type": "integer", "default": 1},
                        "backend": {"type": "string", "default": "auto", "description": "auto, duckduckgo, yahoo"}
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
                        "query": {"type": "string", "description": "Поисковый запрос для изображений"},
                        "region": {"type": "string", "default": "us-en", "description": "Регион поиска (us-en, ru-ru, uk-ua и т.д.)"},
                        "safesearch": {"type": "string", "default": "moderate", "enum": ["on", "moderate", "off"]},
                        "timelimit": {"type": "string", "enum": ["d", "w", "m", "y"], "description": "d=день, w=неделя, m=месяц, y=год"},
                        "max_results": {"type": "integer", "default": 10, "minimum": 1},
                        "page": {"type": "integer", "default": 1},
                        "backend": {"type": "string", "default": "auto"},
                        "size": {"type": "string", "enum": ["Small", "Medium", "Large", "Wallpaper"], "description": "Размер изображения"},
                        "color": {"type": "string", "enum": ["color", "Monochrome", "Red", "Orange", "Yellow", "Green", "Blue", "Purple", "Pink", "Brown", "Black", "Gray", "Teal", "White"], "description": "Цвет изображения"},
                        "type_image": {"type": "string", "enum": ["photo", "clipart", "gif", "transparent", "line"], "description": "Тип изображения"},
                        "layout": {"type": "string", "enum": ["Square", "Tall", "Wide"], "description": "Ориентация изображения"},
                        "license_image": {"type": "string", "enum": ["any", "Public", "Share", "ShareCommercially", "Modify", "ModifyCommercially"], "description": "Лицензия: any (All Creative Commons), Public (PublicDomain), Share (Free to Share and Use), ShareCommercially (Free to Share and Use Commercially), Modify (Free to Modify, Share, and Use), ModifyCommercially (Free to Modify, Share, and Use Commercially)"}
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
                        "query": {"type": "string", "description": "Поисковый запрос для видео"},
                        "region": {"type": "string", "default": "us-en", "description": "Регион поиска (us-en, ru-ru, uk-ua и т.д.)"},
                        "safesearch": {"type": "string", "default": "moderate", "enum": ["on", "moderate", "off"]},
                        "timelimit": {"type": "string", "enum": ["d", "w", "m"], "description": "d=день, w=неделя, m=месяц (год не поддерживается для видео)"},
                        "max_results": {"type": "integer", "default": 10, "minimum": 1},
                        "page": {"type": "integer", "default": 1},
                        "backend": {"type": "string", "default": "auto"},
                        "resolution": {"type": "string", "enum": ["high", "standard"], "description": "Разрешение видео (обратите внимание: standard, не standart)"},
                        "duration": {"type": "string", "enum": ["short", "medium", "long"], "description": "Длительность видео"},
                        "license_videos": {"type": "string", "enum": ["creativeCommon", "youtube"], "description": "Лицензия видео"}
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
                        "query": {"type": "string", "description": "Поисковый запрос для книг"},
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
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": tools
            }
        }
        logger.info(f"Generated tools/list response: {json.dumps(response, ensure_ascii=False)}")
        logger.info("About to return tools/list response")
        return response

    # Вызов инструмента
    elif method == "tools/call":
        logger.info("Processing tools/call request")
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        logger.info(f"Calling tool: {tool_name} with arguments: {arguments}")
        
        try:
            # Validate common arguments for all search tools
            if tool_name in ["ddg_search_text", "ddg_search_news", "ddg_search_images", "ddg_search_videos", "ddg_search_books"]:
                query = arguments.get("query", "").strip()
                if not query:
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32602,
                            "message": f"Пустой поисковый запрос для инструмента {tool_name}. Пожалуйста, укажите непустое значение для параметра 'query'.",
                            "data": {"arguments": arguments}
                        }
                    }
                    logger.warning(f"Empty query for tool {tool_name}: {arguments}")
                    return response
            
            if tool_name == "ddg_search_text":
                results = search_text(**arguments)
                response = {
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
                logger.debug(f"Sending response: {response}")
                return response
            elif tool_name == "ddg_search_news":
                results = search_news(**arguments)
                response = {
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
                logger.debug(f"Sending response: {response}")
                return response
            elif tool_name == "ddg_search_images":
                results = search_images(**arguments)
                response = {
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
                logger.debug(f"Sending response: {response}")
                return response
            elif tool_name == "ddg_search_videos":
                results = search_videos(**arguments)
                response = {
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
                logger.debug(f"Sending response: {response}")
                return response
            elif tool_name == "ddg_search_books":
                results = search_books(**arguments)
                response = {
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
                logger.debug(f"Sending response: {response}")
                return response
            elif tool_name == "ddg_search_operators":
                results = get_search_operators()
                response = {
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
                logger.debug(f"Sending response: {response}")
                return response
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}"
                    }
                }
                logger.debug(f"Sending response: {response}")
                return response
        except Exception as e:
            response = {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
            logger.debug(f"Sending response: {response}")
            return response

    # Неизвестный метод
    response = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        }
    }
    logger.debug(f"Sending response: {response}")
    return response

def main():
    """Main server loop"""
    logger.info("Starting DuckDuckGo MCP Server")
    try:
        # Infinite request processing loop
        request_count = 0
        while True:
            try:
                logger.debug(f"Waiting for message #{request_count + 1}")
                message = read_message()
                request_count += 1
                logger.info(f"Received message #{request_count}: {message}")
                
                if message is None:
                    # If message is None, it means EOF or connection closed
                    logger.info("Received None message, exiting loop")
                    break  # Exit the loop gracefully
                
                # Check that message is a dictionary
                if not isinstance(message, dict):
                    logger.warning(f"Received non-dict message: {message}")
                    continue

                logger.info(f"About to call handle_request with message: {message}")
                response = handle_request(message)
                logger.info(f"Generated response: {response}")
                
                if response:
                    logger.info(f"About to send response: {response}")
                    send_message(response)
                    logger.info("Response sent successfully")
                else:
                    logger.info("No response to send")
                    
            except KeyboardInterrupt:
                # Graceful shutdown on Ctrl+C
                logger.info("Server shutdown requested by KeyboardInterrupt")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                import traceback
                traceback.print_exc()
                # Continue processing
                continue
                
    except Exception as e:
        logger.error(f"Error in main: {e}")
        import traceback
        traceback.print_exc()
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
        except Exception as send_error:
            logger.error(f"Failed to send error response: {send_error}")
        finally:
            logger.info("Server shutting down due to error")
        
if __name__ == "__main__":
    main()