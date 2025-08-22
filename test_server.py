#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы MCP сервера
"""

import json
import subprocess
import sys

def send_message(proc, data):
    """Отправка сообщения в процесс"""
    data_str = json.dumps(data, ensure_ascii=False)
    message = f'{len(data_str)}\n{data_str}\n'
    print(f"Отправляем: {message!r}")
    proc.stdin.write(message)
    proc.stdin.flush()

def read_message(proc):
    """Чтение сообщения из процесса"""
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

def main():
    # Запускаем сервер
    proc = subprocess.Popen(
        [sys.executable, 'ddg_mcp_server.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding='utf-8'
    )
    
    try:
        # Отправляем initialize запрос
        initialize_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        send_message(proc, initialize_request)
        
        # Читаем ответ
        response = read_message(proc)
        print(f"Ответ на initialize: {response}")
        
        # Отправляем запрос на поиск
        search_request = {
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
        }
        send_message(proc, search_request)
        
        # Читаем ответ
        response = read_message(proc)
        print(f"Ответ на поиск: {response}")
        
    finally:
        proc.terminate()
        # Выводим stderr сервера для отладки
        stderr_output = proc.stderr.read()
        print(f"STDERR сервера:\n{stderr_output}")

if __name__ == "__main__":
    main()