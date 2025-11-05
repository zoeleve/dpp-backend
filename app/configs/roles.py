from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"

class UserSubRole(str, Enum):
    MANUFACTURER = "manufacturer"
    TECHNICIAN = "technician"
    DISTRIBUTOR = "distributor"
    RECYCLER = "recycler"
    INSPECTOR = "inspector"
    CONSUMER = "consumer"
    AUDITOR = "auditor"
    PARTNER = "partner"
