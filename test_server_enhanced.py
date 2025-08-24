#!/usr/bin/env python3
"""
Расширенный тестовый скрипт для проверки работы MCP сервера
Поддерживает три режима тестирования:
1. Интерактивный режим (TTY) - для отладки
2. STDIO режим - для тестирования через pipes
3. TCP режим - для тестирования сетевого подключения

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
        print(message)
    except (ValueError, OSError, UnicodeEncodeError, UnicodeDecodeError):
        # Если ошибка I/O, просто пропускаем
        pass
    except Exception:
        # Любые другие ошибки тоже пропускаем
        pass


def send_message_stdio(proc, data):
    """Отправка сообщения в процесс STDIO с корректной обработкой UTF-8"""
    if proc.stdin is None:
        print("⚠️  Ошибка: stdin процесса не доступен")
        return
        
    data_str = json.dumps(data, ensure_ascii=False)
    # Используем длину в байтах, не в символах
    byte_length = len(data_str.encode('utf-8'))
    message = f'{byte_length}\n{data_str}\n'
    print(f"Отправляем STDIO: {data.get('method', 'unknown')}")
    print(f"  Длина в байтах: {byte_length}")
    try:
        proc.stdin.write(message)
        proc.stdin.flush()
        print(f"  ✅ Сообщение отправлено")
    except Exception as e:
        print(f"  ❌ Ошибка отправки: {e}")

def read_message_stdio(proc, timeout=10):
    """Чтение сообщения из процесса STDIO с корректной обработкой UTF-8 и таймаутом"""
    if proc.stdout is None:
        print("⚠️  Ошибка: stdout процесса не доступен")
        return None
        
    try:
        print("  📝 Ожидаем ответ от сервера...")
        
        # Проверяем что процесс еще жив
        if proc.poll() is not None:
            print(f"  ❌ Процесс сервера завершился с кодом: {proc.returncode}")
            return None
        
        # Добавляем таймаут для чтения
        import select
        import os
        
        # На Windows select не работает с pipes, используем другой подход
        if os.name == 'nt':  # Windows
            # Простой подход с коротким ожиданием
            import time
            start_time = time.time()
            
            # Читаем длину в байтах с проверкой таймаута
            length_line = None
            while time.time() - start_time < timeout:
                if proc.poll() is not None:
                    print(f"  ❌ Процесс завершился во время ожидания: {proc.returncode}")
                    return None
                    
                try:
                    # Пытаемся прочитать с очень коротким таймаутом
                    length_line = proc.stdout.readline()
                    if length_line:
                        break
                except:
                    pass
                time.sleep(0.1)
        else:
            # На Unix-подобных системах используем select
            ready, _, _ = select.select([proc.stdout], [], [], timeout)
            if not ready:
                print(f"  ⏰ Таймаут {timeout}с при ожидании ответа сервера")
                return None
            length_line = proc.stdout.readline()
        
        print(f"  Получена длина: {length_line!r}")
        if not length_line:
            print("  ⚠️  Пустая строка длины")
            return None
        
        try:
            byte_length = int(length_line.strip())
            print(f"  Ожидаемая длина сообщения: {byte_length} байт")
        except ValueError:
            print(f"  ❌ Неверный формат длины: {length_line!r}")
            return None
        
        # Читаем сообщение с проверкой таймаута
        if os.name == 'nt':  # Windows
            start_time = time.time()
            message_str = ""
            while len(message_str) < byte_length and time.time() - start_time < timeout:
                if proc.poll() is not None:
                    print(f"  ❌ Процесс завершился во время чтения: {proc.returncode}")
                    return None
                try:
                    chunk = proc.stdout.read(byte_length - len(message_str))
                    if chunk:
                        message_str += chunk
                except:
                    pass
                if len(message_str) < byte_length:
                    time.sleep(0.1) 
        else:
            message_str = proc.stdout.read(byte_length)
            
        if len(message_str) != byte_length:
            print(f"  ⚠️  Ожидалось {byte_length} символов, получено {len(message_str)}")
        
        # Пропускаем \n
        try:
            proc.stdout.read(1)
        except:
            pass
        
        print(f"  Фактически прочитано: {len(message_str)} символов")
        print(f"  Получено сообщение (первые 100 символов): {message_str[:100]!r}...")
        
        # Попробуем распарсить JSON
        try:
            parsed_json = json.loads(message_str)
            print("  ✅ JSON успешно распарсен")
            return parsed_json
        except json.JSONDecodeError as je:
            print(f"  ❌ Ошибка парсинга JSON: {je}")
            print(f"  Проблемный JSON: {message_str}")
            return None
        
    except UnicodeDecodeError as ude:
        print(f"  ❌ Ошибка декодирования Unicode: {ude}")
        return None
    except Exception as e:
        print(f"  ❌ Ошибка чтения STDIO: {e}")
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
                "query": "российские технологии",
                "region": "ru-ru",
                "description": "Технологические новости"
            },
            {
                "id": 5,
                "query": "спорт Россия",
                "region": "ru-ru",
                "description": "Спортивные новости"
            }
        ]
        
        for test_case in russian_queries:
            print(f"\n📰 {test_case['id']}. Поиск: {test_case['description']}")
            print(f"   Запрос: '{test_case['query']}' (регион: {test_case['region']})")
            
            send_message_stdio(proc, {
                "jsonrpc": "2.0",
                "id": test_case['id'],
                "method": "tools/call",
                "params": {
                    "name": "ddg_search_news",
                    "arguments": {
                        "query": test_case['query'],
                        "region": test_case['region'],
                        "max_results": 3
                    }
                }
            })
            
            response = read_message_stdio(proc)
            
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
    
    # Запускаем сервер в режиме STDIO (без TTY)
    try:
        proc = subprocess.Popen(
            [sys.executable, 'ddg_mcp_server.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding='utf-8'
        )
        print(f"✅ Сервер запущен с PID: {proc.pid}")
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
            # Базовый поиск
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "ddg_search_text",
                    "arguments": {
                        "query": "python programming",
                        "max_results": 3
                    }
                }
            },
            # Список инструментов
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/list",
                "params": {}
            }
        ]
        
        responses = []
        
        for i, request in enumerate(requests):
            request["id"] = i + 1
            
            # Проверяем что процесс еще жив
            if proc.poll() is not None:
                print(f"❌ Процесс сервера завершился с кодом: {proc.returncode}")
                break
                
            print(f"\n📤 Отправляем запрос {i+1}/{len(requests)}: {request['method']}")
            send_message_stdio(proc, request)
            
            print(f"📬 Ожидаем ответ на {request['method']}...")
            response = read_message_stdio(proc, timeout=15)  # 15 секунд таймаут
            
            if response:
                responses.append(response)
                print(f"✅ Ответ на {request['method']} (ID: {request['id']}): получен")
                print(f"   Тип ответа: {'result' if 'result' in response else 'error' if 'error' in response else 'unknown'}")
            else:
                print(f"❌ Не удалось получить ответ на {request['method']}")
                responses.append(None)
            
            print("-" * 50)
        
        print(f"\n📊 Результаты STDIO теста:")
        print(f"   Успешных ответов: {len([r for r in responses if r is not None])}/{len(requests)}")
        
        return responses
        
    except Exception as e:
        print(f"❌ Ошибка STDIO теста: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        # Завершаем процесс
        if proc.poll() is None:
            print("🚫 Завершаем сервер...")
            proc.terminate()
            time.sleep(1)
            if proc.poll() is None:
                print("⚡ Принудительное завершение...")
                proc.kill()

def run_tcp_test():
    """Тестирование через TCP"""
    print("Тестовый клиент для TCP сервера")
    print("="*40)
    
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
        
        # Тест 4: Поиск новостей на русском языке
        print("\nТест 4: Поиск новостей 'новости России'")
        news_request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "ddg_search_news",
                "arguments": {
                    "query": "новости России",
                    "region": "ru-ru",
                    "max_results": 2
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
    print('{"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "ddg_search_news", "arguments": {"query": "новости России", "region": "ru-ru", "max_results": 3}}}')
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
        
        print("3. TCP тест (пропускаем - требует работающий TCP сервер):")
        print("⚠️  TCP тест пропущен - запустите 'python tcp_ddg_server.py' для теста")
        
        try:
            print("\n" + "="*60 + "\n")
        except (ValueError, OSError):
            pass
        
        print("4. Краткий тест русских новостей:")
        try:
            # Очень краткий тест - просто проверяем import
            from ddg_mcp_server import fix_encoding
            test_text = "РьРѕРІРµСЃС‚Ри"  # Поврежденная кодировка
            fixed = fix_encoding(test_text)
            
            # Безопасный вывод с обработкой ошибок I/O
            safe_print(f"✅ Функция fix_encoding работает: '{test_text[:20]}...' -> '{fixed[:20]}...'")
            safe_print("DEBUG: Encoding test completed")
        except Exception as e:
            # Безопасный вывод ошибки
            error_msg = str(e)[:100] if len(str(e)) > 100 else str(e)
            safe_print(f"DEBUG: Encoding test failed: {error_msg}...")
        
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