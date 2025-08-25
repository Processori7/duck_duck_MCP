#!/usr/bin/env python3
"""
Расширенный тестовый скрипт для проверки работы MCP сервера
Поддерживает три режима тестирования:
1. Интерактивный режим (TTY) - для отладки
2. STDIO режим - для тестирования через pipes
3. TCP режим - для тестирования сетевого подключения
4. All режим - для тестирования всех возможностей
Включает тесты с русским языком для проверки кодировки.
"""

import json
import subprocess
import sys
import socket
import threading
import time
import io
from datetime import datetime

# Настройка кодировки UTF-8 для Windows
if sys.platform == "win32":
    try:
        import io
        # Проверяем, что потоки не закрыты перед переназначением
        if not sys.stdin.closed:
            sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
        if not sys.stdout.closed:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        if not sys.stderr.closed:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
    except (AttributeError, ValueError, OSError):
        # Если не удается переназначить потоки, используем стандартные
        pass


def safe_print(message):
    """Безопасный вывод с обработкой I/O ошибок"""
    try:
        print(message, flush=True)  # Принудительная отправка вывода
    except (ValueError, OSError, UnicodeEncodeError, UnicodeDecodeError):
        # Если ошибка I/O, попробуем записать в stderr
        try:
            import sys
            sys.stderr.write(f"SAFE_PRINT: {str(message)}\n")
            sys.stderr.flush()
        except:
            # Если и stderr недоступен, просто пропускаем
            pass
    except Exception:
        # Любые другие ошибки тоже пропускаем
        pass


def send_message_stdio(proc, data):
    """Отправка сообщения в процесс STDIO с корректной обработкой UTF-8"""
    try:
        data_str = json.dumps(data, ensure_ascii=False)
        # Используем длину в байтах, не в символах
        data_bytes = data_str.encode('utf-8')
        byte_length = len(data_bytes)
        
        # Формируем сообщение в байтах: длина\n + данные + \n
        length_bytes = f'{byte_length}\n'.encode('utf-8')
        newline_bytes = b'\n'
        message_bytes = length_bytes + data_bytes + newline_bytes
        
        print(f"Отправляем STDIO: {data.get('method', 'unknown')}")
        print(f"  Длина в байтах: {byte_length}")
        
        # Записываем байты напрямую в stdin (stdin уже в бинарном режиме)
        proc.stdin.write(message_bytes)
        proc.stdin.flush()
        print(f"  ✅ Сообщение отправлено")
        
    except Exception as e:
        print(f"  ❌ Ошибка отправки: {e}")

def read_message_stdio(proc, timeout=10):
    """Чтение сообщения с байт-левел коммуникацией"""
    if proc.stdout is None:
        print("⚠️  Ошибка: stdout процесса не доступен")
        return None
        
    try:
        print("  📝 Ожидаем ответ от сервера...")
        
        if proc.poll() is not None:
            print(f"  ❌ Процесс завершился: {proc.returncode}")
            return None
        
        # Читаем длину сообщения
        length_line = b''
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if proc.poll() is not None:
                return None
                
            try:
                # Читаем по одному байту до \n
                byte_char = proc.stdout.read(1)
                if not byte_char:
                    time.sleep(0.01)
                    continue
                    
                length_line += byte_char
                if byte_char == b'\n':
                    break
                    
            except Exception:
                time.sleep(0.01)
                continue
        
        if not length_line or length_line == b'\n':
            print(f"  ⏰ Таймаут {timeout}с - не получена длина")
            return None
        
        try:
            # Убираем \n и декодируем длину
            length_str = length_line.rstrip(b'\n').decode('utf-8')
            byte_length = int(length_str)
            print(f"  Ожидаем {byte_length} байт")
        except (ValueError, UnicodeDecodeError) as e:
            print(f"  ❌ Неверная длина: {length_line!r} - {e}")
            return None
        
        # Читаем сообщение указанной длины
        message_bytes = b""
        start_time = time.time()
        
        while len(message_bytes) < byte_length and time.time() - start_time < timeout:
            if proc.poll() is not None:
                return None
                
            try:
                remaining = byte_length - len(message_bytes)
                # Читаем оставшиеся байты (но не больше 1024 за раз)
                chunk_size = min(remaining, 1024)
                chunk = proc.stdout.read(chunk_size)
                
                if chunk:
                    message_bytes += chunk
                else:
                    time.sleep(0.01)
                    
            except Exception:
                break
        
        if len(message_bytes) < byte_length:
            print(f"  ❌ Получено только {len(message_bytes)} из {byte_length} байт")
            return None
        
        # Читаем завершающий \n
        try:
            trailing_newline = proc.stdout.read(1)
            if trailing_newline != b'\n':
                print(f"  ⚠️ Ожидался \\n, получен: {trailing_newline!r}")
        except:
            pass
        
        # Декодируем сообщение
        try:
            message_str = message_bytes.decode('utf-8')
        except UnicodeDecodeError as e:
            print(f"  ❌ Ошибка UTF-8: {e}")
            return None
        
        print(f"  Получено: {len(message_bytes)} байт")
        
        # Парсим JSON
        try:
            parsed_json = json.loads(message_str)
            print("  ✅ JSON распарсен")
            return parsed_json
        except json.JSONDecodeError as e:
            print(f"  ❌ JSON ошибка: {e}")
            print(f"  Сырые данные: {message_str[:100]}...")
            return None
        
    except Exception as e:
        print(f"  ❌ Ошибка STDIO: {e}")
        import traceback
        traceback.print_exc()
        return None

def send_message_tcp(sock, data):
    """Отправка сообщения через TCP"""
    data_str = json.dumps(data, ensure_ascii=False)
    data_bytes = data_str.encode('utf-8')
    message = f'{len(data_bytes)}\n'.encode('utf-8') + data_bytes + b'\n'
    print(f"Отправляем TCP: {data.get('method', 'unknown')}")
    sock.sendall(message)

def read_message_tcp(sock, timeout=5.0):
    """Чтение сообщения через TCP"""
    try:
        # Устанавливаем таймаут для операции чтения
        sock.settimeout(timeout)
        
        # Читаем длину
        length_bytes = b''
        while b'\n' not in length_bytes:
            chunk = sock.recv(1)
            if not chunk:
                return None
            length_bytes += chunk
        
        length = int(length_bytes.decode('utf-8').strip())
        print(f"TCP - Ожидаемая длина сообщения: {length} байт")
        
        # Читаем сообщение
        content_bytes = b''
        while len(content_bytes) < length:
            remaining = length - len(content_bytes)
            chunk = sock.recv(min(remaining, 4096))
            if not chunk:
                return None
            content_bytes += chunk
        
        # Пропускаем \n после сообщения
        sock.recv(1)
        
        content = content_bytes.decode('utf-8')
        print(f"TCP - Получено сообщение ({len(content)} символов)")
        return json.loads(content)
    except socket.timeout:
        print(f"TCP - Таймаут при чтении (timeout={timeout}с)")
        return None
    except Exception as e:
        print(f"TCP - Ошибка чтения: {e}")
        return None

def display_search_results(results, search_type="search"):
    """Красиво выводит результаты поиска в консоль"""
    if not results:
        print("  ❌ Результаты не найдены")
        return
    
    print(f"  ✅ Найдено {len(results)} результатов:")
    print("  " + "="*60)
    
    for i, result in enumerate(results, 1):
        print(f"  📄 Результат {i}:")
        
        if 'title' in result:
            print(f"     🏷️  Заголовок: {result['title']}")
        
        if 'body' in result:
            body = result['body'][:150] + "..." if len(result.get('body', '')) > 150 else result.get('body', '')
            print(f"     📝 Описание: {body}")
        
        if 'url' in result:
            print(f"     🔗 URL: {result['url']}")
        elif 'href' in result:
            print(f"     🔗 URL: {result['href']}")
            
        if 'date' in result:
            print(f"     📅 Дата: {result['date']}")
            
        if 'source' in result:
            print(f"     📰 Источник: {result['source']}")
            
        if '_note' in result:
            print(f"     ℹ️  Примечание: {result['_note']}")
            
        print("  " + "-"*60)

def run_russian_news_test():
    """Специальный тест для русских новостей"""
    print("\n🇷🇺 === ТЕСТ РУССКИХ НОВОСТЕЙ === 🇷🇺")
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    print("\n🚀 Запускаем MCP сервер...")
    
    # Запускаем сервер в режиме STDIO
    try:
        proc = subprocess.Popen(
            [sys.executable, 'ddg_mcp_server.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8',
            errors='replace',
            bufsize=0  # Отключаем буферизацию
        )
        print(f"  ✅ Сервер запущен с PID: {proc.pid}")
    except Exception as e:
        print(f"  ❌ Ошибка запуска сервера: {e}")
        return
    
    # Проверяем, что процесс жив
    if proc.poll() is not None:
        print(f"  ❌ Сервер немедленно завершился с кодом: {proc.returncode}")
        return
    
    # Короткая пауза для стабилизации
    time.sleep(0.5)
    
    try:
        # 1. Инициализация
        print("\n📋 1. Инициализация сервера...")
        send_message_stdio(proc, {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        })
        
        response = read_message_stdio(proc)
        if response and 'result' in response:
            print("   ✅ Сервер инициализирован успешно")
        else:
            print(f"   ❌ Ошибка инициализации: {response}")
            return
        
        # 2. Тестовые запросы с русскими новостями
        russian_queries = [
            {
                "id": 2,
                "query": "новости России",
                "region": "ru-ru",
                "description": "Общие новости России"
            },
            {
                "id": 3,
                "query": "последние новости Москвы",
                "region": "ru-ru", 
                "description": "Новости столицы"
            },
            {
                "id": 4,
                "query": "Какие новости сегодня",
                "region": "ru-ru",
                "timelimit": "d",
                "description": "Сегодняшние новости (улучшенный тест)"
            },
            {
                "id": 5,
                "query": "Какие технологии в моде",
                "region": "ru-ru",
                "description": "Технологические новости"
            }
        ]
        
        for test_case in russian_queries:
            print(f"\n📰 {test_case['id']}. Поиск: {test_case['description']}")
            print(f"   Запрос: '{test_case['query']}' (регион: {test_case['region']})")
            
            # Подготовка запроса
            request_params = {
                "query": test_case['query'],
                "region": test_case['region'],
                "max_results": 3
            }
            
            # Добавляем timelimit если он указан
            if 'timelimit' in test_case:
                request_params['timelimit'] = test_case['timelimit']
                print(f"   Ограничение по времени: {test_case['timelimit']} (только сегодняшние)")
            
            # Отправка запроса с увеличенным таймаутом
            send_message_stdio(proc, {
                "jsonrpc": "2.0",
                "id": test_case['id'],
                "method": "tools/call",
                "params": {
                    "name": "ddg_search_news",
                    "arguments": request_params
                }
            })
            
            # Чтение ответа с увеличенным таймаутом для новостей
            timeout = 30 if test_case['id'] == 4 else 15  # Больше времени для сегодняшних новостей
            response = read_message_stdio(proc, timeout=timeout)
            
            if response and 'result' in response:
                try:
                    content = response['result']['content'][0]['text']
                    results = json.loads(content)
                    display_search_results(results, "news")
                except (KeyError, json.JSONDecodeError, IndexError) as e:
                    print(f"   ❌ Ошибка обработки результатов: {e}")
                    print(f"   📄 Сырой ответ: {response}")
            elif response and 'error' in response:
                print(f"   ❌ Ошибка поиска: {response['error']}")
            else:
                print(f"   ❌ Неожиданный ответ: {response}")
            
            # Небольшая пауза между запросами
            time.sleep(1)
        
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        print(f"\n🔚 Завершение теста: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Завершаем процесс
        if proc.poll() is None:
            print("  🚫 Завершаем сервер...")
            proc.terminate()
            time.sleep(1)
            if proc.poll() is None:
                print("  ⚡ Принудительное завершение...")
                proc.kill()
        
        # Выводим stderr сервера для диагностики
        try:
            if proc.stderr is not None:
                stderr_output = proc.stderr.read()
                if stderr_output:
                    print(f"\n📋 STDERR сервера:\n{stderr_output}")
                else:
                    print("\n📋 STDERR сервера: пуст")
        except Exception as e:
            print(f"\n⚠️  Ошибка чтения stderr: {e}")

def run_stdio_test():
    """Тестирование через STDIO с таймаутом"""
    print("=== Тестирование STDIO ===")
    
    # Запускаем сервер в режиме STDIO с байт-левел коммуникацией
    try:
        proc = subprocess.Popen(
        [sys.executable, 'ddg_mcp_server.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0
    )
        print(f"✅ Сервер запущен с PID: {proc.pid}")
        
        # Короткая пауза для стабилизации
        time.sleep(1.0)
        
    except Exception as e:
        print(f"❌ Ошибка запуска сервера: {e}")
        return None
    
    try:
        # Последовательность тестовых запросов
        requests = [
            # Initialize запрос
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            },
            # Список инструментов
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            },
            # Базовый поиск
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "ddg_search_text",
                    "arguments": {
                        "query": "python programming",
                        "max_results": 3
                    }
                }
            },
            # Русский поиск новостей
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {
                    "name": "ddg_search_news",
                    "arguments": {
                        "query": "Какие новости сегодня",
                        "region": "ru-ru",
                        "timelimit": "d",
                        "max_results": 3
                    }
                }
            }
        ]
        
        responses = []
        start_time = time.time()
        max_test_time = 120  # 2 минуты максимум
        
        for i, request in enumerate(requests):
            # Проверка общего таймаута
            if time.time() - start_time > max_test_time:
                print(f"⏰ Общий таймаут теста превышен")
                break
            
            # Проверяем что процесс еще жив
            if proc.poll() is not None:
                print(f"❌ Процесс сервера завершился с кодом: {proc.returncode}")
                break
                
            print(f"\n📤 Отправляем запрос {i+1}/{len(requests)}: {request['method']}")
            
            try:
                send_message_stdio(proc, request)
                
                print(f"📬 Ожидаем ответ на {request['method']}...")
                # Увеличиваем таймаут для поисковых запросов
                timeout = 30 if 'tools/call' in request['method'] else 10
                response = read_message_stdio(proc, timeout=timeout)
                
                if response:
                    responses.append(response)
                    print(f"✅ Ответ на {request['method']} (ID: {request.get('id')}): получен")
                    print(f"   Тип ответа: {'result' if 'result' in response else 'error' if 'error' in response else 'unknown'}")
                    
                    # Обработка результатов поиска
                    if 'result' in response and request['method'] == 'tools/call':
                        try:
                            content = response['result']['content'][0]['text']
                            search_results = json.loads(content)
                            if request['params']['name'] == 'ddg_search_news':
                                print(f"   📰 Найдено новостей: {len(search_results) if search_results else 0}")
                                if search_results:
                                    for j, result in enumerate(search_results[:2], 1):
                                        title = result.get('title', 'Без заголовка')[:60]
                                        source = result.get('source', 'Неизвестный источник')
                                        print(f"     {j}. {title}... ({source})")
                            else:
                                print(f"   🔍 Найдено результатов: {len(search_results) if search_results else 0}")
                        except (KeyError, json.JSONDecodeError, IndexError) as e:
                            print(f"   ⚠️ Ошибка обработки результатов: {e}")
                            
                else:
                    print(f"❌ Не удалось получить ответ на {request['method']}")
                    responses.append(None)
                    
            except Exception as e:
                print(f"❌ Ошибка выполнения запроса: {str(e)[:100]}")
                responses.append(None)
            
            print("-" * 50)
            time.sleep(0.5)  # Пауза между запросами
        
        print(f"\n📊 Результаты STDIO теста:")
        successful_responses = len([r for r in responses if r is not None])
        print(f"   Успешных ответов: {successful_responses}/{len(requests)}")
        print(f"   Процент успеха: {(successful_responses/len(requests)*100):.1f}%")
        
        return responses
        
    except Exception as e:
        print(f"❌ Ошибка STDIO теста: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Завершаем процесс
        try:
            if proc and proc.poll() is None:
                print("🚫 Завершаем сервер...")
                proc.terminate()
                time.sleep(1)
                if proc.poll() is None:
                    print("⚡ Принудительное завершение...")
                    proc.kill()
        except:
            pass

def run_tcp_test():
    """Тестирование через TCP"""
    print("Тестовый клиент для TCP сервера")
    print("="*40)
    
    client = None  # Инициализируем переменную для безопасности
    
    try:
        # Подключаемся к серверу
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5.0)  # 5 секунд таймаут
        
        print("Подключение к серверу 127.0.0.1:8765...")
        client.connect(('127.0.0.1', 8765))
        print("✓ Подключено!")
        
        # Тест 1: Инициализация
        print("\nТест 1: Инициализация")
        init_request = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            },
            "id": 1
        }
        send_message_tcp(client, init_request)
        
        response = read_message_tcp(client)
        if response:
            print(f"✓ Получен ответ: {response.get('result', {}).get('protocolVersion', 'unknown')}")
        else:
            print("✗ Нет ответа")
        
        # Тест 2: Список инструментов
        print("\nТест 2: Получение списка инструментов")
        tools_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": {},
            "id": 2
        }
        send_message_tcp(client, tools_request)
        
        response = read_message_tcp(client)
        if response and 'result' in response:
            tools = response['result'].get('tools', [])
            print(f"✓ Получено инструментов: {len(tools)}")
            for tool in tools:
                print(f"  - {tool['name']}")
        else:
            print("✗ Нет ответа")
        
        # Тест 3: Простой поиск
        print("\nТест 3: Тестовый поиск 'Python tutorial'")
        search_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ddg_search_text",
                "arguments": {
                    "query": "Python tutorial",
                    "max_results": 2
                }
            },
            "id": 3
        }
        send_message_tcp(client, search_request)
        
        # Увеличиваем таймаут для поиска, так как он может занять время
        response = read_message_tcp(client, timeout=30.0)
        if response and 'result' in response:
            content = response['result'].get('content', [])
            if content:
                print(f"✓ Получено результатов: {len(content)}")
                for item in content:
                    if item.get('type') == 'text':
                        # Выводим только первые 100 символов
                        text = item.get('text', '')[:100]
                        print(f"  Результат: {text}...")
            else:
                print("✓ Запрос выполнен, но результатов нет")
        else:
            print("✗ Нет ответа")
        
        # Тест 4: Поиск сегодняшних новостей на русском языке
        print("\nТест 4: Поиск новостей 'Какие новости сегодня'")
        news_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ddg_search_news",
                "arguments": {
                    "query": "Какие новости сегодня",
                    "region": "ru-ru",
                    "timelimit": "d",
                    "max_results": 3
                }
            },
            "id": 4
        }
        send_message_tcp(client, news_request)
        
        response = read_message_tcp(client, timeout=30.0)
        if response and 'result' in response:
            content = response['result'].get('content', [])
            if content:
                print(f"✓ Получено результатов: {len(content)}")
                for item in content:
                    if item.get('type') == 'text':
                        text = item.get('text', '')[:100]
                        print(f"  Результат: {text}...")
            else:
                print("✓ Запрос выполнен, но результатов нет")
        else:
            print("✗ Нет ответа")
        
        print("\n" + "="*40)
        print("Тестирование завершено успешно!")
        
    except ConnectionRefusedError:
        print("✗ Не удалось подключиться к серверу!")
        print("Убедитесь, что TCP сервер запущен (python tcp_ddg_server.py)")
        return None
    except Exception as e:
        print(f"✗ Ошибка: {e}")
        return None
    finally:
        if client is not None:
            try:
                client.close()
                print("Соединение закрыто")
            except:
                pass

def run_interactive_test():
    """Интерактивное тестирование (имитация ручного ввода)"""
    print("=== Интерактивное тестирование ===")
    print("Для тестирования в интерактивном режиме запустите:")
    print("  python ddg_mcp_server.py")
    print("Затем введите следующие запросы по одному:")
    print()
    print("1. Initialize:")
    print('{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}')
    print()
    print("2. Tools list:")
    print('{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}')
    print()
    print("3. Search:")
    print('{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "ddg_search_text", "arguments": {"query": "python programming", "max_results": 3}}}')
    print()
    print("4. Русский поиск новостей:")
    print('{"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "ddg_search_news", "arguments": {"query": "Какие новости сегодня", "region": "ru-ru", "timelimit": "d", "max_results": 3}}}')
    print()
    print("Для выхода введите: quit")

def main():
    print("🔧 === ЗАПУСК ТЕСТОВОГО СКРИПТА ===")
    print(f"Аргументы командной строки: {sys.argv}")
    try:
        print("DEBUG: main() function started")
    except (ValueError, OSError):
        pass
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python test_server_enhanced.py stdio     - тестирование через STDIO")
        print("  python test_server_enhanced.py tcp       - тестирование через TCP")
        print("  python test_server_enhanced.py interactive - интерактивное тестирование")
        print("  python test_server_enhanced.py russian   - тест русских новостей")
        print("  python test_server_enhanced.py all       - все тесты")
        try:
            print("DEBUG: Returning due to no arguments")
        except (ValueError, OSError):
            pass
        return
    
    test_type = sys.argv[1]
    print(f"Выбранный тип теста: {test_type}")
    try:
        print(f"DEBUG: Processing test type: {test_type}")
    except (ValueError, OSError):
        pass
    
    if test_type == "stdio":
        print("🚀 Запуск STDIO теста...")
        run_stdio_test()
    elif test_type == "tcp":
        print("🚀 Запуск TCP теста...")
        run_tcp_test()
    elif test_type == "interactive":
        print("🚀 Запуск интерактивного теста...")
        run_interactive_test()
    elif test_type == "russian":
        print("🚀 Запуск теста русских новостей...")
        run_russian_news_test()
    elif test_type == "all":
        print("🚀 Запуск всех тестов...")
        try:
            print("DEBUG: About to start test sequence")
        except (ValueError, OSError):
            pass
        
        print("1. Интерактивный тест:")
        try:
            run_interactive_test()
            print("DEBUG: Interactive test completed")
        except Exception as e:
            print(f"DEBUG: Interactive test failed: {e}")
        
        try:
            print("\n" + "="*60 + "\n")
        except (ValueError, OSError):
            pass
        
        print("2. Краткий тест сервера (без STDIO):")
        try:
            # Простой тест - проверяем что сервер запускается
            proc = subprocess.Popen(
                [sys.executable, 'ddg_mcp_server.py'],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding='utf-8'
            )
            print(f"✅ Сервер запустился с PID: {proc.pid}")
            
            # Просто проверяем что он работает 2 секунды
            time.sleep(2)
            if proc.poll() is None:
                print("✅ Сервер работает стабильно")
            else:
                print(f"❌ Сервер завершился с кодом: {proc.returncode}")
            
            proc.terminate()
            print("DEBUG: Simple server test completed")
        except Exception as e:
            print(f"DEBUG: Simple server test failed: {e}")
        
        try:
            print("\n" + "="*60 + "\n")
        except (ValueError, OSError):
            pass
        
        try:
            # Connect to server
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            
            print("📡 Connecting to 127.0.0.1:8765...")
            sock.connect(('127.0.0.1', 8765))
            print("✅ Connection established!")
            
            # Send initialize request
            init_request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "roots": {
                            "listChanged": True
                        }
                    },
                    "clientInfo": {
                        "name": "test-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            print("📤 Sending initialize request...")
            message = json.dumps(init_request, ensure_ascii=False).encode('utf-8') + b'\n'
            sock.sendall(message)
            
            # Read response
            print("📥 Reading response...")
            response_data = b''
            while True:
                chunk = sock.recv(1)
                if not chunk or chunk == b'\n':
                    break
                response_data += chunk
                
            if response_data:
                response = json.loads(response_data.decode('utf-8'))
                print(f"✅ Received response:")
                print(json.dumps(response, indent=2, ensure_ascii=False))
                
                # Test tools/list
                tools_request = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list"
                }
                
                print("\n📤 Sending tools/list request...")
                message = json.dumps(tools_request, ensure_ascii=False).encode('utf-8') + b'\n'
                sock.sendall(message)
                
                # Read tools response
                response_data = b''
                while True:
                    chunk = sock.recv(1)
                    if not chunk or chunk == b'\n':
                        break
                    response_data += chunk
                    
                if response_data:
                    response = json.loads(response_data.decode('utf-8'))
                    print(f"✅ Tools list received:")
                    print(json.dumps(response, indent=2, ensure_ascii=False))
                    
            sock.close()
            print("\n🎉 TCP server test completed successfully!")
        except Exception as e:
            print(f"❌ TCP server test failed: {e}")
            print("⚠️  TCP тест пропущен - запустите 'python tcp_ddg_server.py' для теста")
        
        try:
            print("\n" + "="*60 + "\n")
        except (ValueError, OSError):
            pass
        
        print("4. Краткий тест русских новостей:")
        safe_print("🚀 Запуск полного MCP теста с 4 запросами...")
        
        proc = None  # Инициализируем переменную
        test_start_time = time.time()
        max_test_time = 60  # Максимальное время теста 60 секунд
        
        try:
            # Проверка общего таймаута
            if time.time() - test_start_time > max_test_time:
                safe_print("⏰ Общий таймаут теста превышен, пропускаем MCP тест")
                return
            
            # Запускаем сервер для полного MCP тестирования
            proc = subprocess.Popen(
            [sys.executable, 'ddg_mcp_server.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8'
        )
            safe_print(f"✅ Сервер запущен с PID: {proc.pid}")
            
            # Короткая пауза для стабилизации
            time.sleep(1.0)  # Увеличенная пауза
            
            # Проверяем что сервер запустился
            server_ready = True
            if proc.poll() is not None:
                safe_print(f"❌ Сервер немедленно завершился с кодом: {proc.returncode}")
                # Выводим stderr для диагностики
                try:
                    if proc.stderr is not None:
                        stderr_output = proc.stderr.read()
                        if stderr_output:
                            safe_print(f"📋 STDERR: {stderr_output[:200]}...")
                except:
                    pass
                safe_print("⚠️ Сервер не запустился, но попробуем выполнить тесты...")
                server_ready = False
            else:
                safe_print("✅ Сервер работает, начинаем MCP тесты...")
            
            # Выполняем MCP тесты даже если сервер не прошел первоначальную проверку
            if server_ready or True:  # Всегда пытаемся выполнить тесты
                # Последовательность тестовых запросов
                test_requests = [
                    {
                        "request": {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
                        "description": "1. Initialize",
                        "timeout": 10
                    },
                    {
                        "request": {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                        "description": "2. Tools list",
                        "timeout": 10
                    },
                    {
                        "request": {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "ddg_search_text", "arguments": {"query": "python programming", "max_results": 1}}},
                        "description": "3. Search",
                        "timeout": 20
                    },
                    {
                        "request": {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "ddg_search_news", "arguments": {"query": "Какие новости сегодня", "region": "ru-ru", "timelimit": "d", "max_results": 3}}},
                        "description": "4. Русский поиск новостей",
                        "timeout": 30
                    }
                ]
                
                # Выполняем все запросы последовательно
                for i, test_case in enumerate(test_requests):
                    # Проверка общего таймаута
                    if time.time() - test_start_time > max_test_time:
                        safe_print(f"⏰ Общий таймаут теста превышен на шаге {i+1}")
                        break
                        
                    safe_print(f"\n📤 {test_case['description']}")
                    
                    # Проверяем что процесс еще жив
                    if proc.poll() is not None:
                        safe_print(f"❌ Сервер завершился с кодом: {proc.returncode}")
                        break
                    
                    try:
                        # Отправляем запрос с коротким таймаутом
                        request_start = time.time()
                        send_message_stdio(proc, test_case['request'])
                        
                        # Проверка таймаута отправки
                        if time.time() - request_start > 5:  # 5 секунд на отправку
                            safe_print(f"⏰ Таймаут отправки запроса")
                            continue
                        
                        # Читаем ответ с уменьшенным таймаутом
                        reduced_timeout = min(test_case['timeout'], 15)  # Максимум 15 секунд
                        response = read_message_stdio(proc, timeout=reduced_timeout)
                        
                        if response:
                            if 'result' in response:
                                safe_print(f"✅ Ответ получен (ID: {response.get('id')})")
                                
                                # Специальная обработка для разных типов ответов
                                if test_case['request']['method'] == 'initialize':
                                    safe_print(f"   Протокол: {response['result'].get('protocolVersion', 'неизвестно')}")
                                    
                                elif test_case['request']['method'] == 'tools/list':
                                    tools = response['result'].get('tools', [])
                                    safe_print(f"   Найдено инструментов: {len(tools)}")
                                    for tool in tools[:3]:  # Показываем первые 3
                                        safe_print(f"     - {tool.get('name', 'без имени')}")
                                        
                                elif test_case['request']['method'] == 'tools/call':
                                    try:
                                        content = response['result']['content'][0]['text']
                                        if test_case['request']['params']['name'] == 'ddg_search_news':
                                            # Парсим результаты новостей
                                            results = json.loads(content)
                                            if results and len(results) > 0:
                                                safe_print(f"   📰 Найдено новостей: {len(results)}")
                                                for j, result in enumerate(results[:2], 1):
                                                    title = result.get('title', 'Без заголовка')[:60]
                                                    source = result.get('source', 'Неизвестный источник')
                                                    safe_print(f"     {j}. {title}... ({source})")
                                            else:
                                                safe_print("   ⚠️ Новости не найдены")
                                        else:
                                            # Обычный текстовый поиск
                                            results = json.loads(content)
                                            if results and len(results) > 0:
                                                safe_print(f"   🔍 Найдено результатов: {len(results)}")
                                                for j, result in enumerate(results[:2], 1):
                                                    title = result.get('title', 'Без заголовка')[:60]
                                                    safe_print(f"     {j}. {title}...")
                                            else:
                                                safe_print("   ⚠️ Результаты не найдены")
                                    except (KeyError, json.JSONDecodeError, IndexError) as e:
                                        safe_print(f"   ⚠️ Ошибка обработки результатов: {e}")
                                        safe_print(f"   📄 Сырой ответ: {str(response)[:100]}...")
                                        
                            elif 'error' in response:
                                safe_print(f"❌ Ошибка сервера: {response['error']}")
                            else:
                                safe_print(f"⚠️ Неожиданный формат ответа: {str(response)[:100]}...")
                        else:
                            safe_print(f"❌ Нет ответа (таймаут {test_case['timeout']}с)")
                            
                    except Exception as e:
                        safe_print(f"❌ Ошибка выполнения запроса: {str(e)[:100]}")
                    
                    # Проверка общего таймаута после каждого теста
                    if time.time() - test_start_time > max_test_time:
                        safe_print(f"⏰ Общий таймаут теста превышен после шага {i+1}")
                        break
                    
                    # Короткая пауза между запросами
                    time.sleep(0.2)  # Уменьшенная пауза для ускорения
                
                safe_print("\n✅ Все MCP запросы выполнены")
            
        except Exception as e:
            error_msg = str(e)[:100] if len(str(e)) > 100 else str(e)
            safe_print(f"❌ Ошибка теста: {error_msg}")
            
        finally:
            # Убеждаемся что процесс завершен
            try:
                if proc is not None and proc.poll() is None:
                    safe_print("🚫 Завершаем сервер...")
                    proc.terminate()
                    time.sleep(0.5)
                    if proc.poll() is None:
                        proc.kill()
                safe_print("✅ Тест завершен")
            except:
                pass
        
        try:
            print("\n" + "="*60 + "\n")
        except (ValueError, OSError):
            # Если ошибка I/O, просто пропускаем
            pass
        try:
            print("Все тесты завершены (упрощенная версия).")
            print("📝 Для полного теста используйте:")
            print("   python test_server_enhanced.py russian   - для полного теста русских новостей")
            print("   python test_server_enhanced.py stdio     - для STDIO теста")
        except (ValueError, OSError):
            # Если ошибка I/O, просто пропускаем
            pass
        try:
            print("DEBUG: All tests sequence completed")
        except (ValueError, OSError):
            # Если ошибка I/O, просто пропускаем
            pass
    else:
        print(f"❌ Неизвестный тип теста: {test_type}")
        print("Доступные типы: stdio, tcp, interactive, russian, all")
    
    try:
        print("\n✅ ТЕСТОВЫЙ СКРИПТ ЗАВЕРШЕН")
        print("DEBUG: main() function completed successfully")
    except (ValueError, OSError):
        # Если ошибка I/O, просто пропускаем
        pass

if __name__ == "__main__":
    main()