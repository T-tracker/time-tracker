import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'BD_Kursach'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://time_tracker_user:gioz7F3J1k2WeaD6gwheZ3qSX7NZxgt8@dpg-d51cnqv5r7bs73flp8o0-a.oregon-postgres.render.com/time_tracker_i4rz'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
