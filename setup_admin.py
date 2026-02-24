from app import app, db, User
import random

def generate_cpf():
    def calculate_digit(digits):
        soma = 0
        weight = len(digits) + 1
        for digit in digits:
            soma += int(digit) * weight
            weight -= 1
        remainder = (soma * 10) % 11
        return 0 if remainder == 10 else remainder

    digits = [random.randint(0, 9) for _ in range(9)]
    digits.append(calculate_digit(digits))
    digits.append(calculate_digit(digits))
    
    return "".join(map(str, digits))

def format_cpf(cpf):
    return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"

with app.app_context():
    db.create_all()
    
    if User.query.filter_by(username='admin').first():
        print("Admin validation: User exists.")
    else:
        # Generate a valid CPF for admin
        raw_cpf = generate_cpf()
        formatted_cpf = format_cpf(raw_cpf)
        
        user = User(
            username='admin',
            email='admin@siscap.local',
            cpf=formatted_cpf,
            active=True
        )
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()
        print(f"Admin created successfully!")
        print(f"Username: admin")
        print(f"Password: admin123")
        print(f"CPF: {formatted_cpf}")
        print(f"Email: admin@siscap.local")
