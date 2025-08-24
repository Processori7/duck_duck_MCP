#!/usr/bin/env python3
"""
Simple test script to verify TCP MCP server connectivity
"""
import socket
import json
import time

def test_tcp_connection():
    """Test TCP server connection and basic MCP protocol"""
    print("🚀 Testing TCP MCP Server Connection...")
    
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
        return True
        
    except ConnectionRefusedError:
        print("❌ Connection refused - server not running on port 8765")
        return False
    except socket.timeout:
        print("❌ Connection timeout - server not responding")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_tcp_connection()