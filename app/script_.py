import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/auth/login"
REGISTER_URL = f"{BASE_URL}/users/"
API_URL = f"{BASE_URL}/dpp/json/"

# Credentials
USERNAME = "zoe"
PASSWORD = "test"
EMAIL = "zoe@example.com"

def create_user():
    print(f"👤 Attempting to create user '{USERNAME}'...")
    payload = {
        "username": USERNAME,
        "password": PASSWORD,
        "email": EMAIL,
        "role": "admin"
    }
    try:
        response = requests.post(REGISTER_URL, data=payload) # Form data
        if response.status_code in [200, 201]:
            print("✅ User created successfully!")
        elif response.status_code == 400 and "Email already registered" in response.text:
            print("ℹ️ User already exists (Email registered).")
        else:
            print(f"⚠️ User creation returned {response.status_code}: {response.text}")
            # Try to proceed anyway, maybe username exists but email check failed differently
    except Exception as e:
        print(f"💥 Failed to connect to registration: {str(e)}")

def get_access_token():
    try:
        response = requests.post(LOGIN_URL, json={"username": USERNAME, "password": PASSWORD})
        if response.status_code == 200:
            token = response.json().get("access_token")
            print("✅ Successfully authenticated!")
            return token
        else:
            print(f"❌ Authentication failed: {response.text}")
            return None
    except Exception as e:
        print(f"💥 Failed to connect to login: {str(e)}")
        return None

# Dataset με 20 Αντικείμενα
dpp_data = [
    # --- INDUSTRIAL (SIEMENS & ABB) ---
    {
        "title": "Siemens Simotics S-1FK7 Motor",
        "product_id": "SIE-MOT-1FK7-001",
        "manufacturer": "Siemens AG",
        "model_number": "1FK7063-2AF71-1RA0",
        "serial_number": "SN-98234122",
        "production_date": "2024-05-12",
        "attributes": {
            "power_kw": 2.3, "torque_nm": 11, "speed_rpm": 3000,
            "carbon_footprint_kg": 142.5, "efficiency_class": "IE4",
            "material_copper_kg": 2.1, "repairability_index": 8.8
        }
    },
    {
        "title": "Siemens Sinamics G120 Inverter",
        "product_id": "SIE-INV-G120-055",
        "manufacturer": "Siemens AG",
        "model_number": "6SL3210-1PE21-1AL0",
        "serial_number": "SN-77210983",
        "production_date": "2024-02-20",
        "attributes": {
            "voltage": "400V", "current": "11A", "co2_footprint": "95kg",
            "modular_design": True, "firmware_version": "v4.7"
        }
    },
    {
        "title": "ABB ACS880 Industrial Drive",
        "product_id": "ABB-DRV-880-012",
        "manufacturer": "ABB Group",
        "model_number": "ACS880-01-034A-3",
        "serial_number": "ABB-9912384",
        "production_date": "2023-11-15",
        "attributes": {
            "safety_level": "SIL3", "protection": "IP55",
            "energy_saving_mode": True, "recycled_plastic_pct": 15
        }
    },
    # --- ELECTRONICS & BATTERIES (TESLA, SAMSUNG, APPLE) ---
    {
        "title": "Tesla Powerwall 2 Plus",
        "product_id": "TSL-PW2-2024",
        "manufacturer": "Tesla Inc.",
        "model_number": "PW2-13.5-G1",
        "serial_number": "BAT-7622910-B",
        "production_date": "2024-08-01",
        "attributes": {
            "capacity_kwh": 13.5, "chemistry": "NMC",
            "cobalt_origin": "Congo", "lithium_origin": "Australia",
            "end_of_life_instructions": "Return to Tesla Service Center"
        }
    },
    {
        "title": "Samsung SDI Battery Cell 21700",
        "product_id": "SAM-CEL-21700-48G",
        "manufacturer": "Samsung SDI",
        "model_number": "INR21700-48G",
        "serial_number": "SAM-BATCH-44",
        "production_date": "2024-01-10",
        "attributes": {
            "voltage_nominal": 3.6, "capacity_mah": 4800,
            "cycle_life": 1000, "hazard_class": 9
        }
    },
    {
        "title": "Apple iPad Pro M4",
        "product_id": "APL-IPD-M4-512",
        "manufacturer": "Apple Inc.",
        "model_number": "A2902",
        "serial_number": "APL-S9923KML",
        "production_date": "2024-06-01",
        "attributes": {
            "rare_earth_recycled": 100, "aluminum_recycled": 100,
            "battery_health_score": 100, "repairability_rating": "4/10"
        }
    },
    # --- TEXTILES (PATAGONIA, LEVI'S) ---
    {
        "title": "Patagonia Nano Puff Jacket",
        "product_id": "PAT-NPF-BLU-M",
        "manufacturer": "Patagonia",
        "model_number": "84212",
        "serial_number": "PAT-2024-991",
        "production_date": "2024-03-15",
        "attributes": {
            "material": "100% Recycled Polyester", "fair_trade_certified": True,
            "water_consumption_liters": 12.5, "pfc_free": True
        }
    },
    {
        "title": "Levi's 501 Original Jeans",
        "product_id": "LEV-501-DNM-32",
        "manufacturer": "Levi Strauss & Co.",
        "model_number": "00501-0101",
        "serial_number": "LEV-002133",
        "production_date": "2023-12-20",
        "attributes": {
            "organic_cotton_pct": 98, "water_less_technology": True,
            "microplastic_shedding": "Low", "traceability_score": "A"
        }
    }
]

# Προσθέτω άλλα 12 αντικείμενα αυτόματα για να φτάσουμε τα 20
for i in range(9, 21):
    dpp_data.append({
        "title": f"Generic Product {i}",
        "product_id": f"GEN-PROD-{i:03d}",
        "manufacturer": "Standard Corp",
        "model_number": f"MOD-{i*10}",
        "serial_number": f"SN-{i*111}",
        "production_date": "2024-01-01",
        "attributes": {"test_field": "test_value", "category": "General"}
    })

def seed_database():
    # Step 1: Create User
    create_user()
    
    # Step 2: Login
    token = get_access_token()
    if not token:
        print("❌ Aborting seeding due to authentication failure.")
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    print(f"🚀 Starting seeding of {len(dpp_data)} items...")
    for item in dpp_data:
        try:
            response = requests.post(API_URL, json=item, headers=headers)
            if response.status_code in [200, 201]:
                print(f"✅ Success: {item['title']}")
            else:
                print(f"❌ Error {response.status_code} for {item['title']}: {response.text}")
        except Exception as e:
            print(f"💥 Failed to connect: {str(e)}")

if __name__ == "__main__":
    seed_database()
