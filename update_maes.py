from app import app, db
from models import Aluno

with app.app_context():
    # Update text 'None' to NULL
    count1 = Aluno.query.filter(Aluno.nome_mae == 'None').update({Aluno.nome_mae: None}, synchronize_session=False)
    # Update empty string to NULL
    count2 = Aluno.query.filter(Aluno.nome_mae == '').update({Aluno.nome_mae: None}, synchronize_session=False)
    
    db.session.commit()
    
    print(f"Alunos atualizados: {count1 + count2}")
