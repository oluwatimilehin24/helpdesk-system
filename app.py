from flask import render_template, request, redirect, url_for
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///helpdesk.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev-secret-key'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='Medium')
    status = db.Column(db.String(20), default='Open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)

with app.app_context():
    db.create_all()
    print("Database created successfully.")

@app.route('/')
def dashboard():
    tickets = Ticket.query.all()
    open_count = Ticket.query.filter_by(status='Open').count()
    in_progress = Ticket.query.filter_by(status='In Progress').count()
    resolved = Ticket.query.filter_by(status='Resolved').count()
    return render_template('dashboard.html', tickets=tickets,
                           open=open_count, in_progress=in_progress, resolved=resolved)

@app.route('/ticket/new', methods=['GET', 'POST'])
def new_ticket():
    if request.method == 'POST':
        ticket = Ticket(
            title=request.form['title'],
            description=request.form['description'],
            priority=request.form['priority'],
            user_id=1
        )
        db.session.add(ticket)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('new_ticket.html')

@app.route('/ticket/<int:id>')
def view_ticket(id):
    ticket = Ticket.query.get_or_404(id)
    return render_template('view_ticket.html', ticket=ticket)

@app.route('/ticket/<int:id>/update', methods=['POST'])
def update_ticket(id):
    ticket = Ticket.query.get_or_404(id)
    ticket.status = request.form['status']
    if ticket.status == 'Resolved':
        ticket.resolved_at = datetime.utcnow()
        ticket.resolution_notes = request.form.get('resolution_notes', '')
    db.session.commit()
    return redirect(url_for('view_ticket', id=id))

@app.route('/tickets')
def all_tickets():
    tickets = Ticket.query.order_by(Ticket.created_at.desc()).all()
    return render_template('all_tickets.html', tickets=tickets)

@app.route('/sla')
def sla_dashboard():
    sla_targets = {
        'Critical': 4,
        'High': 8,
        'Medium': 24,
        'Low': 72
    }

    tickets  = Ticket.query.all()
    sla_data = []
    breached = 0
    compliant = 0

    for ticket in tickets:
        target_hours = sla_targets.get(ticket.priority, 24)
        target_minutes = target_hours * 60

        if ticket.resolved_at:
            # Ticket is resolved - calculate actual time taken
            delta = ticket.resolved_at - ticket.created_at
            minutes_taken = delta.total_seconds() / 60
            met_sla = minutes_taken <= target_minutes
            hours_taken = round(delta.total_seconds() / 3600, 1)
            status_label = 'Resolved'
        else:
            # Ticket still open - calculate time elapsed so far
            delta = datetime.utcnow() - ticket.created_at
            minutes_taken = delta.total_seconds() / 60
            met_sla = minutes_taken  <= target_minutes
            hours_taken = round(delta.total_seconds() / 3600, 1)
            status_label = ticket.status

        if met_sla:
            compliant += 1
        else:
            breached += 1

        sla_data.append({
            'id': ticket.id,
            'title': ticket.title,
            'priority': ticket.priority,
            'status': status_label,
            'hours_taken': hours_taken,
            'target_hours': target_hours,
            'met_sla': met_sla
        })

    total = compliant + breached
    compliance_rate = round((compliant / total * 100), 1) if total > 0 else 0

    return render_template('sla_dashboard.html',
                           sla_data=sla_data,
                           compliant=compliant,
                           breached=breached,
                           compliance_rate=compliance_rate)

if __name__ == '__main__':
    app.run(debug=True)