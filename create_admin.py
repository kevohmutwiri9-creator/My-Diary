from app import create_app, db
from app.models.user import User

def create_admin(username, email, password):
    app = create_app()
    with app.app_context():
        # Check if admin already exists
        if User.query.filter_by(username=username).first():
            print(f"User '{username}' already exists!")
            return
        
        # Create new admin user
        admin = User(
            username=username,
            email=email,
            is_admin=True
        )
        admin.set_password(password)
        
        # Add to database
        db.session.add(admin)
        db.session.commit()
        print(f"Admin user '{username}' created successfully!")

if __name__ == "__main__":
    import getpass
    
    print("Create Admin User")
    print("================")
    username = input("Enter username: ")
    email = input("Enter email: ")
    
    while True:
        password = getpass.getpass("Enter password: ")
        confirm_password = getpass.getpass("Confirm password: ")
        if password == confirm_password:
            break
        print("Passwords do not match. Please try again.")
    
    create_admin(username, email, password)
