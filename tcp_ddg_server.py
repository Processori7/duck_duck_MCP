#!/usr/bin/env python3
import json
import socket
import threading
import sys
import os
import signal
import time
import logging
from datetime import datetime

# Настройка логирования для видимости всех сообщений
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Выводим в stdout для видимости
    ]
)
logger = logging.getLogger(__name__)

# Импортируем логику из основного сервера
try:
    from ddg_mcp_server import (
        handle_request
    )
    logger.info("✓ Модуль ddg_mcp_server успешно импортирован")
except ImportError as e:
    logger.error(f"✗ Ошибка импорта ddg_mcp_server: {e}")
    print("Ошибка: не найден ddg_mcp_server. Убедитесь, что файл в папке.")
    sys.exit(1)


def send_message_tcp(conn, data):
    """Отправка сообщения через TCP в формате MCP"""
    try:
        # Используем ensure_ascii=False для корректной обработки Unicode
        data_str = json.dumps(data, ensure_ascii=False)
        data_bytes = data_str.encode('utf-8')
        # MCP использует простой JSON + newline формат
        message = data_bytes + b'\n'
        conn.sendall(message)
        logger.debug(f"Отправлено сообщение: {data_str[:100]}...")
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        raise
    
    
def read_message(conn):
    """Чтение сообщения через TCP в формате MCP (JSON + newline)"""
    try:
        # Устанавливаем таймаут
        conn.settimeout(30)
        
        # Читаем до newline (MCP формат)
        message_bytes = b''
        while True:
            try:
                chunk = conn.recv(1)
                if not chunk:
                    logger.debug("Клиент закрыл соединение")
                    return None
                    
                if chunk == b'\n':
                    break
                    
                message_bytes += chunk
                
                # Защита от слишком больших сообщений
                if len(message_bytes) > 1024 * 1024:  # 1MB лимит
                    logger.error("Сообщение слишком большое")
                    return None
                    
            except socket.timeout:
                logger.warning("Таймаут при чтении сообщения")
                return None
        
        if not message_bytes:
            logger.debug("Получено пустое сообщение")
            return None
            
        # Декодируем и парсим JSON
        content = message_bytes.decode('utf-8')
        logger.debug(f"Получено сообщение ({len(content)} символов): {content[:200]}...")
        
        return json.loads(content)
        
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON: {e}")
        logger.error(f"Проблемное сообщение: {content if 'content' in locals() else 'undefined'}")
        return None
    except socket.error as e:
        logger.error(f"Ошибка сокета: {e}")
        return None
    except Exception as e:
        logger.error(f"Ошибка чтения: {e}")
        import traceback
        traceback.print_exc()
        return None

def handle_client(conn, addr):
    """Обработка клиента с поддержкой MCP протокола"""
    logger.info(f"✓ Новое подключение от {addr}")
    print(f"\n{'='*60}")
    print(f"[+] Клиент подключился: {addr[0]}:{addr[1]}")
    print(f"{'='*60}")
    
    try:
        # Устанавливаем keep-alive для стабильности соединения
        conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        
        # Ожидаем инициализацию от MCP клиента
        logger.info(f"Ожидаем MCP инициализацию от клиента {addr}")
        
        while True:
            message = read_message(conn)
            if message is None:
                logger.info(f"Соединение закрыто клиентом {addr}")
                break
            
            method = message.get('method', 'unknown')
            request_id = message.get('id', 'no-id')
            
            print(f"\n[←] Запрос #{request_id}: {method}")
            logger.info(f"Обработка запроса {method} от {addr}")
            
            # Выводим параметры для отладки
            if 'params' in message:
                params = message['params']
                if method == 'tools/call':
                    tool_name = params.get('name', 'unknown')
                    print(f"    └─ Инструмент: {tool_name}")
                    if 'arguments' in params:
                        args = params['arguments']
                        if 'query' in args:
                            print(f"    └─ Запрос: '{args['query']}'")
            
            # Обрабатываем запрос
            start_time = time.time()
            response = handle_request(message)
            elapsed = time.time() - start_time
            
            if response:
                if 'error' in response:
                    print(f"[✗] Ошибка: {response['error'].get('message', 'Unknown error')}")
                    logger.error(f"Ошибка обработки: {response['error']}")
                else:
                    print(f"[→] Ответ отправлен (обработка: {elapsed:.2f}с)")
                    logger.info(f"Ответ отправлен за {elapsed:.2f} секунд")
                    
                send_message_tcp(conn, response)
                # Небольшая задержка для стабильности
                time.sleep(0.01)  # Уменьшаем задержку для лучшей отзывчивости
            else:
                logger.warning("Получен пустой ответ от handle_request")
                # Отправляем ошибку клиенту
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": "Internal error: empty response"
                    }
                }
                send_message_tcp(conn, error_response)
                
    except ConnectionResetError:
        print(f"\n[!] Клиент {addr} принудительно разорвал соединение")
        logger.warning(f"Клиент {addr} принудительно разорвал соединение")
    except Exception as e:
        print(f"\n[!] Ошибка обработки клиента {addr}: {e}")
        logger.error(f"Ошибка обработки клиента {addr}: {e}", exc_info=True)
    finally:
        try:
            conn.close()
        except:
            pass
        print(f"\n[-] Клиент {addr[0]}:{addr[1]} отключился")
        print(f"{'='*60}\n")
        logger.info(f"Клиент {addr} отключился")

def main():
    """Запуск TCP-сервера с улучшенной совместимостью MCP"""
    print("\n" + "="*60)
    print("      DuckDuckGo MCP TCP Server")
    print("="*60)
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # Улучшенные настройки для стабильности
    server.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    server.settimeout(1.0)  # Таймаут 1 секунда для accept()
    
    try:
        server.bind(('127.0.0.1', 8765))
        server.listen(5)  # Увеличиваем очередь подключений
        
        print(f"\n[✓] Сервер запущен: 127.0.0.1:8765")
        print(f"[✓] Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[i] Для остановки нажмите Ctrl+C")
        print(f"[i] MCP протокол: JSON-RPC 2.0 через TCP")
        print("\n" + "="*60)
        print("Ожидание подключений...\n")
        
        logger.info("TCP сервер успешно запущен на 127.0.0.1:8765")
        
        connection_count = 0
        while True:
            try:
                conn, addr = server.accept()
                connection_count += 1
                print(f"\n[★] Подключение #{connection_count} от {addr[0]}:{addr[1]}")
                
                # Делаем потоки daemon, чтобы они завершались при выходе из программы
                thread = threading.Thread(
                    target=handle_client, 
                    args=(conn, addr), 
                    daemon=True,
                    name=f"Client-{addr[0]}:{addr[1]}"
                )
                thread.start()
                logger.info(f"Запущен поток для обработки клиента {addr}")
                
            except socket.timeout:
                # Это нормально - просто продолжаем ждать
                continue
            except KeyboardInterrupt:
                print("\n\n" + "="*60)
                print("[!] Получен сигнал остановки (Ctrl+C)")
                print("="*60)
                break
                
    except OSError as e:
        if e.errno == 10048:  # Windows: порт уже используется
            print(f"\n" + "="*60)
            print("[✗] ОШИБКА: Порт 8765 уже используется!")
            print("="*60)
            print("\nВозможные решения:")
            print("  1. Закройте другой экземпляр сервера")
            print("  2. Подождите несколько секунд и повторите запуск")
            print("  3. Используйте команду для поиска процесса:")
            print("     netstat -ano | findstr :8765")
            logger.error(f"Порт 8765 уже занят")
        else:
            print(f"\n[✗] Ошибка запуска сервера: {e}")
            logger.error(f"Ошибка запуска сервера: {e}")
    except Exception as e:
        print(f"\n[✗] Неожиданная ошибка: {e}")
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
    finally:
        print("\n" + "="*60)
        print("[...] Остановка сервера...")
        server.close()
        print("[✓] Сервер остановлен")
        print(f"[✓] Время остановки: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60 + "\n")
        logger.info("TCP сервер остановлен")

if __name__ == "__main__":
    try:
        # Проверяем, что все необходимые модули установлены
        try:
            import ddgs
            logger.info("✓ Модуль ddgs установлен")
        except ImportError:
            print("\n[✗] ОШИБКА: Модуль 'ddgs' не установлен!")
            print("Установите его командой: pip install ddgs")
            sys.exit(1)
            
        main()
    except KeyboardInterrupt:
        print("\n[✓] Сервер корректно остановлен пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\n[✗] Критическая ошибка: {e}")
        logger.error(f"Критическая ошибка: {e}", exc_info=True)
        sys.exit(1)
