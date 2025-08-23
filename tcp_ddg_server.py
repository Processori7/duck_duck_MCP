#!/usr/bin/env python3
import json
import socket
import threading
import sys
import os

# Импортируем логику из основного сервера
try:
    from ddg_mcp_server import (
        handle_request
    )
except ImportError:
    print("Ошибка: не найден ddg_mcp_server. Убедитесь, что файл в папке.")
    sys.exit(1)


def send_message_tcp(conn, data):
    """Send message via TCP"""
    data_str = json.dumps(data, ensure_ascii=True)
    message = f'{len(data_str)}\n{data_str}\n'
    conn.sendall(message.encode('utf-8'))
    
    
def read_message(conn):
    """Чтение сообщения через TCP"""
    try:
        # Читаем длину
        length_bytes = b''
        while b'\n' not in length_bytes:
            chunk = conn.recv(1)
            if not chunk:
                return None
            length_bytes += chunk
        length_str = length_bytes.decode('utf-8').strip()
        
        # Проверяем, что длина не пустая
        if not length_str:
            print("Получена пустая строка вместо длины сообщения")
            return None
            
        # Читаем сообщение
        length = int(length_str)
        content_bytes = b''
        while len(content_bytes) < length:
            chunk = conn.recv(length - len(content_bytes))
            if not chunk:
                return None
            content_bytes += chunk
            
        content = content_bytes.decode('utf-8')
        # Пропускаем \n после сообщения
        conn.recv(1)
        
        return json.loads(content)
    except ValueError as e:
        print(f"Ошибка преобразования длины: {e}")
        return None
    except Exception as e:
        print(f"Ошибка чтения: {e}")
        return None

def handle_client(conn, addr):
    """Обработка клиента"""
    print(f"Клиент подключился: {addr}")
    try:
        # Отправляем регистрацию
        send_message_tcp(conn, {
            "jsonrpc": "2.0",
            "method": "client/registerCapability",
            "params": {"registrations": []}
        })

        while True:
            message = read_message(conn)
            if message is None:
                print("Соединение закрыто клиентом")
                break
            
            response = handle_request(message)
            if response:
                send_message_tcp(conn, response)
                # Добавим небольшую задержку, чтобы клиент успел прочитать ответ
                import time
                time.sleep(0.1)
    except Exception as e:
        print(f"Ошибка обработки клиента: {e}")
    finally:
        conn.close()
        print(f"Клиент {addr} отключился")

def main():
    """Запуск TCP-сервера"""
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('127.0.0.1', 8765))
        server.listen(1)
        print("TCP сервер запущен на 127.0.0.1:8765")
        
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.start()
    except Exception as e:
        print(f"Ошибка запуска сервера: {e}")
    finally:
        server.close()

if __name__ == "__main__":
    main()