#!/usr/bin/env python3
"""
Расширенный тестовый скрипт для проверки работы MCP сервера
Поддерживает три режима тестирования:
1. Интерактивный режим (TTY) - для отладки
2. STDIO режим - для тестирования через pipes
3. TCP режим - для тестирования сетевого подключения
"""

import json
import subprocess
import sys
import socket
import threading
import time


def send_message_stdio(proc, data):
    """Отправка сообщения в процесс STDIO"""
    data_str = json.dumps(data, ensure_ascii=False)
    message = f'{len(data_str)}\n{data_str}\n'
    print(f"Отправляем STDIO: {message!r}")
    proc.stdin.write(message)
    proc.stdin.flush()

def read_message_stdio(proc):
    """Чтение сообщения из процесса STDIO"""
    try:
        # Читаем длину
        length_line = proc.stdout.readline()
        print(f"Получена длина: {length_line!r}")
        if not length_line:
            return None
        
        length = int(length_line.strip())
        print(f"Ожидаемая длина сообщения: {length} символов")
        
        # Читаем сообщение
        # Так как proc открыт с text=True, read() возвращает строку
        message_str = proc.stdout.read(length)
        print(f"Фактически прочитано: {len(message_str)} символов")
        print(f"Получено сообщение (первые 200 символов): {message_str[:200]!r}...")
        
        # Пропускаем 
        newline_char = proc.stdout.read(1)
        print(f"Пропущенный символ: {newline_char!r}")
        
        # Попробуем распарсить JSON
        try:
            parsed_json = json.loads(message_str)
            print("JSON успешно распарсен")
            return parsed_json
        except json.JSONDecodeError as je:
            print(f"Ошибка парсинга JSON: {je}")
            print(f"Проблемный JSON (первые 200 символов): {message_str[:200]!r}...")
            return None
        
    except UnicodeDecodeError as ude:
        print(f"Ошибка декодирования Unicode: {ude}")
        print(f"Позиция ошибки: {ude.start}")
        # Попробуем прочитать байты напрямую для отладки
        # Это сложно сделать с text=True, поэтому просто сообщим об ошибке
        return None
    except Exception as e:
        print(f"Ошибка чтения STDIO: {e}")
        import traceback
        traceback.print_exc()
        # Выводим stderr сервера для отладки
        stderr_output = proc.stderr.read()
        if stderr_output:
            print(f"STDERR сервера:\n{stderr_output}")
        return None

def send_message_tcp(sock, data):
    """Отправка сообщения через TCP"""
    data_str = json.dumps(data, ensure_ascii=False)
    message = f'{len(data_str)}\n{data_str}\n'
    print(f"Отправляем TCP: {message!r}")
    sock.sendall(message.encode('utf-8'))

def read_message_tcp(sock):
    """Чтение сообщения через TCP"""
    try:
        # Читаем длину
        length_bytes = b''
        while b'\n' not in length_bytes:
            chunk = sock.recv(1)
            if not chunk:
                return None
            length_bytes += chunk
        length_str = length_bytes.decode('utf-8').strip()
        print(f"TCP - Получена длина: {length_str!r}")
        
        # Проверяем, что длина не пустая
        if not length_str:
            print("TCP - Получена пустая строка вместо длины сообщения")
            return None
        
        # Читаем сообщение
        length = int(length_str)
        print(f"TCP - Ожидаемая длина сообщения: {length} байт")
        content_bytes = b''
        while len(content_bytes) < length:
            chunk = sock.recv(length - len(content_bytes))
            if not chunk:
                print("TCP - Получен пустой чанк при чтении сообщения")
                return None
            content_bytes += chunk
            
        content = content_bytes.decode('utf-8')
        print(f"TCP - Получено сообщение (первые 200 символов): {content[:200]!r}...")
        # Пропускаем \n после сообщения
        sock.recv(1)
        
        return json.loads(content)
    except ValueError as e:
        print(f"TCP - Ошибка преобразования длины: {e}")
        return None
    except Exception as e:
        print(f"TCP - Ошибка чтения: {e}")
        return None

def run_stdio_test():
    """Тестирование через STDIO"""
    print("=== Тестирование STDIO ===")
    
    # Запускаем сервер в режиме STDIO (без TTY)
    proc = subprocess.Popen(
        [sys.executable, 'ddg_mcp_server.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8'
    )
    
    try:
        # Последовательность тестовых запросов
        # Включаем тесты из оригинального test_server.py
        requests = [
            # Initialize запрос из test_server.py
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            },
            # Запрос на поиск из test_server.py
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
            # Дополнительные тесты из test_server_enhanced.py
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/list",
                "params": {}
            }
        ]
        
        responses = []
        
        for i, request in enumerate(requests):
            # Корректируем ID для уникальности
            request["id"] = i + 1
            send_message_stdio(proc, request)
            response = read_message_stdio(proc)
            responses.append(response)
            print(f"Ответ на {request['method']} (ID: {request['id']}): {response}")
            print("-" * 50)
        
        return responses
        
    except Exception as e:
        print(f"Ошибка STDIO теста: {e}")
        return None
    finally:
        proc.terminate()
        # Выводим stderr сервера для отладки
        stderr_output = proc.stderr.read()
        if stderr_output:
            print(f"STDERR сервера:\n{stderr_output}")

def run_tcp_test():
    """Тестирование через TCP"""
    print("=== Тестирование TCP ===")
    
    try:
        # Подключаемся к TCP серверу (предполагаем, что он запущен)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Устанавливаем таймаут для подключения
        sock.settimeout(5)
        sock.connect(('127.0.0.1', 8765))
        # Сброс таймаута после успешного подключения
        sock.settimeout(None)
        
        # Пропускаем начальное сообщение client/registerCapability от сервера
        initial_response = read_message_tcp(sock)
        if initial_response and initial_response.get("method") == "client/registerCapability":
            print(f"Получено начальное сообщение от сервера: {initial_response['method']}")
        else:
            print(f"Неожиданный ответ от сервера при подключении: {initial_response}")
        
        # Последовательность тестовых запросов
        requests = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            },
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
            }
        ]
        
        responses = []
        
        for request in requests:
            send_message_tcp(sock, request)
            response = read_message_tcp(sock)
            responses.append(response)
            print(f"Ответ на {request['method']}: {response}")
            print("-" * 50)
        
        sock.close()
        return responses
        
    except socket.timeout:
        print("Ошибка TCP теста: Таймаут подключения. Убедитесь, что TCP сервер запущен.")
        print("Для запуска TCP сервера выполните: python tcp_ddg_server.py")
        return None
    except ConnectionRefusedError:
        print("Ошибка TCP теста: Подключение отклонено. Убедитесь, что TCP сервер запущен.")
        print("Для запуска TCP сервера выполните: python tcp_ddg_server.py")
        return None
    except Exception as e:
        print(f"Ошибка TCP теста: {e}")
        import traceback
        traceback.print_exc()
        return None

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
    print("Для выхода введите: quit")

def main():
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python test_server_enhanced.py stdio  - тестирование через STDIO")
        print("  python test_server_enhanced.py tcp    - тестирование через TCP")
        print("  python test_server_enhanced.py interactive - интерактивное тестирование")
        print("  python test_server_enhanced.py all    - все тесты")
        return
    
    test_type = sys.argv[1]
    
    if test_type == "stdio":
        print("Запуск STDIO теста...")
        run_stdio_test()
    elif test_type == "tcp":
        print("Запуск TCP теста...")
        run_tcp_test()
    elif test_type == "interactive":
        print("Запуск интерактивного теста...")
        run_interactive_test()
    elif test_type == "all":
        print("Запуск всех тестов...")
        print("1. Интерактивный тест:")
        run_interactive_test()
        print("\n" + "="*60 + "\n")
        print("2. STDIO тест:")
        run_stdio_test()
        print("\n" + "="*60 + "\n")
        print("3. TCP тест:")
        # Небольшая задержка перед запуском TCP теста
        time.sleep(2)
        run_tcp_test()
        print("\n" + "="*60 + "\n")
        print("Все тесты завершены.")
    else:
        print(f"Неизвестный тип теста: {test_type}")
        print("Доступные типы: stdio, tcp, interactive, all")

if __name__ == "__main__":
    main()