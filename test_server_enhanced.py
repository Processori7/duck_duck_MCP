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
        
        # Читаем сообщение
        message = proc.stdout.read(length)
        print(f"Получено сообщение: {message!r}")
        
        # Пропускаем \n
        proc.stdout.read(1)
        
        return json.loads(message)
    except Exception as e:
        print(f"Ошибка чтения STDIO: {e}")
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
        
        # Читаем сообщение
        length = int(length_str)
        content = sock.recv(length).decode('utf-8')
        print(f"Получено TCP сообщение: {content!r}")
        
        return json.loads(content)
    except Exception as e:
        print(f"Ошибка чтения TCP: {e}")
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
            send_message_stdio(proc, request)
            response = read_message_stdio(proc)
            responses.append(response)
            print(f"Ответ на {request['method']}: {response}")
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
        sock.connect(('127.0.0.1', 8765))
        
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
        
    except Exception as e:
        print(f"Ошибка TCP теста: {e}")
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
        print("  python test_server.py stdio  - тестирование через STDIO")
        print("  python test_server.py tcp    - тестирование через TCP")
        print("  python test_server.py interactive - интерактивное тестирование")
        print("  python test_server.py all    - все тесты")
        return
    
    test_type = sys.argv[1]
    
    if test_type == "stdio":
        run_stdio_test()
    elif test_type == "tcp":
        run_tcp_test()
    elif test_type == "interactive":
        run_interactive_test()
    elif test_type == "all":
        print("Запуск всех тестов...")
        run_interactive_test()
        print("\n" + "="*60 + "\n")
        run_stdio_test()
        print("\n" + "="*60 + "\n")
        run_tcp_test()
    else:
        print(f"Неизвестный тип теста: {test_type}")
        print("Доступные типы: stdio, tcp, interactive, all")

if __name__ == "__main__":
    main()