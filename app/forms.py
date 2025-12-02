from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, IntegerField, FloatField, TextAreaField, FileField
from wtforms.validators import DataRequired, Email, Length, EqualTo, NumberRange

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])

class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])

class VehicleForm(FlaskForm):
    make = StringField('Make', validators=[DataRequired(), Length(max=100)])
    model = StringField('Model', validators=[DataRequired(), Length(max=100)])
    year = IntegerField('Year', validators=[DataRequired(), NumberRange(min=1900, max=2030)])
    price = FloatField('Price ($)', validators=[DataRequired(), NumberRange(min=0)])
    description = TextAreaField('Description')
    image = FileField('Vehicle Image')
