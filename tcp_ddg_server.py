#!/usr/bin/env python3
import json
import socket
import threading
import sys

# Импортируем логику из основного сервера
try:
    from ddg_mcp_server import (
        handle_request,
        send_message
    )
except ImportError:
    print("Ошибка: не найден ddg_mcp_server. Убедитесь, что файл в папке.")
    sys.exit(1)



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
        
        # Читаем сообщение
        length = int(length_str)
        content = conn.recv(length).decode('utf-8')
        return json.loads(content)
    except Exception as e:
        print(f"Ошибка чтения: {e}")
        return None

def handle_client(conn, addr):
    """Обработка клиента"""
    print(f"Клиент подключился: {addr}")
    try:
        # Отправляем регистрацию
        send_message(conn, {
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
                send_message(conn, response)
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