from typing import Dict, Any, List, Union
import sqlite3
from PyQt6.QtCore import QTimer, pyqtSignal, QObject
from datetime import datetime
from contextlib import contextmanager

from core.utils import API_ENDPOINTS, POST, UtilityFunctions
from core.client_network import ClientNetworkThread
from core.password_hasher import PasswordHasher

class CacheManager(QObject):
    connection_status_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.__CACHE_PATH = "./local_cache.db"
        self.__STATUSES = ("online", "offline", "server down")
        self.__status = 0
        self.last_sync = datetime.min.isoformat()
        self.__hasher = PasswordHasher()
        self.__init_db()
        self.__init_timer()
    
    @contextmanager
    def get_connection(self, err_msg = "Error", err_data = None):
        conn = None
        cursor = None
        try:
            conn = sqlite3.connect(self.__CACHE_PATH)
            cursor = conn.cursor()
            yield cursor

            if conn:
                conn.commit()

        except Exception as e:
            raise
            if conn:
                conn.rollback()
            print(f"{err_msg}: {str(e)}")
            return err_data
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def __init_db(self):
        with self.get_connection("Error initializing tables") as cursor:
            cursor.execute('''CREATE TABLE IF NOT EXISTS active_trainees (
                                assignment_id INTEGER PRIMARY KEY,
                                token_number INTEGER UNIQUE,
                                token_id TEXT UNIQUE,
                                trainee_name TEXT,
                                trainee_desg TEXT,
                                course_start_date TEXT,
                                course_end_date TEXT,
                                meal_preference TEXT NOT NULL
                        )''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS exceptions (
                                fake_exception_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                token_number INTEGER,
                                from_date TEXT,
                                to_date TEXT,
                                breakfast_time_slot TEXT,
                                lunch_time_slot TEXT,
                                dinner_time_slot TEXT,
                                is_suspended INTEGER
                        )''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS settings (
                                key TEXT UNIQUE,
                                value TEXT
                        )''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS qr_scans (
                                fake_scan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                                assignment_id INTEGER,
                                scan_date TEXT,
                                scan_time TEXT,
                                meal_type TEXT,
                                sync_status INTEGER DEFAULT 0,
                                FOREIGN KEY (assignment_id) REFERENCES active_trainees (assignment_id)
                        )''')
            
            cursor.execute('''CREATE INDEX IF NOT EXISTS idx_qr_scans_composite
                                ON qr_scans (assignment_id, scan_date, scan_time, meal_type)
                           ''')

            cursor.execute("SELECT value from settings WHERE key = 'last_sync_time'")
            res = cursor.fetchone()
            if res:
                self.last_sync = res[0]
    
    def __init_timer(self):
        self.nudge_timer = QTimer(self)
        self.nudge_timer.timeout.connect(self.__nudge_backend)
    
    def __nudge_backend(self):
        # Sync the qr_scans table of server
        with self.get_connection("Error syncing qr_scans") as cursor:
            cursor.execute("SELECT assignment_id, scan_date, scan_time, meal_type FROM qr_scans WHERE sync_status <> 0")
            res = cursor.fetchall()

            if res:
                # i want to call an API endpoint which allows offline scans to upload onto main database
                offline_scans = [
                    {"assignment_id": row[0], "date": row[1], "time": row[2], "meal_type": row[3]}
                    for row in res
                ]
            else:
                offline_scans = None

            self.__worker = ClientNetworkThread(
                self, API_ENDPOINTS["nudge-backend-to-save-to-local-cache"], POST,
                json_data = {"last_sync_str": self.last_sync, "scans": offline_scans}
            )
            self.__worker.bind_and_start(self.__on_api_success, self.__set_server_offline, self.set_client_offline)
    
    def __update_connection_status(self, new_status_idx: int):
        if self.__status != new_status_idx:
            self.__status = new_status_idx
            self.connection_status_changed.emit(self.__STATUSES[self.__status])
    
    def __on_api_success(self, action: str, data: Dict[str, Any]):
        print("Client Online")
        self.__update_connection_status(0)

        status = data.get("status")
        sync_time = data.get("server_sync_time")

        with self.get_connection("Sync failed") as cursor:

            # Enable WAL mode for drastically improved write performance
            cursor.execute("PRAGMA journal_mode=WAL;")

            cursor.execute('''
                INSERT INTO settings (key, value)
                VALUES ('last_sync_time', ?)
                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value
            ''', (sync_time,))
            cursor.execute("UPDATE qr_scans SET sync_status = 0 WHERE sync_status <> 0")

            if status == "up_to_date":
                print("Local cache already up to date!")
            
            elif status == "synced_now":
                print("Syncing cache with database...")
                start_time = datetime.now()
                self.__sync_with_backend(cursor, data)
                elapsed_time = datetime.now() - start_time
                print(f"Synced cache successfully in {elapsed_time}s!")
            
            self.last_sync = sync_time
    
    def __sync_with_backend(self, cursor: sqlite3.Cursor, data: Dict[str, Any]):
        assignments: List = data.get("assignments", [])
        assignments_list_of_tuple = [
            (row["assignment_id"], row["token_number"], row["token_id"],
             row["trainee_name"], row["trainee_desg"], row["course_start_date"],
             row["course_end_date"], row["meal_preference"]) 
            for row in assignments
        ]

        settings: Dict = data.get("settings", {})
        settings_list_of_tuple = [(key, value) for key, value in settings.items()]

        exceptions: List = data.get("exceptions", [])
        exceptions_list_of_tuple = [
            (row["token_number"], row["from_date"], row["to_date"],
             row["breakfast_time_slot"], row["lunch_time_slot"],
             row["dinner_time_slot"], row["is_suspended"]) 
            for row in exceptions
        ]

        scans: List = data.get("scans", [])
        scans_list_of_tuple = [
            (row["assignment_id"], row["scan_date"], row["scan_time"], row["meal_type"])
            for row in scans
        ]

        print(assignments_list_of_tuple)

        # Sync the active_trainees table
        upsert_query = """
            INSERT INTO active_trainees (
                assignment_id,
                token_number, 
                token_id,
                trainee_name,
                trainee_desg,
                course_start_date,
                course_end_date,
                meal_preference
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (assignment_id)
            DO UPDATE SET
                token_number = EXCLUDED.token_number,
                token_id = EXCLUDED.token_id,
                trainee_name = EXCLUDED.trainee_name,
                trainee_desg = EXCLUDED.trainee_desg,
                course_start_date = EXCLUDED.course_start_date,
                course_end_date = EXCLUDED.course_end_date,
                meal_preference = EXCLUDED.meal_preference
        """
        cursor.executemany(upsert_query, assignments_list_of_tuple)
        
        valid_backend_tokens = [row["assignment_id"] for row in assignments]
        if valid_backend_tokens:
            placeholders = ",".join(["?"] * len(valid_backend_tokens))
            delete_query = f"DELETE FROM active_trainees WHERE assignment_id NOT IN ({placeholders})"
        else:
            delete_query = "DELETE FROM active_trainees;"
        
        cursor.execute(delete_query, valid_backend_tokens)
        print("Sync complete [1/4]: active_trainees TABLE synced successfully!")


        # Sync the settings table
        upsert_query = """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT (key)
            DO UPDATE SET value = EXCLUDED.value
        """

        cursor.executemany(upsert_query, settings_list_of_tuple)
        print("Sync complete [2/4]: settings TABLE synced successfully!")


        # Sync the exceptions table
        cursor.execute("DELETE FROM exceptions;")
        insert_query = """
            INSERT INTO exceptions (
                token_number,
                from_date,
                to_date,
                breakfast_time_slot,
                lunch_time_slot,
                dinner_time_slot,
                is_suspended
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        cursor.executemany(insert_query, exceptions_list_of_tuple)
        print("Sync complete [3/4]: exceptions TABLE synced successfully!")


        # Sync the qr_scans table
        cursor.execute("DELETE FROM qr_scans;")
        placeholders = ', '.join(["(?, ?, ?, ?)"] * len(scans))
        flat_params = [val for row in scans_list_of_tuple for val in row]
        if flat_params:
            query = f"INSERT INTO qr_scans (assignment_id, scan_date, scan_time, meal_type) VALUES {placeholders}"
            cursor.execute(query, flat_params)
        print("Sync complete [4/4]: qr_scans TABLE synced successfully!")

    def __set_server_offline(self, action, error_msg):
        print("Server Down")
        print(f"Error caught on action: {action}\n{error_msg}")
        self.__update_connection_status(2)

    def set_client_offline(self):
        print("Client Offline")
        self.__update_connection_status(1)

    def start_sync(self, interval_ms: int) -> None:
        self.__nudge_backend()
        self.nudge_timer.start(interval_ms)
    
    def get_status(self) -> str:
        return self.__STATUSES[self.__status]
    
    def get_data(self, key: str) -> Union[List[tuple], None]:
        with self.get_connection("Error fetching data from cache") as cursor:
            if key == "assignments":
                cursor.execute("""SELECT token_number, token_id, trainee_name, trainee_desg,
                               course_start_date, course_end_date, meal_preference
                               FROM active_trainees""")
            elif key == "settings":
                cursor.execute("SELECT key, value FROM settings WHERE key <> 'last_sync_time'")
            elif key == "exceptions":
                cursor.execute("""SELECT token_number, from_date, to_date, breakfast_time_slot,
                               lunch_time_slot, dinner_time_slot, is_suspended
                               FROM exceptions""")
            elif key == "scans":
                current_date = UtilityFunctions.get_current_ist_datetime().strftime("%Y-%m-%d")
                cursor.execute("""SELECT
                                    t.token_number,
                                    t.trainee_name,
                                    t.meal_preference,
                                    q.scan_date,
                                    q.scan_time
                                FROM active_trainees AS t
                                INNER JOIN qr_scans AS q
                                ON t.assignment_id = q.assignment_id
                                WHERE q.scan_date = ? ORDER BY q.scan_time ASC
                               """, (current_date,))
            else:
                return None

            return cursor.fetchall()
    
    def add_online_scan(self, token_number: int, scan_date: str, scan_time: str, meal_type: str) -> bool:
        with self.get_connection() as cursor:

            cursor.execute("SELECT assignment_id FROM active_trainees WHERE token_number = ?", (token_number,))
            res = cursor.fetchone()
            if not res:
                return False
            
            assignment_id = res[0]
            current_date = UtilityFunctions.get_current_ist_datetime().strftime("%Y-%m-%d")
            cursor.execute("DELETE FROM qr_scans WHERE scan_date < ?", (current_date,))

            cursor.execute("""INSERT INTO qr_scans (assignment_id, scan_date, scan_time, meal_type)
                                VALUES (?, ?, ?, ?)
                           """, (assignment_id, scan_date, scan_time, meal_type))
            return True

    # Called from methods that are called when client is offline
    def verify_token_and_supply_data(
        self,
        cursor: sqlite3.Cursor,
        token_id: str,
        token_number: int
    ) -> Dict[str, Union[str, int]]:
        cursor.execute('''
                    SELECT assignment_id, trainee_name, trainee_desg, course_end_date, meal_preference
                    FROM active_trainees
                    WHERE token_id = ?
                    ''', (token_id,)
                    )
        trainee_data = cursor.fetchone()

        # Check - Is the QR token assigned to a trainee?
        if not trainee_data:
            return {
                "status": "failure",
                "message": "There is no trainee assigned to this Physical QR Token"
            }
        else:
            assignment_id, name, desg, end_date, preference = trainee_data
        
        current_datetime = UtilityFunctions.get_current_ist_datetime()
        current_date = current_datetime.strftime("%Y-%m-%d")
        current_time = current_datetime.strftime("%H:%M:%S")

        # Check - Did the QR token expire for that trainee?
        if (datetime.strptime(end_date.strip(), "%Y-%m-%d").date() < current_datetime.date()):
            return "Physical QR Token expired for the trainee!"

        cursor.execute("SELECT key, value FROM settings WHERE key LIKE '%_time_slot' OR key = 'only_veg_days'")
        settings: Dict[str, str] = {key:value for (key, value) in cursor.fetchall()}

        time_slot_keys = ("breakfast_time_slot", "lunch_time_slot", "dinner_time_slot")

        # Check - Have the Meal Slot Timing Settings been initialized?
        if not all([slot in settings for slot in time_slot_keys]):
            return {
                "status": "failure",
                "message": "Meal Time Slot configuration data not found!"
            }

        active_breakfast_slot = settings.get(time_slot_keys[0])
        active_lunch_slot = settings.get(time_slot_keys[1])
        active_dinner_slot = settings.get(time_slot_keys[2])
        only_veg_days = settings.get("only_veg_days")

        if only_veg_days and only_veg_days.strip():
            only_veg_days_arr = [day.strip().title() for day in only_veg_days.split(',') if day.strip()]
            if current_datetime.strftime("%a") in only_veg_days_arr:
                preference = "VEG (same for all today)"

        cursor.execute('''
                    SELECT breakfast_time_slot, lunch_time_slot, dinner_time_slot, is_suspended
                    FROM exceptions
                    WHERE token_number = ? AND ? BETWEEN from_date AND to_date
                    ORDER BY fake_exception_id DESC LIMIT 1
                    ''', (token_number, current_date)
                    )
        active_exception = cursor.fetchone()

        if active_exception:
            custom_breakfast_slot, custom_lunch_slot, custom_dinner_slot, is_suspended = active_exception

            # Check - Is that trainee suspended from meals for today (due to vacation etc.)?
            if is_suspended:
                return {
                    "status": "failure",
                    "message": f"Token No. ({token_number}) is suspended from meals today!"
                }

            active_breakfast_slot = custom_breakfast_slot or active_breakfast_slot
            active_lunch_slot = custom_lunch_slot or active_lunch_slot
            active_dinner_slot = custom_dinner_slot or active_dinner_slot
        
        time_slot_names = ("BREAKFAST", "LUNCH", "DINNER")
        active_time_slots = (active_breakfast_slot, active_lunch_slot, active_dinner_slot)
        
        matched_slot_name = None

        for slot_type, slot in zip(time_slot_names, active_time_slots):
            if UtilityFunctions.is_time_in_slot(current_time, slot):
                matched_slot_name = slot_type
                break
        
        if not matched_slot_name:
            # Check - Is it the correct time to scan the QR? (No meals right now)
            return {
                "status": "failure",
                "message": "Not a valid meal slot! Try again later!"
            }
        
        cursor.execute(
            "SELECT meal_type FROM qr_scans WHERE assignment_id = ? AND scan_date = ?",
            (assignment_id, current_date)
        )
        meals_taken_today = [res[0] for res in cursor.fetchall()]


        if matched_slot_name in meals_taken_today:
            return {
                "status": "failure",
                "message": f"The trainee has already taken the meal for {matched_slot_name.upper()}!"
            }
        
        cursor.execute(
            '''INSERT INTO qr_scans (assignment_id, scan_date, scan_time, meal_type, sync_status)
            VALUES (?, ?, ?, ?, ?)''', (assignment_id, current_date, current_time, matched_slot_name, self.__status)
        )

        return {"status": "success", "token_id": token_id, "token_number": token_number, "trainee_name": name,
                "trainee_desg": desg, "meal_preference": preference}
    
    # Called only when client offline
    def verify_scanned_token(self, token_id: str) -> Dict[str, Union[str, int]]:
        parts = token_id.split('.')
        if (len(parts)!=2):
            return {
                "status": "failure",
                "message": "Invalid QR Code Scanned! (Invalid Format)"
            }
        token_number, token_hash_code = parts

        try:
            token_number = int(token_number)
        except ValueError:
            return {
                "status": "failure",
                "message": "Invalid Token Number (within QR Code)"
            }
        
        if not self.__hasher.check_password(str(token_number), token_hash_code):
            return {
                "status": "failure",
                "message": "Invalid QR Code scanned! (Invalid Hash)"
            }

        with self.get_connection(
            err_data={
                "status": "failure",
                "message": "Error verifying token"
            }
        ) as cursor:
            cursor.execute("SELECT 1 FROM active_trainees WHERE token_id = ?", (token_id,))
            res = cursor.fetchone()

            # Check - Is the QR scanned a valid token?
            if not res:
                return {
                    "status": "failure",
                    "message": "Invalid QR Code scanned! (Invalid Token Number)"
                }
            
            return self.verify_token_and_supply_data(cursor, token_id=token_id, token_number=token_number)
    
    # Called only when client offline
    def verify_typed_token(self, token_number: int) -> Dict[str, Union[str, int]]:
        with self.get_connection(
            err_data={
                "status": "failure",
                "message": f"Error verifying token"
            }
        ) as cursor:  
            cursor.execute("SELECT token_id FROM active_trainees WHERE token_number = ?", (token_number,))
            res = cursor.fetchone()

            # Check - Is the QR scanned a valid token?
            if not res:
                return {
                    "status": "failure",
                    "message": "Invalid Token Number (Not Registered)"
                }
            else:
                token_id = res[0]
            
            return self.verify_token_and_supply_data(cursor, token_id=token_id, token_number=token_number)