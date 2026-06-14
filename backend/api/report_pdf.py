from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from .models import StudyBlock

def generate_anexo_27(output, user):
    p = canvas.Canvas(output, pagesize=letter)
    width, height = letter

    # Header
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, height - 50, "ANEXO 27 - FICHA MÉDICA DE BUCEO")
    
    # User Data
    p.setFont("Helvetica", 12)
    p.drawString(100, height - 80, f"Nombre: {user.first_name} {user.last_name}")
    p.drawString(100, height - 100, f"Email: {user.email}")
    
    profile = getattr(user, 'profile', None)
    if profile:
        p.drawString(100, height - 120, f"DNI: {profile.dni}")
        p.drawString(100, height - 140, f"Grado: {profile.rank} | Destino: {profile.destination}")
        p.drawString(100, height - 160, f"Peso: {profile.weight} kg | Altura: {profile.height} cm")

    p.line(100, height - 180, 500, height - 180)

    # Studies and Notations
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, height - 210, "Estudios y Notaciones Médicas")
    
    y_position = height - 240
    blocks = StudyBlock.objects.filter(user=user)
    
    for block in blocks:
        if y_position < 100:
            p.showPage()
            y_position = height - 50
            
        p.setFont("Helvetica-Bold", 12)
        p.drawString(100, y_position, f"Estudio: {block.title} ({block.study_date})")
        y_position -= 20
        
        p.setFont("Helvetica", 10)
        p.drawString(120, y_position, f"Descripción: {block.description}")
        y_position -= 20
        
        comments = block.comments.all()
        for comment in comments:
            p.setFont("Helvetica-BoldOblique", 10)
            status_text = "APROBADO" if comment.status == "APPROVED" else "RECHAZADO"
            p.setFillColor(colors.green if comment.status == "APPROVED" else colors.red)
            p.drawString(140, y_position, f"[{status_text}] Médico ({comment.doctor.username}):")
            p.setFillColor(colors.black)
            y_position -= 12
            
            p.setFont("Helvetica-Oblique", 10)
            p.drawString(160, y_position, f"{comment.content}")
            y_position -= 15
            
            if comment.verified_signature:
                p.setFont("Helvetica-Bold", 8)
                p.drawString(140, y_position, "[Firma Digital Verificada]")
                y_position -= 15
        
        y_position -= 10
        p.line(120, y_position + 5, 480, y_position + 5)
        y_position -= 20

    p.save()
