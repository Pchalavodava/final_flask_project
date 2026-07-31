from apscheduler.schedulers.background import BackgroundScheduler

from app.calculatings import calculate_new_weekly_top

scheduler = BackgroundScheduler()

scheduler.add_job(calculate_new_weekly_top, trigger='cron', day_of_week='mon', hour=0, minute=0, id='update_top')