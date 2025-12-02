from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

from .models import db, User, Vehicle
from .forms import LoginForm, SignupForm, VehicleForm
from .aws_services import s3_service, dynamodb_service, cloudwatch_service

# Import custom library
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from automotive_lib import VehicleAnalytics, PriceCalculator

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__)

# Initialize custom library
price_calculator = PriceCalculator()
analytics = VehicleAnalytics()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Auth Routes
@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            cloudwatch_service.log_event(f"User {user.username} logged in", "INFO")
            dynamodb_service.log_activity(user.id, 'LOGIN', {'ip': request.remote_addr})
            flash('Login successful!', 'success')
            return redirect(url_for('main.dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html', form=form)


@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    form = SignupForm()
    if form.validate_on_submit():
        existing_user = User.query.filter(
            (User.username == form.username.data) | (User.email == form.email.data)
        ).first()
        if existing_user:
            flash('Username or email already exists', 'danger')
            return render_template('signup.html', form=form)
        
        user = User(
            username=form.username.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data)
        )
        db.session.add(user)
        db.session.commit()
        
        cloudwatch_service.log_event(f"New user registered: {user.username}", "INFO")
        dynamodb_service.log_activity(user.id, 'SIGNUP', {'email': user.email})
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('signup.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    cloudwatch_service.log_event(f"User {current_user.username} logged out", "INFO")
    dynamodb_service.log_activity(current_user.id, 'LOGOUT', {})
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.index'))


# Main Routes
@main.route('/')
def index():
    vehicles = Vehicle.query.order_by(Vehicle.created_at.desc()).limit(6).all()
    return render_template('index.html', vehicles=vehicles)


@main.route('/dashboard')
@login_required
def dashboard():
    vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    
    # Use custom library for analytics
    vehicle_data = [{'make': v.make, 'model': v.model, 'year': v.year, 'price': v.price} for v in vehicles]
    analytics.set_vehicles(vehicle_data)
    summary = analytics.get_summary()
    
    return render_template('dashboard.html', vehicles=vehicles, analytics=summary)


@main.route('/vehicles')
def list_vehicles():
    vehicles = Vehicle.query.order_by(Vehicle.created_at.desc()).all()
    return render_template('vehicles.html', vehicles=vehicles)


@main.route('/vehicle/<int:id>')
def view_vehicle(id):
    vehicle = Vehicle.query.get_or_404(id)
    
    # Use custom library for price analysis
    price_info = price_calculator.get_price_suggestion(vehicle.make, vehicle.year)
    
    return render_template('vehicle_detail.html', vehicle=vehicle, price_info=price_info)


@main.route('/vehicle/add', methods=['GET', 'POST'])
@login_required
def add_vehicle():
    form = VehicleForm()
    if form.validate_on_submit():
        image_url = None
        
        # Upload image to S3 if provided
        if form.image.data and hasattr(form.image.data, 'filename'):
            if allowed_file(form.image.data.filename):
                filename = secure_filename(form.image.data.filename)
                result = s3_service.upload_file(form.image.data, filename)
                if result['success']:
                    image_url = result['url']
        
        vehicle = Vehicle(
            make=form.make.data,
            model=form.model.data,
            year=form.year.data,
            price=form.price.data,
            description=form.description.data,
            image_url=image_url,
            user_id=current_user.id
        )
        db.session.add(vehicle)
        db.session.commit()
        
        cloudwatch_service.log_event(f"Vehicle added: {vehicle.make} {vehicle.model}", "INFO")
        dynamodb_service.log_activity(current_user.id, 'ADD_VEHICLE', {
            'vehicle_id': vehicle.id, 'make': vehicle.make, 'model': vehicle.model
        })
        
        flash('Vehicle added successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('vehicle_form.html', form=form, title='Add Vehicle')


@main.route('/vehicle/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_vehicle(id):
    vehicle = Vehicle.query.get_or_404(id)
    if vehicle.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('main.dashboard'))
    
    form = VehicleForm(obj=vehicle)
    if form.validate_on_submit():
        # Upload new image if provided
        if form.image.data and hasattr(form.image.data, 'filename') and form.image.data.filename:
            if allowed_file(form.image.data.filename):
                filename = secure_filename(form.image.data.filename)
                result = s3_service.upload_file(form.image.data, filename)
                if result['success']:
                    vehicle.image_url = result['url']
        
        vehicle.make = form.make.data
        vehicle.model = form.model.data
        vehicle.year = form.year.data
        vehicle.price = form.price.data
        vehicle.description = form.description.data
        db.session.commit()
        
        cloudwatch_service.log_event(f"Vehicle updated: {vehicle.id}", "INFO")
        dynamodb_service.log_activity(current_user.id, 'EDIT_VEHICLE', {'vehicle_id': vehicle.id})
        
        flash('Vehicle updated successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    return render_template('vehicle_form.html', form=form, title='Edit Vehicle', vehicle=vehicle)


@main.route('/vehicle/delete/<int:id>', methods=['POST'])
@login_required
def delete_vehicle(id):
    vehicle = Vehicle.query.get_or_404(id)
    if vehicle.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('main.dashboard'))
    
    cloudwatch_service.log_event(f"Vehicle deleted: {vehicle.id}", "INFO")
    dynamodb_service.log_activity(current_user.id, 'DELETE_VEHICLE', {
        'vehicle_id': vehicle.id, 'make': vehicle.make
    })
    
    db.session.delete(vehicle)
    db.session.commit()
    
    flash('Vehicle deleted successfully!', 'success')
    return redirect(url_for('main.dashboard'))


@main.route('/analytics')
@login_required
def analytics_page():
    all_vehicles = Vehicle.query.all()
    vehicle_data = [{'make': v.make, 'model': v.model, 'year': v.year, 'price': v.price} for v in all_vehicles]
    analytics.set_vehicles(vehicle_data)
    summary = analytics.get_summary()
    return render_template('analytics.html', analytics=summary)
