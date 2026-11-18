import os, uuid
from datetime import datetime, date, timedelta
from functools import wraps
from flask import Flask, render_template, redirect, url_for, request, flash, jsonify, send_from_directory, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_
from models import db, User, Notice, Task, Notification, ChatMessage
from services import extract_document, analyze_notice, answer_from_notices, CATEGORIES

ALLOWED = {"pdf","jpg","jpeg","png","txt"}

def create_app():
    app=Flask(__name__)
    app.config.update(
        SECRET_KEY=os.getenv("SECRET_KEY","dev-only-change-this-secret"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL","sqlite:///noticeiq.db").replace("postgres://","postgresql://"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=int(os.getenv("MAX_CONTENT_LENGTH",10*1024*1024)),
        UPLOAD_FOLDER=os.path.abspath(os.getenv("UPLOAD_FOLDER","uploads"))
    )
    os.makedirs(app.config["UPLOAD_FOLDER"],exist_ok=True)
    db.init_app(app)
    login=LoginManager(app); login.login_view="login"; login.login_message="Please log in to continue."
    @login.user_loader
    def load_user(user_id): return db.session.get(User,int(user_id))
    with app.app_context(): db.create_all()

    @app.errorhandler(413)
    def too_large(e): return render_template("error.html",message="File is larger than the 10 MB upload limit."),413

    @app.route("/")
    def home():
        return render_template("landing.html") if not current_user.is_authenticated else redirect(url_for("dashboard"))

    @app.route("/register",methods=["GET","POST"])
    def register():
        if current_user.is_authenticated: return redirect(url_for("dashboard"))
        if request.method=="POST":
            name=request.form.get("name","").strip(); email=request.form.get("email","").strip().lower()
            password=request.form.get("password","")
            if not name or len(name)>100 or "@" not in email or len(password)<8:
                flash("Enter a valid name/email and a password of at least 8 characters.","error")
            elif User.query.filter_by(email=email).first():
                flash("An account with this email already exists.","error")
            else:
                user=User(name=name,email=email,password_hash=generate_password_hash(password))
                db.session.add(user); db.session.commit(); login_user(user)
                flash("Welcome to NoticeIQ. Your account is ready.","success")
                return redirect(url_for("dashboard"))
        return render_template("auth.html",mode="register")
    @app.route("/login",methods=["GET","POST"])
    def login():
        if current_user.is_authenticated: return redirect(url_for("dashboard"))
        if request.method=="POST":
            user=User.query.filter_by(email=request.form.get("email","").strip().lower()).first()
            if user and check_password_hash(user.password_hash,request.form.get("password","")):
                login_user(user); return redirect(url_for("dashboard"))
            flash("Email or password is incorrect.","error")
        return render_template("auth.html",mode="login")
    @app.route("/logout",methods=["POST"])
    @login_required
    def logout(): logout_user(); flash("You have been logged out.","success"); return redirect(url_for("home"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        notices=Notice.query.filter_by(user_id=current_user.id).order_by(Notice.created_at.desc()).limit(5).all()
        tasks=Task.query.filter_by(user_id=current_user.id).order_by(Task.due_date.asc().nullslast()).all()
        today=date.today()
        upcoming=[t for t in tasks if t.status!="Completed" and t.due_date and t.due_date.date()>=today][:5]
        return render_template("dashboard.html",notice_count=Notice.query.filter_by(user_id=current_user.id).count(),
            tasks=tasks,notices=notices,upcoming=upcoming,pending=sum(t.status!="Completed" for t in tasks),
            completed=sum(t.status=="Completed" for t in tasks),today=today)

    @app.route("/upload",methods=["GET","POST"])
    @login_required
    def upload():
        if request.method=="POST":
            pasted=request.form.get("notice_text","").strip()
            file=request.files.get("file")
            stored=None; filename=None; source="text"
            try:
                if file and file.filename:
                    filename=secure_filename(file.filename)
                    ext=os.path.splitext(filename)[1].lower()
                    if ext[1:] not in ALLOWED: raise ValueError("Only PDF, JPG, PNG, and TXT files are supported.")
                    stored=uuid.uuid4().hex+ext
                    path=os.path.join(app.config["UPLOAD_FOLDER"],stored)
                    file.save(path); source=ext[1:]
                    extracted=extract_document(path,ext)
                elif pasted: extracted=pasted
                else: raise ValueError("Choose a file or paste notice text.")
                if len(extracted.strip())<8: raise ValueError("Not enough readable text was extracted. Try a clearer file or paste the text.")
                analysis=analyze_notice(extracted)
                return render_template("review.html",analysis=analysis,extracted=extracted,stored=stored,
                    filename=filename,source=source)
            except Exception as e:
                if stored:
                    try: os.remove(os.path.join(app.config["UPLOAD_FOLDER"],stored))
                    except OSError: pass
                flash(str(e),"error")
        return render_template("upload.html")

    @app.route("/notices/save",methods=["POST"])
    @login_required
    def save_notice():
        data=request.get_json(silent=True) if request.is_json else request.form
        try:
            title=(data.get("title") or "Untitled notice").strip()[:220]
            extracted=data.get("extracted_text","")
            if len(extracted.strip())<8: raise ValueError("Notice text is required.")
            event_date=None
            raw=data.get("due_date","")
            if raw:
                try: event_date=date.fromisoformat(raw)
                except ValueError: pass
            stored_name = (data.get("stored") or "").strip()
            if stored_name:
                # Only accept server-generated flat filenames that already exist in our upload directory.
                if os.path.basename(stored_name) != stored_name or not os.path.isfile(os.path.join(app.config["UPLOAD_FOLDER"], stored_name)):
                    raise ValueError("The uploaded file reference is invalid. Please upload the notice again.")
            n=Notice(user_id=current_user.id,title=title,category=data.get("category","Other"),
                original_filename=data.get("filename") or "",stored_filename=stored_name,
                source_type=data.get("source","text"),extracted_text=extracted,
                instructions=data.get("instructions",""),venue=data.get("venue",""),
                priority=data.get("priority","Medium"),event_date=event_date)
            db.session.add(n); db.session.flush()
            if data.get("create_task") in (True,"true","on","1") and raw:
                due=datetime.combine(event_date,datetime.min.time())
                t=Task(user_id=current_user.id,notice_id=n.id,title=title,description=n.instructions or "Review the original notice and complete the required action.",category=n.category,due_date=due,priority=n.priority)
                db.session.add(t)
                db.session.add(Notification(user_id=current_user.id,title="Task created from a notice",message=f"{title} was added to your tasks."))
            db.session.commit()
            if request.is_json: return jsonify(ok=True,id=n.id)
            flash("Notice saved successfully.","success"); return redirect(url_for("notice_detail",notice_id=n.id))
        except Exception as e:
            db.session.rollback()
            if request.is_json: return jsonify(ok=False,error=str(e)),400
            flash(str(e),"error"); return redirect(url_for("upload"))

    @app.route("/notices")
    @login_required
    def notices():
        q=request.args.get("q","").strip(); category=request.args.get("category","")
        query=Notice.query.filter_by(user_id=current_user.id)
        if q: query=query.filter(or_(Notice.title.ilike(f"%{q}%"),Notice.extracted_text.ilike(f"%{q}%")))
        if category: query=query.filter_by(category=category)
        items=query.order_by(Notice.created_at.desc()).all()
        return render_template("notices.html",notices=items,categories=CATEGORIES,q=q,category=category)

    @app.route("/notices/<int:notice_id>")
    @login_required
    def notice_detail(notice_id):
        n=Notice.query.filter_by(id=notice_id,user_id=current_user.id).first_or_404()
        return render_template("notice_detail.html",notice=n)

    @app.route("/notices/<int:notice_id>/file")
    @login_required
    def notice_file(notice_id):
        n=Notice.query.filter_by(id=notice_id,user_id=current_user.id).first_or_404()
        if not n.stored_filename: abort(404)
        return send_from_directory(app.config["UPLOAD_FOLDER"],n.stored_filename,as_attachment=True,download_name=n.original_filename or "notice")

    @app.route("/notices/<int:notice_id>/delete",methods=["POST"])
    @login_required
    def delete_notice(notice_id):
        n=Notice.query.filter_by(id=notice_id,user_id=current_user.id).first_or_404()
        if n.stored_filename:
            try: os.remove(os.path.join(app.config["UPLOAD_FOLDER"],n.stored_filename))
            except OSError: pass
        db.session.delete(n); db.session.commit(); flash("Notice deleted.","success")
        return redirect(url_for("notices"))

    @app.route("/tasks",methods=["GET","POST"])
    @login_required
    def tasks_page():
        if request.method=="POST":
            title=request.form.get("title","").strip()
            if title:
                due=None
                if request.form.get("due_date"):
                    try: due=datetime.fromisoformat(request.form["due_date"])
                    except ValueError: pass
                db.session.add(Task(user_id=current_user.id,title=title,description=request.form.get("description",""),
                    category=request.form.get("category","Other"),due_date=due,priority=request.form.get("priority","Medium")))
                db.session.commit(); flash("Task added.","success")
            return redirect(url_for("tasks_page"))
        status=request.args.get("status",""); category=request.args.get("category",""); q=request.args.get("q","")
        query=Task.query.filter_by(user_id=current_user.id)
        if status: query=query.filter_by(status=status)
        if category: query=query.filter_by(category=category)
        if q: query=query.filter(Task.title.ilike(f"%{q}%"))
        items=query.order_by(Task.due_date.asc().nullslast()).all()
        return render_template("tasks.html",tasks=items,status=status,category=category,q=q,categories=CATEGORIES)

    @app.route("/tasks/<int:task_id>/update",methods=["POST"])
    @login_required
    def update_task(task_id):
        t=Task.query.filter_by(id=task_id,user_id=current_user.id).first_or_404()
        data=request.get_json(silent=True) or request.form
        if data.get("status") in ("Pending","In Progress","Completed"): t.status=data["status"]
        if data.get("title"): t.title=data["title"][:220]
        if "description" in data: t.description=data["description"]
        if "due_date" in data:
            try: t.due_date=datetime.fromisoformat(data["due_date"]) if data["due_date"] else None
            except ValueError: pass
        if data.get("priority") in ("Low","Medium","High"): t.priority=data["priority"]
        db.session.commit()
        if request.is_json: return jsonify(ok=True)
        flash("Task updated.","success"); return redirect(url_for("tasks_page"))
    @app.route("/tasks/<int:task_id>/delete",methods=["POST"])
    @login_required
    def delete_task(task_id):
        t=Task.query.filter_by(id=task_id,user_id=current_user.id).first_or_404()
        db.session.delete(t); db.session.commit(); flash("Task deleted.","success"); return redirect(url_for("tasks_page"))

    @app.route("/calendar")
    @login_required
    def calendar():
        tasks=Task.query.filter_by(user_id=current_user.id).filter(Task.due_date.isnot(None)).all()
        notices=Notice.query.filter_by(user_id=current_user.id).filter(Notice.event_date.isnot(None)).all()
        events=[{"title":t.title,"date":t.due_date.date().isoformat(),"type":"Task"} for t in tasks]
        events += [{"title":n.title,"date":n.event_date.isoformat(),"type":n.category} for n in notices]
        return render_template("calendar.html",events=events)

    @app.route("/chat",methods=["GET","POST"])
    @login_required
    def chat():
        if request.method=="POST":
            question=request.form.get("message","").strip()
            if question:
                db.session.add(ChatMessage(user_id=current_user.id,role="user",content=question))
                db.session.flush()
                saved=Notice.query.filter_by(user_id=current_user.id).order_by(Notice.created_at.desc()).all()
                answer=answer_from_notices(question,saved)
                db.session.add(ChatMessage(user_id=current_user.id,role="assistant",content=answer))
                db.session.commit()
            return redirect(url_for("chat"))
        history=ChatMessage.query.filter_by(user_id=current_user.id).order_by(ChatMessage.created_at.asc()).all()
        return render_template("chat.html",history=history)

    @app.route("/notifications")
    @login_required
    def notifications():
        items=Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
        for n in items: n.read=True
        db.session.commit()
        return render_template("notifications.html",notifications=items)

    @app.route("/profile",methods=["GET","POST"])
    @login_required
    def profile():
        if request.method=="POST":
            name=request.form.get("name","").strip()
            if name: current_user.name=name[:100]
            db.session.commit(); flash("Profile updated.","success"); return redirect(url_for("profile"))
        return render_template("profile.html")

    @app.context_processor
    def inject_globals():
        count=Notification.query.filter_by(user_id=current_user.id,read=False).count() if current_user.is_authenticated else 0
        return {"unread_notifications":count,"categories":CATEGORIES,"now":datetime.now()}
    return app

app=create_app()
if __name__=="__main__": app.run(debug=os.getenv("FLASK_DEBUG")=="1")
