from app.utils.security import hash_password, verify_password

def test_password_hashing():
    """
    Unit Test: Verify that password hashing and verification work correctly.
    """
    password = "secret_password"
    hashed = hash_password(password)
    
    # Ensure the hashed password is not the same as the plain text
    assert hashed != password
    
    # Ensure the correct password verifies successfully
    assert verify_password(password, hashed) is True
    
    # Ensure a wrong password fails verification
    assert verify_password("wrong_password", hashed) is False
