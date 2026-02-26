import time
from datetime import datetime
from pymodbus.client.sync import ModbusTcpClient
import mysql.connector

# --- CONFIGURATION ---
PLC_IP = "192.168.1.3"  # S7-1200 IP Address
PLC_PORT = 506          # Communication Port
PLC_UNIT_ID = 3         # Modbus Unit ID

DB_CONFIG = {
    'host': 'localhost',
    'user': 'admin',        
    'password': 'admin1234',
    'database': 's7_logging_db'
}

def save_production_data(data_list):
    """
    Inserts 7 production parameters into the database.
    Note: The 8th value (Trigger) is NOT saved as per requirement.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # SQL for 7 production columns only
        sql = """INSERT INTO production_logs 
                 (unit_id, ID1_Counter, ID2_Counter, OK_Counter, NG_Counter, All_Counter, Efficiency, Cycle_Time) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"""
        
        # Prepare only first 7 values for the database
        if len(data_list) >= 7:
            record = [PLC_UNIT_ID] + data_list[:7]
            cursor.execute(sql, record)
            conn.commit()
            print(f"[{datetime.now()}] Data Logging Executed: Trigger received from PLC.")
        else:
            print(f"[{datetime.now()}] Error: Insufficient data length.")
            
    except mysql.connector.Error as err:
        print(f"[{datetime.now()}] Database Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

def main():
    client = ModbusTcpClient(PLC_IP, port=PLC_PORT)
    print(f"Starting Trigger-Based Logger (Watching Reg7 for Command) -> {PLC_IP}:{PLC_PORT}")

    while True:
        try:
            # --- AUTO-RECONNECT LOGIC ---
            if not client.is_socket_open():
                print(f"[{datetime.now()}] Connecting to PLC...")
                if not client.connect():
                    time.sleep(5)
                    continue

            # --- DATA ACQUISITION ---
            # Read 8 registers (Reg0 to Reg7)
            # Reg0-6: Production Data | Reg7: Trigger Command
            result = client.read_holding_registers(0, 8, slave=PLC_UNIT_ID)
            
            if not result.isError():
                # --- TRIGGER CHECK ---
                # Check only the 8th value (Index 7) to decide if we should log
                is_trigger_active = (result.registers[7] == 1)
                
                if is_trigger_active:
                    # Save only the production data (first 7 values)
                    save_production_data(result.registers)
                    
                    # Delay to prevent multiple logs while PLC trigger is still high (1)
                    # Adjust this time depending on how long your PLC trigger stays active
                    time.sleep(2) 
                else:
                    # Do nothing, just monitor the trigger status
                    print(f"[{datetime.now()}] System Ready: Waiting for Trigger (Current: 0)", end="\r")
                
                # Polling interval: check PLC every 1 second
                time.sleep(1) 
            else:
                print(f"\n[{datetime.now()}] Modbus Read Error. Resetting...")
                client.close()
                time.sleep(2)

        except Exception as e:
            print(f"\n[{datetime.now()}] Global System Error: {e}")
            try:
                client.close()
            except:
                pass
            time.sleep(5)

if __name__ == "__main__":
    main()
